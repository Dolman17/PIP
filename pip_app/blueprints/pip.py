from __future__ import annotations

import os
from datetime import datetime, timezone

from flask import (
    Blueprint,
    abort,
    current_app,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    send_file,
    session,
    url_for,
)
from flask_login import current_user, login_required
from sqlalchemy import or_

from forms import PIPForm
from models import AIConsentLog, DraftPIP, DocumentFile, Employee, PIPActionItem, PIPRecord, TimelineEvent, db
from pip_app.security import (
    log_security_event,
    require_employee_access,
    require_pip_access,
    scoped_employee_query,
)
from pip_app.services.ai_utils import get_openai_client
from pip_app.services.document_utils import (
    BASE_DIR,
    build_doc_rel_dir,
    build_placeholder_mapping,
    docx_to_html,
    generate_docx_bytes,
    html_to_docx_bytes,
    sanitize_html,
)
from pip_app.services.storage_utils import next_version_for, save_file
from pip_app.services.taxonomy import pick_actions_from_templates as _pick_actions_from_templates
from pip_app.services.time_utils import auto_review_date
from pip_app.services.timeline_utils import log_timeline_event

pip_bp = Blueprint("pip", __name__)


def _friendly_ai_error_message(exc):
    message = str(exc).strip()

    if "OPENAI_API_KEY is not configured" in message:
        return (
            "AI guidance is not available because the OpenAI API key has not been configured. "
            "Please add a valid API key in the environment settings."
        )

    if "Incorrect API key" in message or "invalid_api_key" in message:
        return (
            "AI guidance could not be generated because the configured OpenAI API key appears to be invalid."
        )

    if "Rate limit" in message or "rate_limit" in message:
        return (
            "AI guidance is temporarily unavailable because the OpenAI rate limit has been reached. "
            "Please try again shortly."
        )

    if "insufficient_quota" in message:
        return (
            "AI guidance could not be generated because the OpenAI account has insufficient quota."
        )

    return (
        "AI guidance could not be generated at the moment. "
        "Please try again later or check the AI configuration."
    )


def _max_wizard_step(data: dict) -> int:
    s = 1
    if data.get('employee_id'):
        s = 2
    if all(data.get(k) for k in ('concerns', 'concern_category', 'severity', 'frequency')):
        s = 3
    if all(data.get(k) for k in ('start_date', 'review_date')):
        s = 4
    if all(data.get(k) for k in ('capability_meeting_date', 'capability_meeting_time', 'capability_meeting_venue')):
        s = 5
    items = data.get('action_plan_items') or []
    if s == 5 and isinstance(items, list) and any((x or '').strip() for x in items):
        s = 6
    return s


def get_active_draft_for_user(user_id):
    return DraftPIP.query.filter_by(user_id=user_id, is_dismissed=False) \
                         .order_by(DraftPIP.updated_at.desc()).first()


def _scoped_employee_query():
    return scoped_employee_query(Employee.query, Employee)


def _active_employee_query(include_employee_id=None):
    q = _scoped_employee_query()

    if include_employee_id:
        q = q.filter(
            or_(
                Employee.is_leaver.is_(False),
                Employee.id == include_employee_id
            )
        )
    else:
        q = q.filter(Employee.is_leaver.is_(False))

    return q.order_by(Employee.last_name.asc(), Employee.first_name.asc())


def _scoped_pip_query():
    q = PIPRecord.query.join(Employee)
    if current_user.admin_level == 0:
        if current_user.team_id:
            q = q.filter(Employee.team_id == current_user.team_id)
        else:
            q = q.filter(Employee.id == -1)
    return q


def _has_recent_ai_consent(context_name: str, minutes: int = 120) -> bool:
    latest = (
        AIConsentLog.query
        .filter_by(user_id=current_user.id, context=context_name, accepted=True)
        .order_by(AIConsentLog.accepted_at.desc())
        .first()
    )
    if not latest or not latest.accepted_at:
        return False

    accepted_at = latest.accepted_at
    if accepted_at.tzinfo is not None:
        accepted_at = accepted_at.replace(tzinfo=None)

    age_seconds = (datetime.utcnow() - accepted_at).total_seconds()
    return age_seconds <= minutes * 60


@pip_bp.route('/pip/<int:id>')
@login_required
def pip_detail(id):
    pip = PIPRecord.query.get_or_404(id)
    require_pip_access(pip)
    employee = pip.employee
    return render_template('pip_detail.html', pip=pip, employee=employee)


@pip_bp.route("/pip/<int:pip_id>/documents", methods=["GET"])
@login_required
def pip_documents(pip_id):
    pip_rec = PIPRecord.query.get_or_404(pip_id)
    require_pip_access(pip_rec)

    docs = (
        DocumentFile.query
        .filter_by(pip_id=pip_id)
        .order_by(DocumentFile.created_at.desc())
        .all()
    )
    return render_template("pip_documents.html", pip_rec=pip_rec, docs=docs)


@pip_bp.route("/pip/<int:pip_id>/doc/create/<string:doc_type>", methods=["POST"])
@login_required
def create_pip_doc_draft(pip_id, doc_type):
    pip_rec = PIPRecord.query.get_or_404(pip_id)
    require_pip_access(pip_rec)

    mapping = build_placeholder_mapping(pip_rec)

    template_map = {
        "invite": os.path.join(BASE_DIR, "templates", "docx", "PIP_Invite_Letter_Template_v2025-08-28.docx"),
        "plan": os.path.join(BASE_DIR, "templates", "docx", "PIP_Action_Plan_Template_v2025-08-28.docx"),
        "outcome": os.path.join(BASE_DIR, "templates", "docx", "PIP_Outcome_Letter_Template_v2025-08-28.docx"),
    }
    if doc_type not in template_map:
        abort(404)

    outcome_choice = getattr(pip_rec, "outcome_choice", None)
    docx_bytes = generate_docx_bytes(template_map[doc_type], mapping, outcome_choice=outcome_choice)

    html_raw = docx_to_html(docx_bytes)
    html_clean = sanitize_html(html_raw)

    version = next_version_for(pip_id, doc_type)
    rel_dir = build_doc_rel_dir(pip_id, doc_type, version)
    rel_docx_path = save_file(docx_bytes, rel_dir, f"{doc_type}_v{version}.docx")

    doc = DocumentFile(
        pip_id=pip_id,
        doc_type=doc_type,
        version=version,
        status="draft",
        docx_path=rel_docx_path,
        html_snapshot=html_clean,
        created_by=current_user.username,
    )

    db.session.add(doc)
    db.session.commit()

    log_timeline_event(
        pip_id=pip_id,
        event_type="Document Draft Created",
        notes=f"{doc.doc_type.capitalize()} v{doc.version} created from template.",
    )

    try:
        log_security_event(
            event_type="PIP Document Draft Created",
            notes=f"{doc.doc_type.capitalize()} v{doc.version} created for PIP #{pip_id}",
            pip_record_id=pip_id,
            updated_by=current_user.username,
        )
    except Exception:
        pass

    flash(f"{doc_type.capitalize()} draft v{version} created.", "success")
    return redirect(url_for("pip.edit_pip_doc", pip_id=pip_id, doc_id=doc.id))


@pip_bp.route("/pip/<int:pip_id>/doc/<int:doc_id>/edit", methods=["GET", "POST"])
@login_required
def edit_pip_doc(pip_id, doc_id):
    pip_rec = PIPRecord.query.get_or_404(pip_id)
    require_pip_access(pip_rec)

    doc = DocumentFile.query.filter_by(id=doc_id, pip_id=pip_id).first_or_404()

    if request.method == "POST":
        html = request.form.get("html", "")
        if not html:
            flash("No content received.", "warning")
            return redirect(request.url)

        clean_html = sanitize_html(html)
        new_docx = html_to_docx_bytes(clean_html)

        if not new_docx:
            flash("The edited document could not be converted to DOCX.", "danger")
            return redirect(request.url)

        rel_dir = build_doc_rel_dir(pip_id, doc.doc_type, doc.version)
        rel_docx_path = save_file(
            new_docx,
            rel_dir,
            f"{doc.doc_type}_v{doc.version}_edited.docx"
        )

        doc.html_snapshot = clean_html
        doc.docx_path = rel_docx_path
        db.session.commit()

        log_timeline_event(
            pip_id=pip_id,
            event_type="Document Draft Updated",
            notes=f"{doc.doc_type.capitalize()} v{doc.version} draft updated.",
        )

        try:
            log_security_event(
                event_type="PIP Document Draft Updated",
                notes=f"{doc.doc_type.capitalize()} v{doc.version} updated for PIP #{pip_id}",
                pip_record_id=pip_id,
                updated_by=current_user.username,
            )
        except Exception:
            pass

        flash("Draft updated.", "success")
        return redirect(request.url)

    return render_template(
        "doc_editor.html",
        pip_rec=pip_rec,
        doc=doc,
        html_content=doc.html_snapshot,
    )


@pip_bp.route("/pip/<int:pip_id>/doc/<int:doc_id>/finalise", methods=["POST"])
@login_required
def finalise_pip_doc(pip_id, doc_id):
    pip_rec = PIPRecord.query.get_or_404(pip_id)
    require_pip_access(pip_rec)

    doc = DocumentFile.query.filter_by(id=doc_id, pip_id=pip_id).first_or_404()
    if doc.status == "final":
        flash("Document already final.", "info")
        return redirect(url_for("pip.pip_documents", pip_id=pip_id))

    doc.status = "final"
    db.session.commit()

    log_timeline_event(
        pip_id=pip_id,
        event_type="Document Finalised",
        notes=f"{doc.doc_type.capitalize()} v{doc.version} finalised.",
    )

    try:
        log_security_event(
            event_type="PIP Document Finalised",
            notes=f"{doc.doc_type.capitalize()} v{doc.version} finalised for PIP #{pip_id}",
            pip_record_id=pip_id,
            updated_by=current_user.username,
        )
    except Exception:
        pass

    flash(f"{doc.doc_type.capitalize()} v{doc.version} finalised.", "success")
    return redirect(url_for("pip.pip_documents", pip_id=pip_id))


@pip_bp.route("/download/doc/<int:doc_id>")
@login_required
def download_doc(doc_id):
    doc = DocumentFile.query.get_or_404(doc_id)
    pip_rec = PIPRecord.query.get_or_404(doc.pip_id)
    require_pip_access(pip_rec)

    abs_path = os.path.join(current_app.config['UPLOAD_FOLDER'], doc.docx_path)

    if not os.path.exists(abs_path):
        print(f"[DOWNLOAD] Missing file: {abs_path}")
        abort(404)

    size = os.path.getsize(abs_path)
    print(f"[DOWNLOAD] doc_id={doc_id} path={abs_path} size={size} bytes")

    try:
        log_security_event(
            event_type="PIP Document Downloaded",
            notes=f"{doc.doc_type.capitalize()} v{doc.version} downloaded for PIP #{doc.pip_id}",
            pip_record_id=doc.pip_id,
            updated_by=current_user.username,
        )
    except Exception:
        pass

    return send_file(abs_path, as_attachment=True, download_name=os.path.basename(abs_path))


@pip_bp.route('/pip/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_pip(id):
    pip = PIPRecord.query.get_or_404(id)
    require_pip_access(pip)
    employee = pip.employee

    if request.method == 'POST':
        form = PIPForm()
        form.process(request.form)
    else:
        form = PIPForm(obj=pip)
        for _ in range(len(pip.action_items) - len(form.actions.entries)):
            form.actions.append_entry()
        for idx, ai in enumerate(pip.action_items):
            form.actions.entries[idx].form.description.data = ai.description
            form.actions.entries[idx].form.status.data = ai.status

    advice_text = None

    if request.method == 'POST' and 'generate_advice' in request.form:
        if not _has_recent_ai_consent("pip_advice"):
            flash("Please accept the AI guidance notice before generating advice.", "warning")
            return redirect(url_for('pip.edit_pip', id=pip.id))

        prompt = (
            f"You are a performance coach.\n"
            f"Employee: {employee.first_name} {employee.last_name}\n"
            f"Job Title: {employee.job_title}\n"
            f"Concerns: {form.concerns.data or '[none]'}\n"
            "Action Items:\n"
        )
        for ai_field in form.actions.entries:
            desc = ai_field.form.description.data or '[no description]'
            stat = ai_field.form.status.data or '[no status]'
            prompt += f"- {desc} [{stat}]\n"
        prompt += f"Meeting Notes: {form.meeting_notes.data or '[none]'}\n"
        prompt += "Provide 3 bulleted actionable tips for the manager to support this employee."

        try:
            client = get_openai_client()
            resp = client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
            )
            advice_text = resp.choices[0].message.content.strip()
        except Exception as exc:
            flash(_friendly_ai_error_message(exc), "error")
            return redirect(url_for('pip.edit_pip', id=pip.id))

        try:
            log_security_event(
                event_type="PIP AI Advice Preview Generated",
                notes=f"Inline AI advice generated for PIP #{pip.id}",
                pip_record_id=pip.id,
                updated_by=current_user.username,
            )
        except Exception:
            pass

        return render_template('edit_pip.html', form=form, pip=pip, employee=employee, advice_text=advice_text)

    if form.validate_on_submit():
        pip.concerns = form.concerns.data
        pip.start_date = form.start_date.data
        pip.review_date = form.review_date.data
        pip.status = form.status.data
        pip.meeting_notes = form.meeting_notes.data
        pip.capability_meeting_date = form.capability_meeting_date.data
        pip.capability_meeting_time = form.capability_meeting_time.data
        pip.capability_meeting_venue = form.capability_meeting_venue.data

        pip.action_items.clear()
        for ai_field in form.actions.entries:
            pip.action_items.append(
                PIPActionItem(
                    description=ai_field.form.description.data,
                    status=ai_field.form.status.data
                )
            )

        db.session.commit()

        try:
            log_security_event(
                event_type="PIP Updated",
                notes=f"PIP #{pip.id} updated",
                pip_record_id=pip.id,
                updated_by=current_user.username,
            )
        except Exception:
            pass

        flash('PIP updated successfully.', 'success')
        return redirect(url_for('pip.pip_detail', id=pip.id))

    return render_template('edit_pip.html', form=form, pip=pip, employee=employee, advice_text=advice_text)


@pip_bp.route('/pip/<int:id>/generate/advice', methods=['POST'])
@login_required
def generate_ai_advice(id):
    pip = PIPRecord.query.get_or_404(id)
    require_pip_access(pip)
    employee = pip.employee

    if not _has_recent_ai_consent("pip_advice"):
        flash("Please accept the AI guidance notice before generating advice.", "warning")
        return redirect(url_for('pip.pip_detail', id=pip.id))

    prompt = (
        "You are an experienced HR Line Manager based in the UK. "
        "Using the information below, provide three clear and practical suggestions for how a line manager "
        "can support the employee's performance improvement. Your advice should reflect HR best practice in the UK.\n\n"
        f"Employee Name: {employee.first_name} {employee.last_name}\n"
        f"Job Title: {employee.job_title}\n"
        f"Concerns: {pip.concerns or '[none]'}\n"
        "Action Items:\n"
    )
    for item in pip.action_items:
        prompt += f"- {item.description or '[no description]'} [{item.status or '[no status]'}]\n"
    prompt += f"Meeting Notes: {pip.meeting_notes or '[none]'}\n\n"
    prompt += "Provide your advice as a bullet-pointed list."

    try:
        client = get_openai_client()
        resp = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
        )

        pip.ai_advice = resp.choices[0].message.content.strip()
        pip.ai_advice_generated_at = datetime.now(timezone.utc)

        event = TimelineEvent(
            pip_record_id=pip.id,
            event_type="AI Advice Generated",
            notes="Advice generated using OpenAI",
            updated_by=current_user.username
        )
        db.session.add(event)

        consent = AIConsentLog(
            user_id=current_user.id,
            context="pip_advice",
            accepted=True,
            accepted_at=datetime.now(timezone.utc),
            request_ip=request.remote_addr,
            user_agent=request.headers.get("User-Agent")
        )
        db.session.add(consent)

        db.session.commit()

    except Exception as e:
        db.session.rollback()
        print(f"[AI ERROR] Failed to generate AI advice for PIP #{pip.id}: {e}")
        flash(_friendly_ai_error_message(e), "error")
        return redirect(url_for('pip.pip_detail', id=pip.id))

    try:
        log_security_event(
            event_type="PIP AI Advice Generated",
            notes=f"AI advice generated for PIP #{pip.id}",
            pip_record_id=pip.id,
            updated_by=current_user.username,
        )
    except Exception:
        pass

    flash('AI advice generated.', 'success')
    return redirect(url_for('pip.pip_detail', id=pip.id))


@pip_bp.route('/pip/create/<int:employee_id>', methods=['GET', 'POST'])
@login_required
def create_pip(employee_id):
    employee = _scoped_employee_query().filter(Employee.id == employee_id).first_or_404()
    require_employee_access(employee)

    if employee.is_leaver:
        flash('You cannot start a new PIP for an employee who is marked as a leaver.', 'warning')
        return redirect(url_for('manage_employee.detail', employee_id=employee.id))

    form = PIPForm()
    if request.method == 'GET' and len(form.actions.entries) == 0:
        form.actions.append_entry()

    if request.method == 'POST':
        action_fields = [k for k in request.form if 'actions-' in k and '-description' in k]
        form.actions.min_entries = len(set(k.split('-')[1] for k in action_fields))

    if form.validate_on_submit():
        pip = PIPRecord(
            employee_id=employee.id,
            concerns=form.concerns.data,
            start_date=form.start_date.data,
            review_date=form.review_date.data,
            meeting_notes=form.meeting_notes.data
        )
        db.session.add(pip)
        db.session.flush()

        for action_form in form.actions.entries:
            item = PIPActionItem(
                pip_record_id=pip.id,
                description=action_form.form.description.data,
                status=action_form.form.status.data
            )
            db.session.add(item)

        db.session.commit()

        try:
            log_security_event(
                event_type="PIP Created",
                notes=f"PIP #{pip.id} created for employee {employee.full_name}",
                pip_record_id=pip.id,
                updated_by=current_user.username,
            )
        except Exception:
            pass

        flash('New PIP created.')
        return redirect(url_for('employees.employee_detail', employee_id=employee.id))

    return render_template('create_pip.html', form=form, employee=employee)


@pip_bp.route('/pip/list')
@login_required
def pip_list():
    pips = _scoped_pip_query().all()
    return render_template('pip_list.html', pips=pips)


@pip_bp.route('/pip/select-employee', methods=['GET', 'POST'])
@login_required
def select_employee_for_pip():
    employees = _active_employee_query().all()

    if request.method == 'POST':
        employee_id = request.form.get('employee_id')
        return redirect(url_for('pip.create_pip', employee_id=employee_id))

    return render_template('pip_select_employee.html', employees=employees)


@pip_bp.route('/pip/create-wizard', methods=['GET', 'POST'])
@login_required
def create_pip_wizard():
    if 'wizard_step' not in session:
        session['wizard_step'] = 1
        session['pip_data'] = {}

    step = session['wizard_step']
    data = session.get('pip_data', {}) or {}
    wizard_errors = {}
    draft = None

    if request.method == 'GET':
        try:
            goto = int(request.args.get('goto', 0))
        except (TypeError, ValueError):
            goto = 0
        if goto:
            max_allowed = _max_wizard_step(data)
            if 1 <= goto <= max_allowed:
                session['wizard_step'] = goto
                step = goto

        if step == 3 and data.get('start_date') and not data.get('review_date'):
            auto_val = auto_review_date(data.get('start_date'))
            if auto_val:
                data['review_date'] = auto_val
                data['auto_review_populated'] = True
                data['auto_review_date'] = auto_val
                session['pip_data'] = data

    if request.method == 'POST':
        if step == 1:
            employee_id = request.form.get('employee_id')
            draft_name = request.form.get('draft_name', '').strip()

            if not employee_id:
                wizard_errors['employee_id'] = "Please select an employee."
            else:
                try:
                    employee_id_int = int(employee_id)
                except (TypeError, ValueError):
                    employee_id_int = None

                employee = None
                if employee_id_int:
                    employee = _active_employee_query(include_employee_id=employee_id_int) \
                        .filter(Employee.id == employee_id_int) \
                        .first()

                if not employee:
                    wizard_errors['employee_id'] = "Please select a valid employee."
                elif employee.is_leaver:
                    wizard_errors['employee_id'] = "You cannot start a new PIP for an employee who is marked as a leaver."
                else:
                    data['employee_id'] = employee.id
                    data['employee_name'] = employee.full_name

            data['draft_name'] = draft_name

        elif step == 2:
            concerns = request.form.get('concerns', '').strip()
            category = request.form.get('concern_category', '').strip()
            severity = request.form.get('severity', '').strip()
            frequency = request.form.get('frequency', '').strip()
            tags = request.form.get('concern_tags', '').strip()
            draft_name = request.form.get('draft_name', '').strip()

            if not concerns:
                wizard_errors['concerns'] = "Concerns cannot be empty."
            if not category:
                wizard_errors['concern_category'] = "Please choose a concern category."
            if not severity:
                wizard_errors['severity'] = "Please select severity."
            if not frequency:
                wizard_errors['frequency'] = "Please select frequency."

            data.update({
                'concerns': concerns,
                'concern_category': category,
                'severity': severity,
                'frequency': frequency,
                'concern_tags': tags,
                'draft_name': draft_name,
            })

        elif step == 3:
            start_date = (request.form.get('start_date') or '').strip()
            review_date = (request.form.get('review_date') or '').strip()
            draft_name = request.form.get('draft_name', '').strip()
            review_weeks = (request.form.get('review_weeks') or '').strip()

            if not start_date:
                wizard_errors['start_date'] = "Start date is required."

            auto_flag = False
            if start_date and not review_date:
                auto_val = auto_review_date(start_date)
                if auto_val:
                    review_date = auto_val
                    auto_flag = True

            if not wizard_errors:
                data['start_date'] = start_date
                data['review_date'] = review_date
                if review_weeks.isdigit():
                    data['review_weeks'] = int(review_weeks)
                elif 'review_weeks' not in data:
                    data['review_weeks'] = 4
                data['auto_review_populated'] = bool(auto_flag)
                data['auto_review_date'] = review_date if auto_flag else None

            data['draft_name'] = draft_name

        elif step == 4:
            data['capability_meeting_date'] = request.form.get('capability_meeting_date')
            data['capability_meeting_time'] = request.form.get('capability_meeting_time')
            data['capability_meeting_venue'] = request.form.get('capability_meeting_venue')
            data['draft_name'] = request.form.get('draft_name', '').strip()

        elif step == 5:
            action_items = request.form.getlist('action_plan_items[]')
            valid_items = [item.strip() for item in action_items if item.strip()]
            if not valid_items:
                wizard_errors['action_plan_items'] = "Add at least one action plan item."
            else:
                data['action_plan_items'] = valid_items
                session['pip_data'] = data
                session['wizard_step'] = 6
                return redirect(url_for('pip.create_pip_wizard'))

        elif step == 6:
            try:
                employee_id = int(data['employee_id'])
                employee = _scoped_employee_query().filter(Employee.id == employee_id).first_or_404()
                require_employee_access(employee)

                if employee.is_leaver:
                    flash("You cannot create a new PIP for an employee who is marked as a leaver.", "warning")
                    session['wizard_step'] = 1
                    return redirect(url_for('pip.create_pip_wizard'))

                items = data.get('action_plan_items') or []
                if not any((x or '').strip() for x in items):
                    flash("Please add at least one action plan item.", "warning")
                    session['wizard_step'] = 5
                    return redirect(url_for('pip.create_pip_wizard'))

                pip = PIPRecord(
                    employee_id=employee_id,
                    concerns=data['concerns'],
                    concern_category=data.get('concern_category'),
                    severity=data.get('severity'),
                    frequency=data.get('frequency'),
                    tags=data.get('concern_tags'),
                    start_date=datetime.strptime(data['start_date'], '%Y-%m-%d').date(),
                    review_date=datetime.strptime(data['review_date'], '%Y-%m-%d').date(),
                    capability_meeting_date=datetime.strptime(data['capability_meeting_date'], '%Y-%m-%d')
                        if data.get('capability_meeting_date') else None,
                    capability_meeting_time=data.get('capability_meeting_time'),
                    capability_meeting_venue=data.get('capability_meeting_venue'),
                    created_by=current_user.username
                )

                db.session.add(pip)
                db.session.commit()

                for item_text in items:
                    action = PIPActionItem(pip_record_id=pip.id, description=item_text)
                    db.session.add(action)

                timeline = TimelineEvent(
                    pip_record_id=pip.id,
                    event_type="PIP Created",
                    notes="PIP created via multi-step wizard",
                    updated_by=current_user.username
                )
                db.session.add(timeline)

                db.session.commit()

                try:
                    log_security_event(
                        event_type="PIP Created",
                        notes=f"PIP #{pip.id} created via multi-step wizard",
                        pip_record_id=pip.id,
                        updated_by=current_user.username,
                    )
                except Exception:
                    pass

                session.pop('wizard_step', None)
                session.pop('pip_data', None)

                flash("PIP created successfully!", "success")
                return redirect(url_for('dashboard'))

            except Exception as e:
                print(f"[ERROR] Failed to save PIP: {e}")
                flash(f"Error creating PIP: {str(e)}", "danger")

        session['pip_data'] = data
        if not wizard_errors and step < 5:
            session['wizard_step'] = step + 1
            return redirect(url_for('pip.create_pip_wizard'))

    selected_employee_id = None
    try:
        if data.get('employee_id'):
            selected_employee_id = int(data.get('employee_id'))
    except (TypeError, ValueError):
        selected_employee_id = None

    employees = _active_employee_query(include_employee_id=selected_employee_id).all() if step == 1 else []
    max_allowed = _max_wizard_step(data)
    draft = get_active_draft_for_user(current_user.id)

    return render_template(
        'create_pip_wizard.html',
        step=step,
        draft=draft,
        data=data,
        wizard_errors=wizard_errors,
        employees=employees,
        max_allowed_step=max_allowed,
        auto_review_populated=bool(data.get('auto_review_populated')),
        auto_review_date=data.get('auto_review_date')
    )


@pip_bp.route('/validate_wizard_step', methods=['POST'])
@login_required
def validate_wizard_step():
    step = int(request.form.get("step", 1))
    errors = {}

    if step == 1:
        employee_id = request.form.get("employee_id")
        if not employee_id:
            errors["employee_id"] = "Please select an employee."
        else:
            try:
                employee_id_int = int(employee_id)
            except (TypeError, ValueError):
                employee_id_int = None

            if not employee_id_int:
                errors["employee_id"] = "Please select a valid employee."
            else:
                employee = _active_employee_query(include_employee_id=employee_id_int).filter(Employee.id == employee_id_int).first()
                if not employee:
                    errors["employee_id"] = "Please select a valid employee."
                elif employee.is_leaver:
                    errors["employee_id"] = "You cannot start a new PIP for an employee who is marked as a leaver."

    elif step == 2:
        if not (request.form.get("concerns", "").strip()):
            errors["concerns"] = "Please describe the concern."
        if not (request.form.get("concern_category", "").strip()):
            errors["concern_category"] = "Please select a concern category."
        if not (request.form.get("severity", "").strip()):
            errors["severity"] = "Please select severity."
        if not (request.form.get("frequency", "").strip()):
            errors["frequency"] = "Please select frequency."

    elif step == 3:
        if not (request.form.get("start_date", "").strip()):
            errors["start_date"] = "Please enter a start date."

    elif step == 4:
        meeting_date = (request.form.get("capability_meeting_date") or request.form.get("meeting_date") or "").strip()
        meeting_time = (request.form.get("capability_meeting_time") or request.form.get("meeting_time") or "").strip()
        meeting_venue = (request.form.get("capability_meeting_venue") or request.form.get("meeting_venue") or "").strip()

        if not meeting_date:
            errors["capability_meeting_date"] = "Please enter a meeting date."
        if not meeting_time:
            errors["capability_meeting_time"] = "Please enter a meeting time."
        if not meeting_venue:
            errors["capability_meeting_venue"] = "Please enter a meeting venue."

    elif step == 5:
        actions = [a.strip() for a in request.form.getlist("action_plan_items[]") if a.strip()]
        if not actions:
            errors["action_plan_items"] = "Please add at least one action item."

    return jsonify({"success": not errors, "errors": errors})


@pip_bp.route('/suggest_actions_ai', methods=['POST'])
@login_required
def suggest_actions_ai():
    if not _has_recent_ai_consent("pip_advice"):
        return jsonify({
            "success": False,
            "message": "AI consent required before generating suggestions."
        }), 403

    data = request.get_json(silent=True) or {}
    concerns = (data.get('concerns') or '').strip()
    severity = (data.get('severity') or '').strip()
    frequency = (data.get('frequency') or '').strip()
    tags = (data.get('tags') or '').strip()
    category = (data.get('category') or '').strip()

    try:
        prior_actions = _pick_actions_from_templates(category, severity)
    except Exception:
        prior_actions = []

    def _dedupe_clean(items, cap=None):
        out, seen = [], set()
        for x in (items or []):
            s = (x or "").strip()
            if not s:
                continue
            k = s.lower()
            if k not in seen:
                out.append(s)
                seen.add(k)
            if cap and len(out) >= cap:
                break
        return out

    sys_msg = (
        "You are an HR advisor in the UK.\n"
        "Return ONLY valid JSON with two arrays:\n"
        '{"actions": ["short concrete manager actions"], "next_up": ["quick follow-ups or escalations"]}.\n'
        "Actions must be specific, measurable where possible, supportive, and suitable for a PIP context.\n"
        "No prose, no markdown, JSON only."
    )

    prior_block = ""
    if prior_actions:
        import json as _json
        prior_block = "Seed actions (consider and adapt as appropriate): " + _json.dumps(
            prior_actions, ensure_ascii=False
        )

    user_msg = f"""
Concern Category: {category or "[unspecified]"}
Concerns: {concerns or "[none]"}
Tags: {tags or "[none]"}
Severity: {severity or "[unspecified]"}
Frequency: {frequency or "[unspecified]"}

{prior_block}

Rules:
- Provide 3–5 'actions' tailored to the inputs.
- Provide 2–4 'next_up' items.
- Keep each item under 140 characters.
- JSON ONLY.
"""

    actions_llm, next_up_llm, raw = [], [], ""

    def _extract_text_from_choice(choice):
        content = getattr(choice.message, "content", "")
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts = []
            for part in content:
                if isinstance(part, dict):
                    text = part.get("text")
                    if isinstance(text, dict):
                        parts.append(str(text.get("value", "")))
                    elif text is not None:
                        parts.append(str(text))
                else:
                    parts.append(str(part))
            return "".join(parts)
        return str(content or "")

    try:
        client = get_openai_client()
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": sys_msg},
                {"role": "user", "content": user_msg},
            ],
            temperature=0.5,
            max_tokens=300,
        )

        raw = _extract_text_from_choice(resp.choices[0]).strip()

        import json as _json, re as _re
        m = _re.search(r"\{[\s\S]*\}", raw)
        json_str = m.group(0) if m else raw
        payload = _json.loads(json_str)

        actions_llm = payload.get("actions", []) or []
        next_up_llm = payload.get("next_up", []) or []
    except Exception as exc:
        message = _friendly_ai_error_message(exc)
        return jsonify({
            "success": False,
            "message": message,
            "actions": [],
            "next_up": [],
        }), 500

    merged_actions = _dedupe_clean(actions_llm, cap=None)
    if prior_actions:
        merged_actions = _dedupe_clean(prior_actions + merged_actions, cap=8)

    next_up = _dedupe_clean(next_up_llm, cap=None)

    tag_list = [t.strip().lower() for t in tags.split(",")] if tags else []
    cat = (category or "").lower()
    sev = (severity or "").lower()
    freq = (frequency or "").lower()

    enrich = []
    if 'lateness' in tag_list or 'timekeeping' in cat:
        enrich += [
            "Daily start-time check-ins for 2 weeks",
            "Agree punctuality targets; log variances",
        ]
    if 'conduct' in tag_list or cat == 'conduct':
        enrich += [
            "Reference conduct policy; document conversations",
            "Book values/behaviour refresher",
        ]
    if 'performance' in cat or ('missed deadlines' in (tags or '').lower()):
        enrich += [
            "Weekly milestones with due dates",
            "Stand-up updates Mon/Wed/Fri",
        ]
    if sev == 'high':
        enrich += ["Escalate to formal stage if no progress"]
    if freq in ('frequent', 'persistent'):
        enrich += ["Increase monitoring and assign a buddy/mentor"]

    next_up = _dedupe_clean(next_up + enrich, cap=8)

    merged_actions = merged_actions[:8] if merged_actions else []
    next_up = next_up[:8] if next_up else []

    try:
        log_security_event(
            event_type="PIP AI Suggestions Generated",
            notes="Action suggestions generated in PIP wizard",
            updated_by=current_user.username,
        )
    except Exception:
        pass

    return jsonify({"success": True, "actions": merged_actions, "next_up": next_up}), 200


@pip_bp.route('/dismiss_draft', methods=['POST'])
@login_required
def dismiss_draft():
    draft = DraftPIP.query.filter_by(user_id=current_user.id, is_dismissed=False).first()
    if draft:
        draft.is_dismissed = True
        draft.updated_at = datetime.now(timezone.utc)
        db.session.commit()

        try:
            log_security_event(
                event_type="PIP Draft Dismissed",
                notes=f"PIP draft dismissed by {current_user.username}",
                updated_by=current_user.username,
            )
        except Exception:
            pass

        return jsonify({"success": True})
    return jsonify({"success": False, "message": "No active draft found"}), 404


@pip_bp.route('/save_pip_draft', methods=['POST'])
@login_required
def save_pip_draft():
    try:
        data = {
            'employee_id': request.form.get('employee_id'),
            'draft_name': request.form.get('draft_name', '').strip(),
            'concerns': request.form.get('concerns', '').strip(),
            'concern_category': request.form.get('concern_category', '').strip(),
            'severity': request.form.get('severity', '').strip(),
            'frequency': request.form.get('frequency', '').strip(),
            'concern_tags': request.form.get('concern_tags', '').strip(),
            'start_date': request.form.get('start_date'),
            'review_date': request.form.get('review_date'),
            'capability_meeting_date': request.form.get('capability_meeting_date'),
            'capability_meeting_time': request.form.get('capability_meeting_time'),
            'capability_meeting_venue': request.form.get('capability_meeting_venue'),
            'action_plan_items': request.form.getlist('action_plan_items[]')
        }
        cleaned_data = {k: v for k, v in data.items() if v not in [None, '', []]}

        employee_id = cleaned_data.get('employee_id')
        if employee_id:
            try:
                employee_id_int = int(employee_id)
                employee = _scoped_employee_query().filter(Employee.id == employee_id_int).first()
                if not employee:
                    return jsonify({"success": False, "message": "Invalid employee selection."}), 403
            except (TypeError, ValueError):
                return jsonify({"success": False, "message": "Invalid employee selection."}), 400

        existing_draft = DraftPIP.query.filter_by(user_id=current_user.id, is_dismissed=False).first()
        if existing_draft:
            db.session.delete(existing_draft)
            db.session.commit()

        new_draft = DraftPIP(
            user_id=current_user.id,
            data=cleaned_data,
            step=session.get('wizard_step', 1),
            is_dismissed=False,
            updated_at=datetime.now(timezone.utc)
        )
        db.session.add(new_draft)
        db.session.commit()

        try:
            log_security_event(
                event_type="PIP Draft Saved",
                notes=f"PIP draft saved at step {session.get('wizard_step', 1)}",
                updated_by=current_user.username,
            )
        except Exception:
            pass

        return jsonify({"success": True, "message": "Draft saved."})
    except Exception as e:
        print(f"[ERROR] Failed to save draft: {e}")
        return jsonify({"success": False, "message": "Failed to save draft."}), 500


@pip_bp.route('/pip/wizard/resume', methods=['GET'])
@login_required
def pip_wizard_resume():
    draft = get_active_draft_for_user(current_user.id)
    if not draft or not draft.data:
        flash("No active draft to resume.", "warning")
        return redirect(url_for('dashboard'))

    employee_id = draft.data.get("employee_id")
    if employee_id:
        try:
            employee_id_int = int(employee_id)
            employee = _scoped_employee_query().filter(Employee.id == employee_id_int).first()
            if not employee:
                flash("You no longer have access to the employee on this draft.", "warning")
                return redirect(url_for('dashboard'))
        except (TypeError, ValueError):
            flash("The saved draft contains an invalid employee reference.", "warning")
            return redirect(url_for('dashboard'))

    session['pip_data'] = dict(draft.data)
    session['wizard_step'] = _max_wizard_step(session['pip_data'])

    try:
        log_security_event(
            event_type="PIP Draft Resumed",
            notes=f"PIP draft resumed at step {session['wizard_step']}",
            updated_by=current_user.username,
        )
    except Exception:
        pass

    return redirect(url_for('pip.create_pip_wizard'))
