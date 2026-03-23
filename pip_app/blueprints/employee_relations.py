from datetime import datetime
import os
from uuid import uuid4

from flask import (
    Blueprint,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
    send_file,
    abort,
)
from flask_login import current_user, login_required
from werkzeug.utils import secure_filename

from pip_app.extensions import db
from pip_app.models import (
    Employee,
    EmployeeRelationsCase,
    EmployeeRelationsTimelineEvent,
    EmployeeRelationsMeeting,
    EmployeeRelationsAttachment,
    EmployeeRelationsDocument,
    EmployeeRelationsPolicyText,
)
from pip_app.services.ai_utils import generate_employee_relations_advice
from pip_app.services.document_utils import (
    BASE_DIR,
    html_to_docx_bytes,
    sanitize_html,
)
from pip_app.services.employee_relations_constants import (
    ATTACHMENT_CATEGORIES,
    CASE_STAGES,
    CASE_STATUSES,
    CASE_TYPES,
    DISCIPLINARY_CATEGORIES,
    DISCIPLINARY_SANCTIONS,
    ER_DOCUMENT_TYPES,
    GRIEVANCE_CATEGORIES,
    GRIEVANCE_OUTCOMES,
    MEETING_TYPES,
    PRIORITY_LEVELS,
)

employee_relations_bp = Blueprint(
    "employee_relations",
    __name__,
    url_prefix="/employee-relations",
)

ER_UPLOAD_DIR = os.path.join(BASE_DIR, "uploads", "employee_relations")
ER_DOCUMENT_DIR = os.path.join(ER_UPLOAD_DIR, "documents")
os.makedirs(ER_UPLOAD_DIR, exist_ok=True)
os.makedirs(ER_DOCUMENT_DIR, exist_ok=True)


def _superuser_required():
    if not current_user.is_authenticated:
        return redirect(url_for("login"))
    if getattr(current_user, "admin_level", 0) != 2:
        flash("You do not have permission to access Employee Relations.", "danger")
        return redirect(url_for("select_module"))
    return None


def _set_active_module():
    session["active_module"] = "Employee Relations"


def _log_case_event(case_id, event_type, notes=None):
    event = EmployeeRelationsTimelineEvent(
        case_id=case_id,
        event_type=event_type,
        notes=notes,
        updated_by=getattr(current_user, "username", None),
    )
    db.session.add(event)


def _parse_date(date_str):
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        return None


def _parse_datetime(datetime_str):
    if not datetime_str:
        return None
    try:
        return datetime.strptime(datetime_str, "%Y-%m-%dT%H:%M")
    except ValueError:
        return None


def _build_er_document_title(er_case, document_type):
    employee_name = f"{er_case.employee.first_name} {er_case.employee.last_name}"
    return f"{document_type} - {employee_name}"


def _next_er_document_version(case_id, document_type):
    latest = (
        EmployeeRelationsDocument.query.filter_by(
            case_id=case_id,
            document_type=document_type,
        )
        .order_by(EmployeeRelationsDocument.version.desc())
        .first()
    )
    return 1 if not latest else latest.version + 1


def _clean_policy_text(raw_text):
    if not raw_text:
        return None

    cleaned = raw_text.replace("\r\n", "\n").replace("\r", "\n")
    lines = [line.strip() for line in cleaned.split("\n")]
    cleaned = "\n".join(line for line in lines if line)
    return cleaned.strip() or None


def _get_active_policy_text(er_case):
    active_policy = (
        EmployeeRelationsPolicyText.query.filter_by(
            case_id=er_case.id,
            is_active=True,
        )
        .order_by(EmployeeRelationsPolicyText.updated_at.desc())
        .first()
    )

    if not active_policy:
        return None, None

    policy_text = active_policy.cleaned_text or active_policy.raw_text or None
    return active_policy, policy_text


@employee_relations_bp.before_request
@login_required
def employee_relations_before_request():
    access_check = _superuser_required()
    if access_check:
        return access_check
    _set_active_module()


@employee_relations_bp.route("/dashboard")
def dashboard():
    open_case_statuses = ["Draft", "Open", "Under Investigation", "Hearing Scheduled", "Appeal Pending"]

    open_cases_count = (
        EmployeeRelationsCase.query.filter(
            EmployeeRelationsCase.status.in_(open_case_statuses)
        ).count()
    )

    cases_by_type = {}
    for case_type in CASE_TYPES:
        cases_by_type[case_type] = EmployeeRelationsCase.query.filter_by(
            case_type=case_type
        ).count()

    cases_by_status = {}
    for status in CASE_STATUSES:
        cases_by_status[status] = EmployeeRelationsCase.query.filter_by(
            status=status
        ).count()

    recent_activity = (
        EmployeeRelationsTimelineEvent.query.order_by(
            EmployeeRelationsTimelineEvent.timestamp.desc()
        )
        .limit(10)
        .all()
    )

    upcoming_actions = (
        EmployeeRelationsCase.query.filter(
            EmployeeRelationsCase.next_action_date.isnot(None),
            EmployeeRelationsCase.status != "Closed",
            EmployeeRelationsCase.status != "Archived",
        )
        .order_by(EmployeeRelationsCase.next_action_date.asc())
        .limit(10)
        .all()
    )

    today = datetime.utcnow().date()
    overdue_cases = (
        EmployeeRelationsCase.query.filter(
            EmployeeRelationsCase.next_action_date.isnot(None),
            EmployeeRelationsCase.next_action_date < today,
            EmployeeRelationsCase.status != "Closed",
            EmployeeRelationsCase.status != "Archived",
        )
        .order_by(EmployeeRelationsCase.next_action_date.asc())
        .all()
    )

    return render_template(
        "employee_relations/dashboard.html",
        open_cases_count=open_cases_count,
        cases_by_type=cases_by_type,
        cases_by_status=cases_by_status,
        recent_activity=recent_activity,
        upcoming_actions=upcoming_actions,
        overdue_cases=overdue_cases,
    )


@employee_relations_bp.route("/cases")
def case_list():
    status_filter = request.args.get("status", "").strip()
    case_type_filter = request.args.get("case_type", "").strip()
    search = request.args.get("search", "").strip()

    query = EmployeeRelationsCase.query.join(Employee).order_by(
        EmployeeRelationsCase.created_at.desc()
    )

    if status_filter:
        query = query.filter(EmployeeRelationsCase.status == status_filter)

    if case_type_filter:
        query = query.filter(EmployeeRelationsCase.case_type == case_type_filter)

    if search:
        search_like = f"%{search}%"
        query = query.filter(
            db.or_(
                EmployeeRelationsCase.title.ilike(search_like),
                EmployeeRelationsCase.allegation_or_grievance.ilike(search_like),
                Employee.first_name.ilike(search_like),
                Employee.last_name.ilike(search_like),
            )
        )

    cases = query.all()

    return render_template(
        "employee_relations/list.html",
        cases=cases,
        status_filter=status_filter,
        case_type_filter=case_type_filter,
        search=search,
        case_statuses=CASE_STATUSES,
        case_types=CASE_TYPES,
    )


@employee_relations_bp.route("/cases/create", methods=["GET", "POST"])
def create_case():
    employees = Employee.query.order_by(Employee.first_name.asc(), Employee.last_name.asc()).all()

    if request.method == "POST":
        employee_id = request.form.get("employee_id", type=int)
        case_type = request.form.get("case_type", "").strip()
        title = request.form.get("title", "").strip()
        allegation_or_grievance = request.form.get("allegation_or_grievance", "").strip()
        date_raised = _parse_date(request.form.get("date_raised", "").strip())
        raised_by = request.form.get("raised_by", "").strip()
        status = request.form.get("status", "Draft").strip()
        stage = request.form.get("stage", "Allegation Logged").strip()

        summary = request.form.get("summary", "").strip() or None
        priority_level = request.form.get("priority_level", "").strip() or None
        service_area = request.form.get("service_area", "").strip() or None
        department = request.form.get("department", "").strip() or None
        hr_lead = request.form.get("hr_lead", "").strip() or None
        investigating_manager = request.form.get("investigating_manager", "").strip() or None
        policy_type = request.form.get("policy_type", "").strip() or None
        next_action_date = _parse_date(request.form.get("next_action_date", "").strip())
        disciplinary_category = request.form.get("disciplinary_category", "").strip() or None
        grievance_category = request.form.get("grievance_category", "").strip() or None
        confidential_notes = request.form.get("confidential_notes", "").strip() or None

        errors = []

        employee = Employee.query.get(employee_id) if employee_id else None
        if not employee:
            errors.append("Please select an employee.")

        if case_type not in CASE_TYPES:
            errors.append("Please select a valid case type.")

        if not title:
            errors.append("Title is required.")

        if not allegation_or_grievance:
            errors.append("Allegation / grievance details are required.")

        if not date_raised:
            errors.append("Date raised is required.")

        if status not in CASE_STATUSES:
            errors.append("Please select a valid status.")

        if stage not in CASE_STAGES:
            errors.append("Please select a valid stage.")

        if priority_level and priority_level not in PRIORITY_LEVELS:
            errors.append("Please select a valid priority level.")

        if errors:
            for error in errors:
                flash(error, "danger")

            return render_template(
                "employee_relations/create.html",
                employees=employees,
                case_types=CASE_TYPES,
                case_statuses=CASE_STATUSES,
                case_stages=CASE_STAGES,
                priority_levels=PRIORITY_LEVELS,
                disciplinary_categories=DISCIPLINARY_CATEGORIES,
                grievance_categories=GRIEVANCE_CATEGORIES,
                form_data=request.form,
            )

        er_case = EmployeeRelationsCase(
            employee_id=employee_id,
            case_type=case_type,
            title=title,
            summary=summary,
            allegation_or_grievance=allegation_or_grievance,
            date_raised=date_raised,
            raised_by=raised_by or None,
            status=status,
            stage=stage,
            priority_level=priority_level,
            service_area=service_area,
            department=department,
            policy_type=policy_type,
            next_action_date=next_action_date,
            confidential_notes=confidential_notes,
            hr_lead=hr_lead,
            investigating_manager=investigating_manager,
            disciplinary_category=disciplinary_category,
            grievance_category=grievance_category,
            created_by=getattr(current_user, "username", None),
            updated_by=getattr(current_user, "username", None),
        )

        db.session.add(er_case)
        db.session.flush()

        _log_case_event(
            er_case.id,
            "Case Created",
            f"{case_type} case created.",
        )

        db.session.commit()
        flash("Employee Relations case created successfully.", "success")
        return redirect(url_for("employee_relations.view_case", case_id=er_case.id))

    return render_template(
        "employee_relations/create.html",
        employees=employees,
        case_types=CASE_TYPES,
        case_statuses=CASE_STATUSES,
        case_stages=CASE_STAGES,
        priority_levels=PRIORITY_LEVELS,
        disciplinary_categories=DISCIPLINARY_CATEGORIES,
        grievance_categories=GRIEVANCE_CATEGORIES,
        form_data={},
    )


@employee_relations_bp.route("/cases/<int:case_id>")
def view_case(case_id):
    er_case = EmployeeRelationsCase.query.get_or_404(case_id)

    return render_template(
        "employee_relations/detail.html",
        er_case=er_case,
        disciplinary_sanctions=DISCIPLINARY_SANCTIONS,
        grievance_outcomes=GRIEVANCE_OUTCOMES,
        meeting_types=MEETING_TYPES,
        attachment_categories=ATTACHMENT_CATEGORIES,
        er_document_types=ER_DOCUMENT_TYPES,
    )


@employee_relations_bp.route("/cases/<int:case_id>/edit", methods=["GET", "POST"])
def edit_case(case_id):
    er_case = EmployeeRelationsCase.query.get_or_404(case_id)
    employees = Employee.query.order_by(Employee.first_name.asc(), Employee.last_name.asc()).all()

    if request.method == "POST":
        old_status = er_case.status
        old_stage = er_case.stage

        employee_id = request.form.get("employee_id", type=int)
        case_type = request.form.get("case_type", "").strip()
        title = request.form.get("title", "").strip()
        allegation_or_grievance = request.form.get("allegation_or_grievance", "").strip()
        date_raised = _parse_date(request.form.get("date_raised", "").strip())
        raised_by = request.form.get("raised_by", "").strip()
        status = request.form.get("status", "Draft").strip()
        stage = request.form.get("stage", "Allegation Logged").strip()

        errors = []

        employee = Employee.query.get(employee_id) if employee_id else None
        if not employee:
            errors.append("Please select an employee.")

        if case_type not in CASE_TYPES:
            errors.append("Please select a valid case type.")

        if not title:
            errors.append("Title is required.")

        if not allegation_or_grievance:
            errors.append("Allegation / grievance details are required.")

        if not date_raised:
            errors.append("Date raised is required.")

        if status not in CASE_STATUSES:
            errors.append("Please select a valid status.")

        if stage not in CASE_STAGES:
            errors.append("Please select a valid stage.")

        if errors:
            for error in errors:
                flash(error, "danger")

            return render_template(
                "employee_relations/edit.html",
                er_case=er_case,
                employees=employees,
                case_types=CASE_TYPES,
                case_statuses=CASE_STATUSES,
                case_stages=CASE_STAGES,
                priority_levels=PRIORITY_LEVELS,
                disciplinary_categories=DISCIPLINARY_CATEGORIES,
                grievance_categories=GRIEVANCE_CATEGORIES,
                disciplinary_sanctions=DISCIPLINARY_SANCTIONS,
                grievance_outcomes=GRIEVANCE_OUTCOMES,
            )

        er_case.employee_id = employee_id
        er_case.case_type = case_type
        er_case.title = title
        er_case.summary = request.form.get("summary", "").strip() or None
        er_case.allegation_or_grievance = allegation_or_grievance
        er_case.date_raised = date_raised
        er_case.raised_by = raised_by or None
        er_case.status = status
        er_case.stage = stage
        er_case.priority_level = request.form.get("priority_level", "").strip() or None
        er_case.service_area = request.form.get("service_area", "").strip() or None
        er_case.department = request.form.get("department", "").strip() or None
        er_case.policy_type = request.form.get("policy_type", "").strip() or None
        er_case.next_action_date = _parse_date(request.form.get("next_action_date", "").strip())
        er_case.investigation_deadline = _parse_date(request.form.get("investigation_deadline", "").strip())
        er_case.hearing_date = _parse_date(request.form.get("hearing_date", "").strip())
        er_case.outcome_due_date = _parse_date(request.form.get("outcome_due_date", "").strip())
        er_case.appeal_deadline = _parse_date(request.form.get("appeal_deadline", "").strip())
        er_case.date_closed = _parse_date(request.form.get("date_closed", "").strip())

        er_case.outcome_status = request.form.get("outcome_status", "").strip() or None
        er_case.confidential_notes = request.form.get("confidential_notes", "").strip() or None

        er_case.hr_lead = request.form.get("hr_lead", "").strip() or None
        er_case.investigating_manager = request.form.get("investigating_manager", "").strip() or None
        er_case.hearing_chair = request.form.get("hearing_chair", "").strip() or None
        er_case.note_taker = request.form.get("note_taker", "").strip() or None
        er_case.appeal_manager = request.form.get("appeal_manager", "").strip() or None

        er_case.disciplinary_category = request.form.get("disciplinary_category", "").strip() or None
        er_case.gross_misconduct_flag = request.form.get("gross_misconduct_flag") == "on"
        er_case.misconduct_date = _parse_date(request.form.get("misconduct_date", "").strip())
        er_case.suspension_flag = request.form.get("suspension_flag") == "on"
        er_case.suspension_with_pay = request.form.get("suspension_with_pay") == "on"
        er_case.previous_warnings_summary = request.form.get("previous_warnings_summary", "").strip() or None
        er_case.recommended_sanction = request.form.get("recommended_sanction", "").strip() or None
        er_case.final_sanction = request.form.get("final_sanction", "").strip() or None
        er_case.warning_level = request.form.get("warning_level", "").strip() or None
        er_case.warning_review_date = _parse_date(request.form.get("warning_review_date", "").strip())
        er_case.warning_expiry_date = _parse_date(request.form.get("warning_expiry_date", "").strip())

        er_case.grievance_category = request.form.get("grievance_category", "").strip() or None
        er_case.person_complained_about = request.form.get("person_complained_about", "").strip() or None
        er_case.bullying_flag = request.form.get("bullying_flag") == "on"
        er_case.harassment_flag = request.form.get("harassment_flag") == "on"
        er_case.discrimination_flag = request.form.get("discrimination_flag") == "on"
        er_case.requested_resolution = request.form.get("requested_resolution", "").strip() or None
        er_case.mediation_considered = request.form.get("mediation_considered") == "on"
        er_case.grievance_outcome = request.form.get("grievance_outcome", "").strip() or None

        er_case.investigation_scope = request.form.get("investigation_scope", "").strip() or None
        er_case.investigation_findings = request.form.get("investigation_findings", "").strip() or None
        er_case.recommended_next_step = request.form.get("recommended_next_step", "").strip() or None

        er_case.appeal_requested_flag = request.form.get("appeal_requested_flag") == "on"
        er_case.appeal_request_date = _parse_date(request.form.get("appeal_request_date", "").strip())
        er_case.appeal_reason = request.form.get("appeal_reason", "").strip() or None
        er_case.appeal_hearing_date = _parse_date(request.form.get("appeal_hearing_date", "").strip())
        er_case.appeal_outcome = request.form.get("appeal_outcome", "").strip() or None
        er_case.appeal_outcome_date = _parse_date(request.form.get("appeal_outcome_date", "").strip())

        er_case.updated_by = getattr(current_user, "username", None)

        _log_case_event(
            er_case.id,
            "Case Updated",
            f"Case updated by {getattr(current_user, 'username', 'system')}.",
        )

        if old_status != status:
            _log_case_event(
                er_case.id,
                "Status Changed",
                f"Status changed from {old_status} to {status}.",
            )

        if old_stage != stage:
            _log_case_event(
                er_case.id,
                "Stage Changed",
                f"Stage changed from {old_stage} to {stage}.",
            )

        db.session.commit()
        flash("Employee Relations case updated successfully.", "success")
        return redirect(url_for("employee_relations.view_case", case_id=er_case.id))

    return render_template(
        "employee_relations/edit.html",
        er_case=er_case,
        employees=employees,
        case_types=CASE_TYPES,
        case_statuses=CASE_STATUSES,
        case_stages=CASE_STAGES,
        priority_levels=PRIORITY_LEVELS,
        disciplinary_categories=DISCIPLINARY_CATEGORIES,
        grievance_categories=GRIEVANCE_CATEGORIES,
        disciplinary_sanctions=DISCIPLINARY_SANCTIONS,
        grievance_outcomes=GRIEVANCE_OUTCOMES,
    )


@employee_relations_bp.route("/cases/<int:case_id>/meetings/add", methods=["POST"])
def add_meeting(case_id):
    er_case = EmployeeRelationsCase.query.get_or_404(case_id)

    meeting_type = request.form.get("meeting_type", "").strip()
    meeting_datetime = _parse_datetime(request.form.get("meeting_datetime", "").strip())
    location = request.form.get("location", "").strip() or None
    attendees = request.form.get("attendees", "").strip() or None
    notes = request.form.get("notes", "").strip() or None
    adjournment_notes = request.form.get("adjournment_notes", "").strip() or None
    outcome_summary = request.form.get("outcome_summary", "").strip() or None

    errors = []
    if meeting_type not in MEETING_TYPES:
        errors.append("Please select a valid meeting type.")
    if not meeting_datetime:
        errors.append("Please provide a valid meeting date and time.")

    if errors:
        for error in errors:
            flash(error, "danger")
        return redirect(url_for("employee_relations.view_case", case_id=case_id))

    meeting = EmployeeRelationsMeeting(
        case_id=er_case.id,
        meeting_type=meeting_type,
        meeting_datetime=meeting_datetime,
        location=location,
        attendees=attendees,
        notes=notes,
        adjournment_notes=adjournment_notes,
        outcome_summary=outcome_summary,
        created_by=getattr(current_user, "username", None),
    )

    db.session.add(meeting)
    _log_case_event(
        er_case.id,
        "Meeting Added",
        f"{meeting_type} scheduled for {meeting_datetime.strftime('%d/%m/%Y %H:%M')}.",
    )
    db.session.commit()

    flash("Meeting added successfully.", "success")
    return redirect(url_for("employee_relations.view_case", case_id=case_id))


@employee_relations_bp.route("/cases/<int:case_id>/attachments/upload", methods=["POST"])
def upload_attachment(case_id):
    er_case = EmployeeRelationsCase.query.get_or_404(case_id)

    file = request.files.get("attachment_file")
    document_category = request.form.get("document_category", "").strip()
    notes = request.form.get("attachment_notes", "").strip() or None

    if not file or not file.filename:
        flash("Please choose a file to upload.", "danger")
        return redirect(url_for("employee_relations.view_case", case_id=case_id))

    if document_category not in ATTACHMENT_CATEGORIES:
        flash("Please select a valid attachment category.", "danger")
        return redirect(url_for("employee_relations.view_case", case_id=case_id))

    safe_name = secure_filename(file.filename)
    if not safe_name:
        flash("Invalid file name.", "danger")
        return redirect(url_for("employee_relations.view_case", case_id=case_id))

    case_dir = os.path.join(ER_UPLOAD_DIR, f"case_{case_id}")
    os.makedirs(case_dir, exist_ok=True)

    unique_name = f"{uuid4().hex}_{safe_name}"
    stored_path = os.path.join(case_dir, unique_name)
    file.save(stored_path)

    attachment = EmployeeRelationsAttachment(
        case_id=er_case.id,
        original_filename=file.filename,
        stored_filename=unique_name,
        stored_path=stored_path,
        document_category=document_category,
        notes=notes,
        uploaded_by=getattr(current_user, "username", None),
    )

    db.session.add(attachment)
    _log_case_event(
        er_case.id,
        "Attachment Uploaded",
        f"{file.filename} uploaded as {document_category}.",
    )
    db.session.commit()

    flash("Attachment uploaded successfully.", "success")
    return redirect(url_for("employee_relations.view_case", case_id=case_id))


@employee_relations_bp.route("/cases/<int:case_id>/policy-texts/add", methods=["POST"])
def add_policy_text(case_id):
    er_case = EmployeeRelationsCase.query.get_or_404(case_id)

    title = request.form.get("policy_title", "").strip()
    raw_text = request.form.get("policy_text", "")
    cleaned_text = _clean_policy_text(raw_text)

    source_attachment_id = request.form.get("source_attachment_id", type=int)
    source_attachment = None

    if source_attachment_id:
        source_attachment = EmployeeRelationsAttachment.query.filter_by(
            id=source_attachment_id,
            case_id=er_case.id,
        ).first()

    if not title:
        title = f"{er_case.policy_type or 'Policy'} - Case {er_case.id}"

    if not cleaned_text and not source_attachment:
        flash("Please paste policy text or select a linked attachment.", "danger")
        return redirect(url_for("employee_relations.view_case", case_id=case_id))

    if source_attachment_id and not source_attachment:
        flash("Selected attachment could not be found for this case.", "danger")
        return redirect(url_for("employee_relations.view_case", case_id=case_id))

    existing_active = EmployeeRelationsPolicyText.query.filter_by(
        case_id=er_case.id,
        is_active=True,
    ).all()

    for existing in existing_active:
        existing.is_active = False
        existing.updated_by = getattr(current_user, "username", None)

    policy_text = EmployeeRelationsPolicyText(
        case_id=er_case.id,
        title=title,
        source_filename=source_attachment.original_filename if source_attachment else None,
        source_attachment_id=source_attachment.id if source_attachment else None,
        raw_text=raw_text.strip() or None,
        cleaned_text=cleaned_text,
        is_active=True,
        created_by=getattr(current_user, "username", None),
        updated_by=getattr(current_user, "username", None),
    )

    db.session.add(policy_text)

    if source_attachment:
        _log_case_event(
            er_case.id,
            "Policy Linked",
            f"Policy text saved and linked to attachment: {source_attachment.original_filename}.",
        )
    else:
        _log_case_event(
            er_case.id,
            "Policy Text Added",
            f"Policy text saved as '{title}'.",
        )

    db.session.commit()
    flash("Policy text saved successfully.", "success")
    return redirect(url_for("employee_relations.view_case", case_id=case_id))


@employee_relations_bp.route("/cases/<int:case_id>/ai-advice/generate", methods=["POST"])
def generate_ai_advice(case_id):
    er_case = EmployeeRelationsCase.query.get_or_404(case_id)

    active_policy, active_policy_text = _get_active_policy_text(er_case)

    try:
        advice = generate_employee_relations_advice(
            er_case=er_case,
            active_policy_text=active_policy_text,
        )
    except Exception as exc:
        flash(f"AI advice could not be generated: {exc}", "danger")
        return redirect(url_for("employee_relations.view_case", case_id=case_id))

    notes_parts = [
        "Employee Relations AI Advice",
        "",
        advice,
    ]

    if active_policy:
        notes_parts.extend(
            [
                "",
                f"[Policy Source: {active_policy.title}]",
            ]
        )

    _log_case_event(
        er_case.id,
        "AI Advice Generated",
        "\n".join(notes_parts),
    )

    db.session.commit()
    flash("AI advice generated and saved to the timeline.", "success")
    return redirect(url_for("employee_relations.view_case", case_id=case_id))


@employee_relations_bp.route("/attachments/<int:attachment_id>/download")
def download_attachment(attachment_id):
    attachment = EmployeeRelationsAttachment.query.get_or_404(attachment_id)

    if not os.path.exists(attachment.stored_path):
        abort(404)

    return send_file(
        attachment.stored_path,
        as_attachment=True,
        download_name=attachment.original_filename,
    )


@employee_relations_bp.route("/cases/<int:case_id>/documents/create", methods=["POST"])
def create_document(case_id):
    er_case = EmployeeRelationsCase.query.get_or_404(case_id)

    document_type = request.form.get("document_type", "").strip()
    if document_type not in ER_DOCUMENT_TYPES:
        flash("Please select a valid document type.", "danger")
        return redirect(url_for("employee_relations.view_case", case_id=case_id))

    title = request.form.get("title", "").strip() or _build_er_document_title(er_case, document_type)

    employee_name = f"{er_case.employee.first_name} {er_case.employee.last_name}"
    default_html = f"""
        <h1>{document_type}</h1>
        <p><strong>Employee:</strong> {employee_name}</p>
        <p><strong>Case Type:</strong> {er_case.case_type}</p>
        <p><strong>Case Title:</strong> {er_case.title}</p>
        <p><strong>Status:</strong> {er_case.status}</p>
        <p><strong>Stage:</strong> {er_case.stage}</p>
        <hr>
        <p>Draft document created for Employee Relations case #{er_case.id}.</p>
    """.strip()

    doc = EmployeeRelationsDocument(
        case_id=er_case.id,
        document_type=document_type,
        title=title,
        status="Draft",
        version=_next_er_document_version(er_case.id, document_type),
        html_content=default_html,
        created_by=getattr(current_user, "username", None),
        updated_by=getattr(current_user, "username", None),
    )

    db.session.add(doc)
    db.session.flush()

    _log_case_event(
        er_case.id,
        "Document Draft Created",
        f"{document_type} draft created (v{doc.version}).",
    )

    db.session.commit()
    flash("Document draft created successfully.", "success")
    return redirect(url_for("employee_relations.edit_document", document_id=doc.id))


@employee_relations_bp.route("/documents/<int:document_id>/edit", methods=["GET", "POST"])
def edit_document(document_id):
    document = EmployeeRelationsDocument.query.get_or_404(document_id)
    er_case = document.case

    if request.method == "POST":
        document.title = request.form.get("title", "").strip() or document.title
        document.html_content = sanitize_html(request.form.get("html_content", "") or "")
        document.updated_by = getattr(current_user, "username", None)

        db.session.commit()
        flash("Document draft updated successfully.", "success")
        return redirect(url_for("employee_relations.view_case", case_id=er_case.id))

    return render_template(
        "employee_relations/edit_document.html",
        document=document,
        er_case=er_case,
    )


@employee_relations_bp.route("/documents/<int:document_id>/finalise", methods=["POST"])
def finalise_document(document_id):
    document = EmployeeRelationsDocument.query.get_or_404(document_id)
    er_case = document.case

    html_content = sanitize_html(document.html_content or "")
    if not html_content.strip():
        flash("Document cannot be finalised because it is empty.", "danger")
        return redirect(url_for("employee_relations.edit_document", document_id=document.id))

    case_doc_dir = os.path.join(ER_DOCUMENT_DIR, f"case_{er_case.id}")
    os.makedirs(case_doc_dir, exist_ok=True)

    safe_title = secure_filename(document.title) or f"er_document_{document.id}"
    file_name = f"{safe_title}_v{document.version}.docx"
    file_path = os.path.join(case_doc_dir, file_name)

    docx_bytes = html_to_docx_bytes(html_content)
    with open(file_path, "wb") as f:
        f.write(docx_bytes)

    document.file_path = file_path
    document.file_name = file_name
    document.status = "Final"
    document.finalised_at = datetime.utcnow()
    document.updated_by = getattr(current_user, "username", None)

    _log_case_event(
        er_case.id,
        "Document Finalised",
        f"{document.document_type} finalised as {file_name}.",
    )

    db.session.commit()
    flash("Document finalised successfully.", "success")
    return redirect(url_for("employee_relations.view_case", case_id=er_case.id))


@employee_relations_bp.route("/documents/<int:document_id>/download")
def download_document(document_id):
    document = EmployeeRelationsDocument.query.get_or_404(document_id)

    if not document.file_path or not os.path.exists(document.file_path):
        flash("Document file not found.", "danger")
        return redirect(url_for("employee_relations.view_case", case_id=document.case_id))

    return send_file(
        document.file_path,
        as_attachment=True,
        download_name=document.file_name or os.path.basename(document.file_path),
    )