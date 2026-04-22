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
from sqlalchemy import or_

from pip_app.extensions import db
from pip_app.models import (
    AdvisorEscalation,
    Employee,
    EmployeeRelationsCase,
    EmployeeRelationsTimelineEvent,
    EmployeeRelationsMeeting,
    EmployeeRelationsAttachment,
    EmployeeRelationsDocument,
    EmployeeRelationsPolicyText,
    EmployeeRelationsAIAdvice,
)
from pip_app.services.ai_utils import (
    generate_employee_relations_advice,
    render_employee_relations_advice_for_timeline,
)
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
from pip_app.services.module_settings import DEFAULT_MODULE_SETTINGS, get_module_settings_for_org

employee_relations_bp = Blueprint(
    "employee_relations",
    __name__,
    url_prefix="/employee-relations",
)

ER_UPLOAD_DIR = os.path.join(BASE_DIR, "uploads", "employee_relations")
ER_DOCUMENT_DIR = os.path.join(ER_UPLOAD_DIR, "documents")
os.makedirs(ER_UPLOAD_DIR, exist_ok=True)
os.makedirs(ER_DOCUMENT_DIR, exist_ok=True)

ER_DOCUMENT_DRAFT_MODES = ["plain", "ai"]
ER_DOCUMENT_DRAFT_ORIGINS = ["plain", "ai", "ai_fallback_plain"]


def _superuser_required():
    if not current_user.is_authenticated:
        return redirect(url_for("login"))
    if getattr(current_user, "admin_level", 0) != 2:
        flash("You do not have permission to access Employee Relations.", "danger")
        return redirect(url_for("select_module"))
    return None


def _set_active_module():
    session["active_module"] = "Employee Relations"


def _scoped_employee_query():
    q = Employee.query
    if getattr(current_user, "admin_level", 0) == 0:
        if getattr(current_user, "team_id", None):
            q = q.filter(Employee.team_id == current_user.team_id)
        else:
            q = q.filter(Employee.id == -1)
    return q


def _active_employee_query(include_employee_id=None):
    q = _scoped_employee_query()

    if include_employee_id:
        q = q.filter(
            or_(
                Employee.is_leaver.is_(False),
                Employee.id == include_employee_id,
            )
        )
    else:
        q = q.filter(Employee.is_leaver.is_(False))

    return q.order_by(Employee.first_name.asc(), Employee.last_name.asc())


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


def _latest_er_ai_advice(er_case):
    return (
        EmployeeRelationsAIAdvice.query.filter_by(case_id=er_case.id)
        .order_by(EmployeeRelationsAIAdvice.created_at.desc())
        .first()
    )


def _is_employee_relations_ai_enabled():
    _org, settings = get_module_settings_for_org(user=current_user)
    setting = settings.get("employee_relations")
    defaults = DEFAULT_MODULE_SETTINGS.get("employee_relations", {"ai_enabled": True})

    if setting is None:
        return bool(defaults.get("ai_enabled", True))

    return bool(getattr(setting, "ai_enabled", defaults.get("ai_enabled", True)))


def _is_employee_relations_escalation_enabled():
    _org, settings = get_module_settings_for_org(user=current_user)
    setting = settings.get("employee_relations")
    defaults = DEFAULT_MODULE_SETTINGS.get(
        "employee_relations",
        {"escalation_enabled": True},
    )

    if setting is None:
        return bool(defaults.get("escalation_enabled", True))

    return bool(
        getattr(setting, "escalation_enabled", defaults.get("escalation_enabled", True))
    )


def _get_er_escalations(case_id):
    return (
        AdvisorEscalation.query.filter_by(
            module_key="employee_relations",
            source_record_type="employee_relations",
            source_record_id=case_id,
        )
        .order_by(AdvisorEscalation.created_at.desc())
        .all()
    )


def _get_latest_er_escalation(case_id):
    return (
        AdvisorEscalation.query.filter_by(
            module_key="employee_relations",
            source_record_type="employee_relations",
            source_record_id=case_id,
        )
        .order_by(AdvisorEscalation.created_at.desc())
        .first()
    )


def _er_escalation_is_active(escalation):
    if escalation is None:
        return False
    return escalation.status in {"draft", "submitted", "acknowledged", "in_review"}


def _build_er_escalation_summary(er_case):
    employee_name = f"{er_case.employee.first_name} {er_case.employee.last_name}"
    lines = [
        f"Employee: {employee_name}",
        f"Job Title: {er_case.employee.job_title or '—'}",
        f"Case Type: {er_case.case_type or '—'}",
        f"Case Title: {er_case.title or '—'}",
        f"Case Status: {er_case.status or '—'}",
        f"Stage: {er_case.stage or '—'}",
        f"Priority: {er_case.priority_level or '—'}",
        f"Date Raised: {er_case.date_raised.strftime('%d %b %Y') if er_case.date_raised else '—'}",
        "",
        "Summary:",
        er_case.summary or "—",
        "",
        "Allegation / Grievance Details:",
        er_case.allegation_or_grievance or "—",
    ]

    if er_case.investigation_findings:
        lines.extend(["", "Investigation Findings:", er_case.investigation_findings])

    if er_case.recommended_next_step:
        lines.extend(["", "Recommended Next Step:", er_case.recommended_next_step])

    if er_case.confidential_notes:
        lines.extend(["", "Confidential Notes:", er_case.confidential_notes])

    latest_ai = _latest_er_ai_advice(er_case)
    if latest_ai:
        lines.extend(
            [
                "",
                "Latest AI Advice Snapshot:",
                latest_ai.immediate_next_steps or latest_ai.overall_risk_view or "—",
            ]
        )

    return "\n".join(lines).strip()


def _default_er_document_mode(er_case):
    return "ai" if _is_employee_relations_ai_enabled() and _latest_er_ai_advice(er_case) else "plain"


def _normalise_er_document_mode(mode_value):
    mode = (mode_value or "").strip().lower()
    return mode if mode in ER_DOCUMENT_DRAFT_MODES else "plain"


def _draft_mode_label(mode):
    return "AI-prefilled draft" if mode == "ai" else "Plain draft"


def _draft_origin_label(origin):
    if origin == "ai":
        return "AI-prefilled draft"
    if origin == "ai_fallback_plain":
        return "AI requested, plain draft used"
    return "Plain draft"


def _resolve_draft_origin(requested_mode, effective_mode):
    if requested_mode == "ai" and effective_mode == "plain":
        return "ai_fallback_plain"
    if effective_mode == "ai":
        return "ai"
    return "plain"


def _html_paragraphs_from_bullet_text(text_value):
    if not text_value:
        return "<p>—</p>"

    lines = [line.strip() for line in str(text_value).splitlines() if line.strip()]
    if not lines:
        return "<p>—</p>"

    html_parts = []
    for line in lines:
        html_parts.append(f"<p>{line}</p>")
    return "\n".join(html_parts)


def _build_er_document_header_html(er_case, document_type, latest_ai):
    employee_name = f"{er_case.employee.first_name} {er_case.employee.last_name}"
    policy_title = latest_ai.policy_text.title if latest_ai and latest_ai.policy_text else "No linked policy text"
    generated_at = (
        latest_ai.created_at.strftime("%d/%m/%Y %H:%M")
        if latest_ai and latest_ai.created_at
        else "—"
    )

    return f"""
        <h1>{document_type}</h1>
        <p><strong>Employee:</strong> {employee_name}</p>
        <p><strong>Case Type:</strong> {er_case.case_type}</p>
        <p><strong>Case Title:</strong> {er_case.title}</p>
        <p><strong>Status:</strong> {er_case.status}</p>
        <p><strong>Stage:</strong> {er_case.stage}</p>
        <p><strong>Date Raised:</strong> {er_case.date_raised.strftime('%d/%m/%Y') if er_case.date_raised else '—'}</p>
        <p><strong>Policy Type:</strong> {er_case.policy_type or '—'}</p>
        <p><strong>AI Advice Timestamp:</strong> {generated_at}</p>
        <p><strong>Policy Reference:</strong> {policy_title}</p>
        <hr>
    """.strip()


def _build_er_document_body_html(document_type, latest_ai):
    document_templates = {
        "Investigation Invite": f"""
            <h2>Suggested Wording for Investigation Invite</h2>
            {_html_paragraphs_from_bullet_text(latest_ai.suggested_wording)}

            <h2>Immediate Next Steps</h2>
            {_html_paragraphs_from_bullet_text(latest_ai.immediate_next_steps)}

            <h2>Investigation Questions</h2>
            {_html_paragraphs_from_bullet_text(latest_ai.investigation_questions)}

            <h2>Fairness &amp; Process Checks</h2>
            {_html_paragraphs_from_bullet_text(latest_ai.fairness_process_checks)}

            <h2>Missing Information</h2>
            {_html_paragraphs_from_bullet_text(latest_ai.missing_information)}
        """,

        "Suspension Confirmation": f"""
            <h2>Suggested Wording for Suspension Confirmation</h2>
            {_html_paragraphs_from_bullet_text(latest_ai.suggested_wording)}

            <h2>Overall Risk View</h2>
            {_html_paragraphs_from_bullet_text(latest_ai.overall_risk_view)}

            <h2>Immediate Next Steps</h2>
            {_html_paragraphs_from_bullet_text(latest_ai.immediate_next_steps)}

            <h2>Fairness &amp; Process Checks</h2>
            {_html_paragraphs_from_bullet_text(latest_ai.fairness_process_checks)}

            <h2>Missing Information</h2>
            {_html_paragraphs_from_bullet_text(latest_ai.missing_information)}
        """,

        "Disciplinary Hearing Invite": f"""
            <h2>Suggested Wording for Disciplinary Hearing Invite</h2>
            {_html_paragraphs_from_bullet_text(latest_ai.suggested_wording)}

            <h2>Immediate Next Steps</h2>
            {_html_paragraphs_from_bullet_text(latest_ai.immediate_next_steps)}

            <h2>Hearing Questions</h2>
            {_html_paragraphs_from_bullet_text(latest_ai.hearing_questions)}

            <h2>Outcome / Sanction Guidance</h2>
            {_html_paragraphs_from_bullet_text(latest_ai.outcome_sanction_guidance)}

            <h2>Fairness &amp; Process Checks</h2>
            {_html_paragraphs_from_bullet_text(latest_ai.fairness_process_checks)}
        """,

        "Disciplinary Outcome Letter": f"""
            <h2>Suggested Wording for Disciplinary Outcome</h2>
            {_html_paragraphs_from_bullet_text(latest_ai.suggested_wording)}

            <h2>Outcome / Sanction Guidance</h2>
            {_html_paragraphs_from_bullet_text(latest_ai.outcome_sanction_guidance)}

            <h2>Fairness &amp; Process Checks</h2>
            {_html_paragraphs_from_bullet_text(latest_ai.fairness_process_checks)}

            <h2>Immediate Next Steps</h2>
            {_html_paragraphs_from_bullet_text(latest_ai.immediate_next_steps)}

            <h2>Missing Information</h2>
            {_html_paragraphs_from_bullet_text(latest_ai.missing_information)}
        """,

        "Warning Letter": f"""
            <h2>Suggested Wording for Warning Letter</h2>
            {_html_paragraphs_from_bullet_text(latest_ai.suggested_wording)}

            <h2>Outcome / Sanction Guidance</h2>
            {_html_paragraphs_from_bullet_text(latest_ai.outcome_sanction_guidance)}

            <h2>Fairness &amp; Process Checks</h2>
            {_html_paragraphs_from_bullet_text(latest_ai.fairness_process_checks)}

            <h2>Immediate Next Steps</h2>
            {_html_paragraphs_from_bullet_text(latest_ai.immediate_next_steps)}
        """,

        "Dismissal Letter": f"""
            <h2>Suggested Wording for Dismissal Letter</h2>
            {_html_paragraphs_from_bullet_text(latest_ai.suggested_wording)}

            <h2>Outcome / Sanction Guidance</h2>
            {_html_paragraphs_from_bullet_text(latest_ai.outcome_sanction_guidance)}

            <h2>Fairness &amp; Process Checks</h2>
            {_html_paragraphs_from_bullet_text(latest_ai.fairness_process_checks)}

            <h2>Missing Information</h2>
            {_html_paragraphs_from_bullet_text(latest_ai.missing_information)}
        """,

        "Grievance Meeting Invite": f"""
            <h2>Suggested Wording for Grievance Meeting Invite</h2>
            {_html_paragraphs_from_bullet_text(latest_ai.suggested_wording)}

            <h2>Immediate Next Steps</h2>
            {_html_paragraphs_from_bullet_text(latest_ai.immediate_next_steps)}

            <h2>Investigation Questions</h2>
            {_html_paragraphs_from_bullet_text(latest_ai.investigation_questions)}

            <h2>Fairness &amp; Process Checks</h2>
            {_html_paragraphs_from_bullet_text(latest_ai.fairness_process_checks)}

            <h2>Missing Information</h2>
            {_html_paragraphs_from_bullet_text(latest_ai.missing_information)}
        """,

        "Grievance Outcome Letter": f"""
            <h2>Suggested Wording for Grievance Outcome</h2>
            {_html_paragraphs_from_bullet_text(latest_ai.suggested_wording)}

            <h2>Fairness &amp; Process Checks</h2>
            {_html_paragraphs_from_bullet_text(latest_ai.fairness_process_checks)}

            <h2>Immediate Next Steps</h2>
            {_html_paragraphs_from_bullet_text(latest_ai.immediate_next_steps)}

            <h2>Missing Information</h2>
            {_html_paragraphs_from_bullet_text(latest_ai.missing_information)}
        """,

        "Appeal Invite": f"""
            <h2>Suggested Wording for Appeal Invite</h2>
            {_html_paragraphs_from_bullet_text(latest_ai.suggested_wording)}

            <h2>Immediate Next Steps</h2>
            {_html_paragraphs_from_bullet_text(latest_ai.immediate_next_steps)}

            <h2>Hearing Questions</h2>
            {_html_paragraphs_from_bullet_text(latest_ai.hearing_questions)}

            <h2>Fairness &amp; Process Checks</h2>
            {_html_paragraphs_from_bullet_text(latest_ai.fairness_process_checks)}

            <h2>Missing Information</h2>
            {_html_paragraphs_from_bullet_text(latest_ai.missing_information)}
        """,

        "Appeal Outcome Letter": f"""
            <h2>Suggested Wording for Appeal Outcome</h2>
            {_html_paragraphs_from_bullet_text(latest_ai.suggested_wording)}

            <h2>Outcome / Sanction Guidance</h2>
            {_html_paragraphs_from_bullet_text(latest_ai.outcome_sanction_guidance)}

            <h2>Fairness &amp; Process Checks</h2>
            {_html_paragraphs_from_bullet_text(latest_ai.fairness_process_checks)}

            <h2>Immediate Next Steps</h2>
            {_html_paragraphs_from_bullet_text(latest_ai.immediate_next_steps)}
        """,

        "Witness Statement Template": f"""
            <h2>Witness Statement Template Guidance</h2>
            {_html_paragraphs_from_bullet_text(latest_ai.investigation_questions)}

            <h2>Fairness &amp; Process Checks</h2>
            {_html_paragraphs_from_bullet_text(latest_ai.fairness_process_checks)}

            <h2>Missing Information</h2>
            {_html_paragraphs_from_bullet_text(latest_ai.missing_information)}
        """,

        "Meeting Notes Template": f"""
            <h2>Meeting Notes Template Guidance</h2>
            {_html_paragraphs_from_bullet_text(latest_ai.immediate_next_steps)}

            <h2>Investigation Questions</h2>
            {_html_paragraphs_from_bullet_text(latest_ai.investigation_questions)}

            <h2>Hearing Questions</h2>
            {_html_paragraphs_from_bullet_text(latest_ai.hearing_questions)}

            <h2>Fairness &amp; Process Checks</h2>
            {_html_paragraphs_from_bullet_text(latest_ai.fairness_process_checks)}
        """,
    }

    return document_templates.get(
        document_type,
        f"""
            <h2>Suggested Wording for HR / Manager</h2>
            {_html_paragraphs_from_bullet_text(latest_ai.suggested_wording)}

            <h2>Immediate Next Steps</h2>
            {_html_paragraphs_from_bullet_text(latest_ai.immediate_next_steps)}

            <h2>Fairness &amp; Process Checks</h2>
            {_html_paragraphs_from_bullet_text(latest_ai.fairness_process_checks)}

            <h2>Outcome / Sanction Guidance</h2>
            {_html_paragraphs_from_bullet_text(latest_ai.outcome_sanction_guidance)}

            <h2>Missing Information</h2>
            {_html_paragraphs_from_bullet_text(latest_ai.missing_information)}
        """,
    ).strip()


def _build_er_document_plain_html(er_case, document_type, draft_origin="plain"):
    employee_name = f"{er_case.employee.first_name} {er_case.employee.last_name}"
    draft_label = _draft_origin_label(draft_origin)

    return f"""
        <h1>{document_type}</h1>
        <p><strong>Draft mode:</strong> {draft_label}</p>
        <p><strong>Employee:</strong> {employee_name}</p>
        <p><strong>Case Type:</strong> {er_case.case_type}</p>
        <p><strong>Case Title:</strong> {er_case.title}</p>
        <p><strong>Status:</strong> {er_case.status}</p>
        <p><strong>Stage:</strong> {er_case.stage}</p>
        <p><strong>Date Raised:</strong> {er_case.date_raised.strftime('%d/%m/%Y') if er_case.date_raised else '—'}</p>
        <hr>

        <p>Draft document created for Employee Relations case #{er_case.id}.</p>

        <h2>Purpose of Document</h2>
        <p>Add the purpose of this document here.</p>

        <h2>Background</h2>
        <p>Set out the relevant background, facts, and dates here.</p>

        <h2>Key Details</h2>
        <p>Add the case-specific details, concerns, allegations, or grievance points here.</p>

        <h2>Next Steps / Required Action</h2>
        <p>Insert the next steps, expectations, hearing details, or outcome wording here.</p>

        <h2>Review Notes</h2>
        <p>Check the wording, dates, policy references, and names before finalising.</p>
    """.strip()


def _build_er_document_ai_html(er_case, document_type, latest_ai):
    header_html = _build_er_document_header_html(er_case, document_type, latest_ai)
    body_html = _build_er_document_body_html(document_type, latest_ai)

    return f"""
        {header_html}
        {body_html}
        <hr>
        <p><strong>Draft mode:</strong> AI-prefilled draft</p>
        <p>This draft was prefilled using the latest structured Employee Relations AI advice for case #{er_case.id}. Review and edit before finalising.</p>
    """.strip()


def _build_er_document_default_html(er_case, document_type, draft_origin="plain"):
    latest_ai = _latest_er_ai_advice(er_case)

    if draft_origin == "ai" and latest_ai:
        return _build_er_document_ai_html(er_case, document_type, latest_ai)

    return _build_er_document_plain_html(
        er_case,
        document_type,
        draft_origin=draft_origin,
    )


def _friendly_ai_error_message(exc):
    message = str(exc).strip()

    if "OPENAI_API_KEY is not configured" in message:
        return (
            "AI advice is not available because the OpenAI API key has not been configured. "
            "Please add a valid API key in the environment settings."
        )

    if "Incorrect API key" in message or "invalid_api_key" in message:
        return (
            "AI advice could not be generated because the configured OpenAI API key appears to be invalid."
        )

    if "Rate limit" in message or "rate_limit" in message:
        return (
            "AI advice is temporarily unavailable because the OpenAI rate limit has been reached. "
            "Please try again shortly."
        )

    if "insufficient_quota" in message:
        return (
            "AI advice could not be generated because the OpenAI account has insufficient quota."
        )

    return (
        "AI advice could not be generated at the moment. "
        "Please try again later or check the AI configuration."
    )


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
    employees = _active_employee_query().all()

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

        employee = _scoped_employee_query().filter(Employee.id == employee_id).first() if employee_id else None
        if not employee:
            errors.append("Please select an employee.")
        elif employee.is_leaver:
            errors.append("You cannot create a new Employee Relations case for an employee who is marked as a leaver.")

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
    latest_ai = _latest_er_ai_advice(er_case)
    er_ai_enabled = _is_employee_relations_ai_enabled()

    escalation_enabled = _is_employee_relations_escalation_enabled()
    escalations = _get_er_escalations(er_case.id)
    latest_escalation = escalations[0] if escalations else None
    can_submit_escalation = escalation_enabled and not _er_escalation_is_active(latest_escalation)

    return render_template(
        "employee_relations/detail.html",
        er_case=er_case,
        disciplinary_sanctions=DISCIPLINARY_SANCTIONS,
        grievance_outcomes=GRIEVANCE_OUTCOMES,
        meeting_types=MEETING_TYPES,
        attachment_categories=ATTACHMENT_CATEGORIES,
        er_document_types=ER_DOCUMENT_TYPES,
        er_document_draft_modes=ER_DOCUMENT_DRAFT_MODES,
        default_er_document_mode=_default_er_document_mode(er_case),
        has_er_ai_advice=bool(latest_ai),
        er_ai_enabled=er_ai_enabled,
        escalation_enabled=escalation_enabled,
        escalations=escalations,
        latest_escalation=latest_escalation,
        can_submit_escalation=can_submit_escalation,
    )


@employee_relations_bp.route("/cases/<int:case_id>/escalate", methods=["POST"])
def submit_escalation(case_id):
    er_case = EmployeeRelationsCase.query.get_or_404(case_id)

    if not _is_employee_relations_escalation_enabled():
        flash("Advisor escalation is disabled for Employee Relations for your organisation.", "warning")
        return redirect(url_for("employee_relations.view_case", case_id=case_id))

    latest_escalation = _get_latest_er_escalation(er_case.id)
    if _er_escalation_is_active(latest_escalation):
        flash("This case already has an active advisor escalation.", "warning")
        return redirect(url_for("employee_relations.view_case", case_id=case_id))

    submitted_summary = (request.form.get("summary") or "").strip()
    summary = submitted_summary or _build_er_escalation_summary(er_case)

    escalation = AdvisorEscalation(
        organisation_id=er_case.employee.organisation_id or getattr(current_user, "organisation_id", None),
        module_key="employee_relations",
        source_record_type="employee_relations",
        source_record_id=er_case.id,
        submitted_by_user_id=current_user.id,
        assigned_to_user_id=None,
        status="submitted",
        summary=summary,
        submitted_at=datetime.utcnow(),
    )

    db.session.add(escalation)

    _log_case_event(
        er_case.id,
        "Advisor Escalation Submitted",
        "Employee Relations case submitted for advisor escalation.",
    )

    db.session.commit()
    flash("Case submitted for advisor escalation.", "success")
    return redirect(url_for("employee_relations.view_case", case_id=case_id))


@employee_relations_bp.route("/cases/<int:case_id>/edit", methods=["GET", "POST"])
def edit_case(case_id):
    er_case = EmployeeRelationsCase.query.get_or_404(case_id)
    employees = _active_employee_query(include_employee_id=er_case.employee_id).all()

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

        employee = _scoped_employee_query().filter(Employee.id == employee_id).first() if employee_id else None
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
        er_case.appeal_outcome_date = _parse_date(request.form.get("appeal_outcome_date", "").strip()) or None

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

    if not _is_employee_relations_ai_enabled():
        flash("AI is disabled for the Employee Relations module for your organisation.", "warning")
        return redirect(url_for("employee_relations.view_case", case_id=case_id))

    active_policy, active_policy_text = _get_active_policy_text(er_case)

    try:
        advice_data = generate_employee_relations_advice(
            er_case=er_case,
            active_policy_text=active_policy_text,
        )
    except Exception as exc:
        flash(_friendly_ai_error_message(exc), "danger")
        return redirect(url_for("employee_relations.view_case", case_id=case_id))

    advice_record = EmployeeRelationsAIAdvice(
        case_id=er_case.id,
        policy_text_id=active_policy.id if active_policy else None,
        overall_risk_view=advice_data.get("overall_risk_view"),
        immediate_next_steps=advice_data.get("immediate_next_steps"),
        investigation_questions=advice_data.get("investigation_questions"),
        hearing_questions=advice_data.get("hearing_questions"),
        outcome_sanction_guidance=advice_data.get("outcome_sanction_guidance"),
        fairness_process_checks=advice_data.get("fairness_process_checks"),
        suggested_wording=advice_data.get("suggested_wording"),
        missing_information=advice_data.get("missing_information"),
        raw_response=advice_data.get("raw_response"),
        model_name=advice_data.get("model_name"),
        created_by=getattr(current_user, "username", None),
    )
    db.session.add(advice_record)

    timeline_notes = render_employee_relations_advice_for_timeline(advice_data)
    if active_policy:
        timeline_notes = f"{timeline_notes}\n\n[Policy Source: {active_policy.title}]"

    _log_case_event(
        er_case.id,
        "AI Advice Generated",
        timeline_notes,
    )

    db.session.commit()
    flash("AI advice generated and saved.", "success")
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

    requested_mode = _normalise_er_document_mode(request.form.get("draft_mode"))
    latest_ai = _latest_er_ai_advice(er_case)
    ai_enabled = _is_employee_relations_ai_enabled()

    effective_mode = requested_mode
    if requested_mode == "ai" and not ai_enabled:
        effective_mode = "plain"
        flash(
            "AI-prefilled draft was requested, but AI is disabled for Employee Relations for this organisation. A plain draft was created instead.",
            "warning",
        )
    elif requested_mode == "ai" and not latest_ai:
        effective_mode = "plain"
        flash(
            "AI-prefilled draft was requested, but no AI advice exists for this case yet. A plain draft was created instead.",
            "warning",
        )

    draft_origin = _resolve_draft_origin(requested_mode, effective_mode)

    title = request.form.get("title", "").strip() or _build_er_document_title(er_case, document_type)
    default_html = _build_er_document_default_html(
        er_case,
        document_type,
        draft_origin=draft_origin,
    )

    doc = EmployeeRelationsDocument(
        case_id=er_case.id,
        document_type=document_type,
        title=title,
        status="Draft",
        version=_next_er_document_version(er_case.id, document_type),
        draft_origin=draft_origin,
        html_content=default_html,
        created_by=getattr(current_user, "username", None),
        updated_by=getattr(current_user, "username", None),
    )

    db.session.add(doc)
    db.session.flush()

    if draft_origin == "ai_fallback_plain":
        timeline_note = (
            f"{document_type} draft created (v{doc.version}) "
            f"with requested mode '{_draft_mode_label(requested_mode)}', "
            f"but no AI-prefilled draft could be used so '{_draft_origin_label(draft_origin)}' was used."
        )
    else:
        timeline_note = (
            f"{document_type} draft created (v{doc.version}) "
            f"using {_draft_origin_label(draft_origin)}."
        )

    _log_case_event(
        er_case.id,
        "Document Draft Created",
        timeline_note,
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