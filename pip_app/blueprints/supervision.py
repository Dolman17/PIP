from __future__ import annotations

from datetime import datetime, timedelta

from flask import Blueprint, abort, flash, redirect, render_template, request, session, url_for
from flask_login import current_user, login_required
from sqlalchemy import func, or_
from sqlalchemy.orm import joinedload

from models import (
    Employee,
    SupervisionAction,
    SupervisionRecord,
    SupervisionTemplate,
    SupervisionTemplateQuestion,
    SupervisionTimelineEvent,
    db,
)
from pip_app.security import require_employee_access, scoped_employee_query
from pip_app.services.module_settings import get_enabled_modules
from pip_app.services.time_utils import today_local


supervision_bp = Blueprint(
    "supervision",
    __name__,
    url_prefix="/supervision",
)


MEETING_TYPES = [
    "Supervision",
    "1:1",
    "Wellbeing Check-in",
    "Performance Support",
    "Probation Check-in",
    "Return to Work Follow-up",
    "Ad-hoc Management Check-in",
]

SUPERVISION_STATUSES = [
    "Draft",
    "Scheduled",
    "Completed",
    "Cancelled",
    "Overdue",
]

ACTION_STATUSES = [
    "Open",
    "Completed",
    "Carried Forward",
    "Cancelled",
]

ACTION_OWNER_TYPES = [
    "Employee",
    "Manager",
    "HR",
    "Other",
]


def _set_active_module():
    session["active_module"] = "Supervision"


@supervision_bp.before_request
@login_required
def before_request():
    _set_active_module()


def _parse_date(value):
    value = (value or "").strip()
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None


def _clean(value):
    value = (value or "").strip()
    return value or None


def _module_enabled():
    enabled_modules = get_enabled_modules(user=current_user)
    return enabled_modules.get("supervision", True)


def _scoped_employee_query():
    return scoped_employee_query(Employee.query, Employee)


def _active_employee_query():
    return (
        _scoped_employee_query()
        .filter(Employee.is_leaver.is_(False))
        .order_by(Employee.last_name.asc(), Employee.first_name.asc())
    )


def _scoped_supervision_query():
    query = SupervisionRecord.query.join(Employee)

    if getattr(current_user, "organisation_id", None):
        query = query.filter(Employee.organisation_id == current_user.organisation_id)

    if current_user.admin_level == 0:
        if current_user.team_id:
            query = query.filter(Employee.team_id == current_user.team_id)
        else:
            query = query.filter(Employee.id == -1)

    return query


def _scoped_action_query():
    query = SupervisionAction.query.join(Employee)

    if getattr(current_user, "organisation_id", None):
        query = query.filter(Employee.organisation_id == current_user.organisation_id)

    if current_user.admin_level == 0:
        if current_user.team_id:
            query = query.filter(Employee.team_id == current_user.team_id)
        else:
            query = query.filter(Employee.id == -1)

    return query


def _get_supervision_or_404(supervision_id):
    supervision = (
        _scoped_supervision_query()
        .options(
            joinedload(SupervisionRecord.employee),
            joinedload(SupervisionRecord.manager),
            joinedload(SupervisionRecord.actions),
            joinedload(SupervisionRecord.timeline_events),
        )
        .filter(SupervisionRecord.id == supervision_id)
        .first_or_404()
    )
    require_employee_access(supervision.employee)
    return supervision


def _get_action_or_404(action_id):
    action = (
        _scoped_action_query()
        .options(
            joinedload(SupervisionAction.employee),
            joinedload(SupervisionAction.supervision),
        )
        .filter(SupervisionAction.id == action_id)
        .first_or_404()
    )
    require_employee_access(action.employee)
    return action


def _log_supervision_event(supervision, event_type, notes=None):
    event = SupervisionTimelineEvent(
        supervision_id=supervision.id,
        event_type=event_type,
        notes=notes,
        updated_by=getattr(current_user, "username", None),
    )
    db.session.add(event)


def _sync_overdue_statuses():
    today = today_local()

    query = _scoped_supervision_query().filter(
        SupervisionRecord.status == "Scheduled",
        SupervisionRecord.meeting_date < today,
    )

    changed = False
    for record in query.all():
        record.status = "Overdue"
        record.updated_by = getattr(current_user, "username", None)
        changed = True

    if changed:
        db.session.commit()


def _seed_default_template_if_missing():
    if getattr(current_user, "organisation_id", None):
        organisation_id = current_user.organisation_id
    else:
        organisation_id = None

    existing = SupervisionTemplate.query.filter_by(
        organisation_id=organisation_id,
        name="Standard Supervision / 1:1",
    ).first()

    if existing:
        return existing

    template = SupervisionTemplate(
        organisation_id=organisation_id,
        name="Standard Supervision / 1:1",
        description="Default supervision template covering wellbeing, performance, conduct, workload, development, support, and actions.",
        meeting_type="Supervision",
        is_active=True,
        sort_order=1,
    )
    db.session.add(template)
    db.session.flush()

    questions = [
        ("Wellbeing", "How is the employee feeling at work?", "textarea", 1),
        ("Workload", "How manageable is the current workload?", "textarea", 2),
        ("Performance", "What performance progress or concerns should be discussed?", "textarea", 3),
        ("Conduct / Standards", "Are there any conduct, standards, or compliance matters to record?", "textarea", 4),
        ("Training & Development", "What training, development, or coaching support is needed?", "textarea", 5),
        ("Achievements", "What has gone well since the last supervision?", "textarea", 6),
        ("Concerns / Barriers", "Are there any barriers, concerns, or risks to note?", "textarea", 7),
        ("Support Agreed", "What support has been agreed?", "textarea", 8),
        ("Actions", "What actions should be followed up?", "textarea", 9),
        ("Next Meeting", "When should the next supervision take place?", "date", 10),
    ]

    for section, question_text, field_type, sort_order in questions:
        db.session.add(
            SupervisionTemplateQuestion(
                template_id=template.id,
                section=section,
                question_text=question_text,
                field_type=field_type,
                is_required=False,
                sort_order=sort_order,
                is_active=True,
            )
        )

    db.session.commit()
    return template


def _apply_supervision_form(record, employee):
    record.organisation_id = employee.organisation_id or getattr(current_user, "organisation_id", None)
    record.employee_id = employee.id

    manager_user_id = request.form.get("manager_user_id", type=int)
    record.manager_user_id = manager_user_id or current_user.id

    record.meeting_title = _clean(request.form.get("meeting_title"))
    record.meeting_type = _clean(request.form.get("meeting_type")) or "Supervision"

    meeting_date = _parse_date(request.form.get("meeting_date"))
    if meeting_date:
        record.meeting_date = meeting_date

    record.meeting_time = _clean(request.form.get("meeting_time"))
    record.location = _clean(request.form.get("location"))

    record.status = _clean(request.form.get("status")) or record.status or "Scheduled"

    record.supervision_period_start = _parse_date(request.form.get("supervision_period_start"))
    record.supervision_period_end = _parse_date(request.form.get("supervision_period_end"))

    record.wellbeing_summary = _clean(request.form.get("wellbeing_summary"))
    record.performance_summary = _clean(request.form.get("performance_summary"))
    record.conduct_summary = _clean(request.form.get("conduct_summary"))
    record.training_summary = _clean(request.form.get("training_summary"))
    record.workload_summary = _clean(request.form.get("workload_summary"))
    record.achievements_summary = _clean(request.form.get("achievements_summary"))
    record.concerns_summary = _clean(request.form.get("concerns_summary"))

    record.employee_comments = _clean(request.form.get("employee_comments"))
    record.manager_comments = _clean(request.form.get("manager_comments"))
    record.manager_confidential_notes = _clean(request.form.get("manager_confidential_notes"))

    record.agreed_support = _clean(request.form.get("agreed_support"))
    record.overall_summary = _clean(request.form.get("overall_summary"))
    record.next_meeting_date = _parse_date(request.form.get("next_meeting_date"))

    record.updated_by = getattr(current_user, "username", None)

    if record.status == "Completed" and not record.completed_at:
        record.completed_at = datetime.utcnow()

    if record.status == "Cancelled" and not record.cancelled_at:
        record.cancelled_at = datetime.utcnow()


def _add_actions_from_form(supervision, employee):
    descriptions = request.form.getlist("action_description[]")
    owner_types = request.form.getlist("action_owner_type[]")
    owner_names = request.form.getlist("action_owner_name[]")
    due_dates = request.form.getlist("action_due_date[]")

    created = 0

    for idx, description in enumerate(descriptions):
        description = _clean(description)
        if not description:
            continue

        owner_type = owner_types[idx] if idx < len(owner_types) else "Employee"
        owner_name = owner_names[idx] if idx < len(owner_names) else None
        due_date_raw = due_dates[idx] if idx < len(due_dates) else None

        action = SupervisionAction(
            supervision_id=supervision.id,
            organisation_id=employee.organisation_id or getattr(current_user, "organisation_id", None),
            employee_id=employee.id,
            description=description,
            owner_type=_clean(owner_type) or "Employee",
            owner_name=_clean(owner_name),
            due_date=_parse_date(due_date_raw),
            status="Open",
        )
        db.session.add(action)
        created += 1

    return created


@supervision_bp.route("/dashboard")
def dashboard():
    if not _module_enabled():
        flash("The Supervision module is currently disabled.", "warning")
        return redirect(url_for("main.home"))

    _sync_overdue_statuses()

    today = today_local()
    next_14_days = today + timedelta(days=14)
    missing_cutoff = today - timedelta(days=60)

    base = _scoped_supervision_query()

    scheduled_count = base.filter(SupervisionRecord.status == "Scheduled").count()
    overdue_count = base.filter(SupervisionRecord.status == "Overdue").count()
    completed_count = base.filter(SupervisionRecord.status == "Completed").count()

    upcoming = (
        base.filter(
            SupervisionRecord.status == "Scheduled",
            SupervisionRecord.meeting_date >= today,
            SupervisionRecord.meeting_date <= next_14_days,
        )
        .order_by(SupervisionRecord.meeting_date.asc())
        .limit(10)
        .all()
    )

    overdue = (
        base.filter(SupervisionRecord.status == "Overdue")
        .order_by(SupervisionRecord.meeting_date.asc())
        .limit(10)
        .all()
    )

    recent_completed = (
        base.filter(SupervisionRecord.status == "Completed")
        .order_by(SupervisionRecord.completed_at.desc().nullslast(), SupervisionRecord.meeting_date.desc())
        .limit(10)
        .all()
    )

    open_actions = (
        _scoped_action_query()
        .filter(SupervisionAction.status.in_(["Open", "Carried Forward"]))
        .order_by(SupervisionAction.due_date.asc().nullslast())
        .limit(10)
        .all()
    )

    actions_due_soon_count = (
        _scoped_action_query()
        .filter(
            SupervisionAction.status.in_(["Open", "Carried Forward"]),
            SupervisionAction.due_date.isnot(None),
            SupervisionAction.due_date <= next_14_days,
        )
        .count()
    )

    active_employees = _active_employee_query().all()
    missing_supervision = []

    for employee in active_employees:
        latest = (
            _scoped_supervision_query()
            .filter(SupervisionRecord.employee_id == employee.id)
            .order_by(SupervisionRecord.meeting_date.desc())
            .first()
        )
        if latest is None or latest.meeting_date < missing_cutoff:
            missing_supervision.append(
                {
                    "employee": employee,
                    "latest": latest,
                }
            )

    missing_supervision = missing_supervision[:10]

    stats = {
        "scheduled": scheduled_count,
        "overdue": overdue_count,
        "completed": completed_count,
        "open_actions": _scoped_action_query().filter(
            SupervisionAction.status.in_(["Open", "Carried Forward"])
        ).count(),
        "actions_due_soon": actions_due_soon_count,
        "missing_supervision": len(missing_supervision),
    }

    return render_template(
        "supervision/dashboard.html",
        stats=stats,
        upcoming=upcoming,
        overdue=overdue,
        recent_completed=recent_completed,
        open_actions=open_actions,
        missing_supervision=missing_supervision,
        today=today,
        next_14_days=next_14_days,
    )


@supervision_bp.route("/list")
def list_supervisions():
    if not _module_enabled():
        flash("The Supervision module is currently disabled.", "warning")
        return redirect(url_for("main.home"))

    _sync_overdue_statuses()

    search = (request.args.get("search") or "").strip()
    status = (request.args.get("status") or "").strip()
    meeting_type = (request.args.get("meeting_type") or "").strip()
    manager_user_id = request.args.get("manager_user_id", type=int)
    date_from = _parse_date(request.args.get("date_from"))
    date_to = _parse_date(request.args.get("date_to"))
    overdue_only = (request.args.get("overdue_only") or "").strip()
    open_actions_only = (request.args.get("open_actions_only") or "").strip()

    query = _scoped_supervision_query().options(
        joinedload(SupervisionRecord.employee),
        joinedload(SupervisionRecord.manager),
        joinedload(SupervisionRecord.actions),
    )

    if search:
        like = f"%{search}%"
        query = query.filter(
            or_(
                Employee.first_name.ilike(like),
                Employee.last_name.ilike(like),
                Employee.job_title.ilike(like),
                Employee.service.ilike(like),
                SupervisionRecord.meeting_title.ilike(like),
                SupervisionRecord.meeting_type.ilike(like),
                SupervisionRecord.overall_summary.ilike(like),
                SupervisionRecord.concerns_summary.ilike(like),
            )
        )

    if status:
        query = query.filter(SupervisionRecord.status == status)

    if meeting_type:
        query = query.filter(SupervisionRecord.meeting_type == meeting_type)

    if manager_user_id:
        query = query.filter(SupervisionRecord.manager_user_id == manager_user_id)

    if date_from:
        query = query.filter(SupervisionRecord.meeting_date >= date_from)

    if date_to:
        query = query.filter(SupervisionRecord.meeting_date <= date_to)

    if overdue_only == "1":
        query = query.filter(SupervisionRecord.status == "Overdue")

    if open_actions_only == "1":
        query = query.join(SupervisionAction).filter(
            SupervisionAction.status.in_(["Open", "Carried Forward"])
        )

    supervisions = (
        query.order_by(SupervisionRecord.meeting_date.desc(), SupervisionRecord.id.desc())
        .all()
    )

    filters = {
        "search": search,
        "status": status,
        "meeting_type": meeting_type,
        "manager_user_id": manager_user_id,
        "date_from": request.args.get("date_from") or "",
        "date_to": request.args.get("date_to") or "",
        "overdue_only": overdue_only,
        "open_actions_only": open_actions_only,
    }

    managers = (
        db.session.query(SupervisionRecord.manager_user_id)
        .filter(SupervisionRecord.manager_user_id.isnot(None))
        .distinct()
        .all()
    )

    return render_template(
        "supervision/list.html",
        supervisions=supervisions,
        filters=filters,
        meeting_types=MEETING_TYPES,
        statuses=SUPERVISION_STATUSES,
        managers=managers,
    )


@supervision_bp.route("/employee/<int:employee_id>")
def employee_supervisions(employee_id):
    employee = _scoped_employee_query().filter(Employee.id == employee_id).first_or_404()
    require_employee_access(employee)

    supervisions = (
        _scoped_supervision_query()
        .filter(SupervisionRecord.employee_id == employee.id)
        .order_by(SupervisionRecord.meeting_date.desc())
        .all()
    )

    actions = (
        _scoped_action_query()
        .filter(
            SupervisionAction.employee_id == employee.id,
            SupervisionAction.status.in_(["Open", "Carried Forward"]),
        )
        .order_by(SupervisionAction.due_date.asc().nullslast())
        .all()
    )

    return render_template(
        "supervision/employee.html",
        employee=employee,
        supervisions=supervisions,
        actions=actions,
    )


@supervision_bp.route("/create/<int:employee_id>", methods=["GET", "POST"])
def create_supervision(employee_id):
    if not _module_enabled():
        flash("The Supervision module is currently disabled.", "warning")
        return redirect(url_for("main.home"))

    employee = _active_employee_query().filter(Employee.id == employee_id).first_or_404()
    require_employee_access(employee)

    _seed_default_template_if_missing()

    if request.method == "POST":
        meeting_date = _parse_date(request.form.get("meeting_date"))
        if not meeting_date:
            flash("Meeting date is required.", "error")
            return render_template(
                "supervision/create.html",
                employee=employee,
                meeting_types=MEETING_TYPES,
                statuses=SUPERVISION_STATUSES,
                owner_types=ACTION_OWNER_TYPES,
                form_data=request.form,
            )

        supervision = SupervisionRecord(
            organisation_id=employee.organisation_id or getattr(current_user, "organisation_id", None),
            employee_id=employee.id,
            manager_user_id=current_user.id,
            meeting_date=meeting_date,
            status="Scheduled",
            created_by=getattr(current_user, "username", None),
            updated_by=getattr(current_user, "username", None),
        )

        _apply_supervision_form(supervision, employee)
        db.session.add(supervision)
        db.session.flush()

        action_count = _add_actions_from_form(supervision, employee)

        _log_supervision_event(
            supervision,
            "Supervision Created",
            f"Supervision record created. {action_count} action(s) added.",
        )

        db.session.commit()

        flash("Supervision / 1:1 record created.", "success")
        return redirect(url_for("supervision.detail", id=supervision.id))

    return render_template(
        "supervision/create.html",
        employee=employee,
        meeting_types=MEETING_TYPES,
        statuses=SUPERVISION_STATUSES,
        owner_types=ACTION_OWNER_TYPES,
        form_data={},
    )


@supervision_bp.route("/<int:id>")
def detail(id):
    supervision = _get_supervision_or_404(id)

    return render_template(
        "supervision/detail.html",
        supervision=supervision,
        employee=supervision.employee,
        owner_types=ACTION_OWNER_TYPES,
        action_statuses=ACTION_STATUSES,
    )


@supervision_bp.route("/<int:id>/edit", methods=["GET", "POST"])
def edit(id):
    supervision = _get_supervision_or_404(id)
    employee = supervision.employee

    if request.method == "POST":
        _apply_supervision_form(supervision, employee)

        action_count = _add_actions_from_form(supervision, employee)

        _log_supervision_event(
            supervision,
            "Supervision Updated",
            f"Supervision record updated. {action_count} new action(s) added.",
        )

        db.session.commit()

        flash("Supervision / 1:1 record updated.", "success")
        return redirect(url_for("supervision.detail", id=supervision.id))

    return render_template(
        "supervision/edit.html",
        supervision=supervision,
        employee=employee,
        meeting_types=MEETING_TYPES,
        statuses=SUPERVISION_STATUSES,
        owner_types=ACTION_OWNER_TYPES,
    )


@supervision_bp.route("/<int:id>/complete", methods=["POST"])
def complete(id):
    supervision = _get_supervision_or_404(id)

    supervision.status = "Completed"
    supervision.completed_at = datetime.utcnow()
    supervision.updated_by = getattr(current_user, "username", None)

    _log_supervision_event(supervision, "Supervision Completed", "Supervision marked as completed.")

    db.session.commit()

    flash("Supervision marked as completed.", "success")
    return redirect(url_for("supervision.detail", id=supervision.id))


@supervision_bp.route("/<int:id>/cancel", methods=["POST"])
def cancel(id):
    supervision = _get_supervision_or_404(id)

    supervision.status = "Cancelled"
    supervision.cancelled_at = datetime.utcnow()
    supervision.updated_by = getattr(current_user, "username", None)

    _log_supervision_event(supervision, "Supervision Cancelled", "Supervision marked as cancelled.")

    db.session.commit()

    flash("Supervision marked as cancelled.", "success")
    return redirect(url_for("supervision.detail", id=supervision.id))


@supervision_bp.route("/<int:id>/actions/add", methods=["POST"])
def add_action(id):
    supervision = _get_supervision_or_404(id)
    employee = supervision.employee

    description = _clean(request.form.get("description"))
    if not description:
        flash("Action description is required.", "error")
        return redirect(url_for("supervision.detail", id=supervision.id))

    action = SupervisionAction(
        supervision_id=supervision.id,
        organisation_id=employee.organisation_id or getattr(current_user, "organisation_id", None),
        employee_id=employee.id,
        description=description,
        owner_type=_clean(request.form.get("owner_type")) or "Employee",
        owner_name=_clean(request.form.get("owner_name")),
        due_date=_parse_date(request.form.get("due_date")),
        status="Open",
    )

    db.session.add(action)
    _log_supervision_event(supervision, "Action Added", description)
    db.session.commit()

    flash("Action added.", "success")
    return redirect(url_for("supervision.detail", id=supervision.id))


@supervision_bp.route("/actions/<int:action_id>/edit", methods=["POST"])
def edit_action(action_id):
    action = _get_action_or_404(action_id)

    description = _clean(request.form.get("description"))
    if not description:
        flash("Action description is required.", "error")
        return redirect(url_for("supervision.detail", id=action.supervision_id))

    action.description = description
    action.owner_type = _clean(request.form.get("owner_type")) or action.owner_type or "Employee"
    action.owner_name = _clean(request.form.get("owner_name"))
    action.due_date = _parse_date(request.form.get("due_date"))
    action.status = _clean(request.form.get("status")) or action.status
    action.completion_notes = _clean(request.form.get("completion_notes"))

    if action.status == "Completed" and not action.completed_at:
        action.completed_at = datetime.utcnow()

    _log_supervision_event(action.supervision, "Action Updated", action.description)

    db.session.commit()

    flash("Action updated.", "success")
    return redirect(url_for("supervision.detail", id=action.supervision_id))


@supervision_bp.route("/actions/<int:action_id>/complete", methods=["POST"])
def complete_action(action_id):
    action = _get_action_or_404(action_id)

    action.status = "Completed"
    action.completed_at = datetime.utcnow()
    action.completion_notes = _clean(request.form.get("completion_notes")) or action.completion_notes

    _log_supervision_event(action.supervision, "Action Completed", action.description)

    db.session.commit()

    flash("Action completed.", "success")
    return redirect(url_for("supervision.detail", id=action.supervision_id))


@supervision_bp.route("/actions/<int:action_id>/carry-forward", methods=["POST"])
def carry_forward_action(action_id):
    action = _get_action_or_404(action_id)

    action.status = "Carried Forward"
    action.due_date = _parse_date(request.form.get("due_date")) or action.due_date

    _log_supervision_event(action.supervision, "Action Carried Forward", action.description)

    db.session.commit()

    flash("Action carried forward.", "success")
    return redirect(url_for("supervision.detail", id=action.supervision_id))


@supervision_bp.route("/templates")
def templates():
    if not current_user.is_admin():
        abort(403)

    _seed_default_template_if_missing()

    organisation_id = getattr(current_user, "organisation_id", None)

    query = SupervisionTemplate.query
    if organisation_id:
        query = query.filter(SupervisionTemplate.organisation_id == organisation_id)
    else:
        query = query.filter(SupervisionTemplate.organisation_id.is_(None))

    templates = query.order_by(SupervisionTemplate.sort_order.asc(), SupervisionTemplate.name.asc()).all()

    return render_template(
        "supervision/templates.html",
        templates=templates,
    )


@supervision_bp.route("/templates/create", methods=["GET", "POST"])
def create_template():
    if not current_user.is_admin():
        abort(403)

    if request.method == "POST":
        template = SupervisionTemplate(
            organisation_id=getattr(current_user, "organisation_id", None),
            name=_clean(request.form.get("name")) or "Untitled Template",
            description=_clean(request.form.get("description")),
            meeting_type=_clean(request.form.get("meeting_type")) or "Supervision",
            is_active=bool(request.form.get("is_active")),
            sort_order=request.form.get("sort_order", type=int) or 0,
        )

        db.session.add(template)
        db.session.flush()

        sections = request.form.getlist("question_section[]")
        questions = request.form.getlist("question_text[]")
        help_texts = request.form.getlist("question_help_text[]")
        field_types = request.form.getlist("question_field_type[]")

        for idx, question_text in enumerate(questions):
            question_text = _clean(question_text)
            if not question_text:
                continue

            db.session.add(
                SupervisionTemplateQuestion(
                    template_id=template.id,
                    section=_clean(sections[idx] if idx < len(sections) else None) or "General",
                    question_text=question_text,
                    help_text=_clean(help_texts[idx] if idx < len(help_texts) else None),
                    field_type=_clean(field_types[idx] if idx < len(field_types) else None) or "textarea",
                    is_required=False,
                    is_active=True,
                    sort_order=idx + 1,
                )
            )

        db.session.commit()

        flash("Supervision template created.", "success")
        return redirect(url_for("supervision.templates"))

    return render_template(
        "supervision/template_form.html",
        template=None,
        meeting_types=MEETING_TYPES,
    )


@supervision_bp.route("/templates/<int:id>/edit", methods=["GET", "POST"])
def edit_template(id):
    if not current_user.is_admin():
        abort(403)

    template = SupervisionTemplate.query.get_or_404(id)

    if getattr(current_user, "organisation_id", None):
        if template.organisation_id != current_user.organisation_id:
            abort(403)

    if request.method == "POST":
        template.name = _clean(request.form.get("name")) or template.name
        template.description = _clean(request.form.get("description"))
        template.meeting_type = _clean(request.form.get("meeting_type")) or template.meeting_type
        template.is_active = bool(request.form.get("is_active"))
        template.sort_order = request.form.get("sort_order", type=int) or 0

        for question in list(template.questions):
            db.session.delete(question)

        db.session.flush()

        sections = request.form.getlist("question_section[]")
        questions = request.form.getlist("question_text[]")
        help_texts = request.form.getlist("question_help_text[]")
        field_types = request.form.getlist("question_field_type[]")

        for idx, question_text in enumerate(questions):
            question_text = _clean(question_text)
            if not question_text:
                continue

            db.session.add(
                SupervisionTemplateQuestion(
                    template_id=template.id,
                    section=_clean(sections[idx] if idx < len(sections) else None) or "General",
                    question_text=question_text,
                    help_text=_clean(help_texts[idx] if idx < len(help_texts) else None),
                    field_type=_clean(field_types[idx] if idx < len(field_types) else None) or "textarea",
                    is_required=False,
                    is_active=True,
                    sort_order=idx + 1,
                )
            )

        db.session.commit()

        flash("Supervision template updated.", "success")
        return redirect(url_for("supervision.templates"))

    return render_template(
        "supervision/template_form.html",
        template=template,
        meeting_types=MEETING_TYPES,
    )