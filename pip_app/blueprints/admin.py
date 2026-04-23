from __future__ import annotations

import csv
import os
import tempfile
import zipfile
from datetime import datetime
from io import BytesIO

from flask import Blueprint, flash, redirect, render_template, request, send_file, url_for
from flask_login import current_user, login_required
from werkzeug.security import generate_password_hash

from forms import OrganisationForm, UserForm
from models import (
    db,
    AdvisorEscalation,
    Employee,
    EmployeeRelationsCase,
    EmployeeRelationsTimelineEvent,
    Organisation,
    OrganisationModuleSetting,
    PIPRecord,
    ProbationPlan,
    ProbationRecord,
    ProbationReview,
    TimelineEvent,
    User,
)
from pip_app.decorators import superuser_required
from pip_app.security import log_security_event
from pip_app.services.module_settings import (
    DEFAULT_MODULE_LABELS,
    DEFAULT_MODULE_SETTINGS,
    get_module_settings_for_org,
)
from pip_app.services.timeline_utils import log_timeline_event

admin_bp = Blueprint("admin", __name__)

ESCALATION_STATUS_LABELS = {
    "draft": "Draft",
    "submitted": "Submitted",
    "acknowledged": "Acknowledged",
    "in_review": "In Review",
    "closed": "Closed",
    "cancelled": "Cancelled",
}

ACTIVE_ESCALATION_STATUSES = {"draft", "submitted", "acknowledged", "in_review"}
QUEUE_ESCALATION_STATUSES = {"submitted", "acknowledged", "in_review"}
ALL_ESCALATION_STATUSES = set(ESCALATION_STATUS_LABELS.keys())
SLA_FILTER_OPTIONS = {
    "green": "On Track",
    "amber": "Watch",
    "red": "Overdue",
    "neutral": "Closed/Cancelled",
}
SORT_OPTIONS = {
    "oldest": "Oldest first",
    "newest": "Newest first",
}


def _organisation_choices():
    organisations = Organisation.query.order_by(Organisation.name.asc()).all()
    return [(0, "No organisation assigned")] + [
        (org.id, org.name) for org in organisations
    ]


def _get_selected_organisation_from_request():
    organisation_id_raw = (
        request.form.get("organisation_id")
        if request.method == "POST"
        else request.args.get("organisation_id")
    )

    if not organisation_id_raw:
        return None

    try:
        organisation_id = int(organisation_id_raw)
    except (TypeError, ValueError):
        return None

    if organisation_id <= 0:
        return None

    return db.session.get(Organisation, organisation_id)


def _admin_queue_access_required():
    if not current_user.is_authenticated:
        return redirect(url_for("login"))
    if not current_user.is_admin():
        flash("You do not have permission to access the advisor queue.", "danger")
        return redirect(url_for("main.home"))
    return None


def _scoped_escalation_query():
    query = AdvisorEscalation.query

    if getattr(current_user, "organisation_id", None):
        query = query.filter(AdvisorEscalation.organisation_id == current_user.organisation_id)

    return query


def _scoped_assignable_users():
    query = User.query.filter(User.admin_level >= 1)

    if getattr(current_user, "organisation_id", None):
        query = query.filter(User.organisation_id == current_user.organisation_id)

    return query.order_by(User.username.asc()).all()


def _get_escalation_or_404(escalation_id):
    escalation = _scoped_escalation_query().filter(
        AdvisorEscalation.id == escalation_id
    ).first_or_404()
    return escalation


def _build_escalation_source_context(escalation):
    context = {
        "source_title": f"{escalation.source_record_type.title()} #{escalation.source_record_id}",
        "source_url": None,
        "employee_name": None,
        "secondary": None,
    }

    if escalation.source_record_type == "pip":
        pip_record = PIPRecord.query.get(escalation.source_record_id)
        if pip_record:
            employee = pip_record.employee
            employee_name = employee.full_name if employee else None
            context.update(
                {
                    "source_title": f"PIP #{pip_record.id}",
                    "source_url": url_for("pip.pip_detail", id=pip_record.id),
                    "employee_name": employee_name,
                    "secondary": employee.job_title if employee else None,
                }
            )

    elif escalation.source_record_type == "employee_relations":
        er_case = EmployeeRelationsCase.query.get(escalation.source_record_id)
        if er_case:
            employee = er_case.employee
            employee_name = (
                f"{employee.first_name} {employee.last_name}".strip()
                if employee else None
            )
            context.update(
                {
                    "source_title": f"ER Case #{er_case.id}: {er_case.title}",
                    "source_url": url_for("employee_relations.view_case", case_id=er_case.id),
                    "employee_name": employee_name,
                    "secondary": er_case.case_type,
                }
            )

    return context


def _calculate_escalation_age_data(escalation):
    now = datetime.utcnow()
    anchor = escalation.submitted_at or escalation.created_at or now
    delta = now - anchor
    age_days = max(delta.days, 0)
    age_hours = max(int(delta.total_seconds() // 3600), 0)

    if escalation.status in {"closed", "cancelled"}:
        sla_status = "neutral"
        sla_label = "Closed"
    elif age_days <= 2:
        sla_status = "green"
        sla_label = "On Track"
    elif age_days <= 5:
        sla_status = "amber"
        sla_label = "Watch"
    else:
        sla_status = "red"
        sla_label = "Overdue"

    return {
        "age_days": age_days,
        "age_hours": age_hours,
        "sla_status": sla_status,
        "sla_label": sla_label,
    }


def _log_escalation_assignment_change(escalation, old_user, new_user):
    old_name = old_user.username if old_user else "Unassigned"
    new_name = new_user.username if new_user else "Unassigned"
    note = f"Advisor escalation assignment changed from {old_name} to {new_name} by {current_user.username}."

    if escalation.source_record_type == "pip":
        log_timeline_event(
            pip_id=escalation.source_record_id,
            event_type="Advisor Escalation Reassigned",
            notes=note,
        )

        try:
            log_security_event(
                event_type="PIP Advisor Escalation Reassigned",
                notes=(
                    f"PIP #{escalation.source_record_id} escalation #{escalation.id} "
                    f"reassigned from {old_name} to {new_name}"
                ),
                pip_record_id=escalation.source_record_id,
                updated_by=current_user.username,
            )
        except Exception:
            pass

    elif escalation.source_record_type == "employee_relations":
        db.session.add(
            EmployeeRelationsTimelineEvent(
                case_id=escalation.source_record_id,
                event_type="Advisor Escalation Reassigned",
                notes=note,
                updated_by=current_user.username,
            )
        )


def _apply_escalation_status_change(escalation, new_status, advisor_notes=None):
    old_status = escalation.status
    now = datetime.utcnow()

    escalation.status = new_status

    if advisor_notes is not None:
        cleaned_notes = advisor_notes.strip()
        escalation.advisor_notes = cleaned_notes or None

    if new_status in {"acknowledged", "in_review"} and escalation.assigned_to_user_id is None:
        escalation.assigned_to_user_id = current_user.id

    if new_status == "acknowledged" and escalation.acknowledged_at is None:
        escalation.acknowledged_at = now

    if new_status == "submitted":
        escalation.closed_at = None
        escalation.cancelled_at = None

    if new_status == "in_review":
        escalation.closed_at = None
        escalation.cancelled_at = None

    if new_status == "closed":
        escalation.closed_at = now
        escalation.cancelled_at = None

    if new_status == "cancelled":
        escalation.cancelled_at = now

    if escalation.source_record_type == "pip":
        status_label = ESCALATION_STATUS_LABELS.get(new_status, new_status.replace("_", " ").title())
        note = f"Advisor escalation status changed from {old_status} to {new_status} by {current_user.username}."
        if escalation.advisor_notes:
            note += f" Notes: {escalation.advisor_notes}"

        log_timeline_event(
            pip_id=escalation.source_record_id,
            event_type=f"Advisor Escalation {status_label}",
            notes=note,
        )

        try:
            log_security_event(
                event_type="PIP Advisor Escalation Updated",
                notes=(
                    f"PIP #{escalation.source_record_id} escalation #{escalation.id} "
                    f"changed from {old_status} to {new_status}"
                ),
                pip_record_id=escalation.source_record_id,
                updated_by=current_user.username,
            )
        except Exception:
            pass

    elif escalation.source_record_type == "employee_relations":
        status_label = ESCALATION_STATUS_LABELS.get(new_status, new_status.replace("_", " ").title())
        note = f"Advisor escalation status changed from {old_status} to {new_status} by {current_user.username}."
        if escalation.advisor_notes:
            note += f" Notes: {escalation.advisor_notes}"

        db.session.add(
            EmployeeRelationsTimelineEvent(
                case_id=escalation.source_record_id,
                event_type=f"Advisor Escalation {status_label}",
                notes=note,
                updated_by=current_user.username,
            )
        )


@admin_bp.route("/admin/dashboard")
@login_required
def admin_dashboard():
    if not current_user.is_superuser():
        flash("You do not have permission to access the admin dashboard.", "danger")
        return redirect(url_for("main.home"))

    escalation_query = _scoped_escalation_query()
    open_escalations_count = escalation_query.filter(
        AdvisorEscalation.status.in_(list(QUEUE_ESCALATION_STATUSES))
    ).count()
    unassigned_escalations_count = escalation_query.filter(
        AdvisorEscalation.status.in_(list(QUEUE_ESCALATION_STATUSES)),
        AdvisorEscalation.assigned_to_user_id.is_(None),
    ).count()
    closed_escalations_count = escalation_query.filter(
        AdvisorEscalation.status == "closed"
    ).count()

    return render_template(
        "admin_dashboard.html",
        open_escalations_count=open_escalations_count,
        unassigned_escalations_count=unassigned_escalations_count,
        closed_escalations_count=closed_escalations_count,
    )


@admin_bp.route("/admin/organisations", methods=["GET", "POST"])
@login_required
@superuser_required
def manage_organisations():
    form = OrganisationForm()
    organisations = Organisation.query.order_by(Organisation.name.asc()).all()

    if form.validate_on_submit():
        name = (form.name.data or "").strip()

        existing = Organisation.query.filter(
            db.func.lower(Organisation.name) == name.lower()
        ).first()
        if existing:
            flash("An organisation with that name already exists.", "danger")
            return redirect(url_for("admin.manage_organisations"))

        org = Organisation(name=name)
        db.session.add(org)
        db.session.commit()

        flash("Organisation created successfully.", "success")
        return redirect(url_for("admin.manage_organisations"))

    organisation_user_counts = {
        org.id: User.query.filter_by(organisation_id=org.id).count()
        for org in organisations
    }

    return render_template(
        "admin_organisations.html",
        form=form,
        organisations=organisations,
        organisation_user_counts=organisation_user_counts,
    )


@admin_bp.route("/admin/organisations/<int:organisation_id>/edit", methods=["GET", "POST"])
@login_required
@superuser_required
def edit_organisation(organisation_id):
    organisation = Organisation.query.get_or_404(organisation_id)
    form = OrganisationForm(obj=organisation)

    if form.validate_on_submit():
        new_name = (form.name.data or "").strip()

        existing = Organisation.query.filter(
            db.func.lower(Organisation.name) == new_name.lower(),
            Organisation.id != organisation.id,
        ).first()
        if existing:
            flash("Another organisation already uses that name.", "danger")
            return redirect(url_for("admin.edit_organisation", organisation_id=organisation.id))

        organisation.name = new_name
        db.session.commit()

        flash("Organisation updated successfully.", "success")
        return redirect(url_for("admin.manage_organisations"))

    return render_template(
        "admin_edit_organisation.html",
        form=form,
        organisation=organisation,
    )


@admin_bp.route("/admin/modules", methods=["GET", "POST"])
@login_required
@superuser_required
def admin_module_settings():
    organisations = Organisation.query.order_by(Organisation.name.asc()).all()
    selected_org = _get_selected_organisation_from_request()

    if request.method == "POST" and request.form.get("organisation_id") and selected_org is None:
        flash("Selected organisation could not be found.", "danger")
        return redirect(url_for("admin.admin_module_settings"))

    if request.method == "GET" and request.args.get("organisation_id") and selected_org is None:
        flash("Selected organisation could not be found.", "danger")
        return redirect(url_for("admin.admin_module_settings"))

    if selected_org is not None:
        org, existing_settings = get_module_settings_for_org(organisation=selected_org)
    else:
        org, existing_settings = get_module_settings_for_org(user=current_user)

    if request.method == "POST":
        for module_key, _label in DEFAULT_MODULE_LABELS:
            module_defaults = DEFAULT_MODULE_SETTINGS.get(
                module_key,
                {
                    "is_enabled": True,
                    "ai_enabled": True,
                    "escalation_enabled": True,
                },
            )

            should_enable = request.form.get(f"{module_key}__enabled") == "on"
            should_enable_ai = request.form.get(f"{module_key}__ai_enabled") == "on"
            should_enable_escalation = request.form.get(f"{module_key}__escalation_enabled") == "on"

            setting = existing_settings.get(module_key)

            if setting is None:
                setting = OrganisationModuleSetting(
                    organisation_id=org.id,
                    module_key=module_key,
                    is_enabled=should_enable if request.form.get(f"{module_key}__enabled") is not None else module_defaults["is_enabled"],
                    ai_enabled=should_enable_ai if request.form.get(f"{module_key}__ai_enabled") is not None else module_defaults["ai_enabled"],
                    escalation_enabled=should_enable_escalation if request.form.get(f"{module_key}__escalation_enabled") is not None else module_defaults["escalation_enabled"],
                )
                db.session.add(setting)
            else:
                setting.is_enabled = should_enable
                setting.ai_enabled = should_enable_ai
                setting.escalation_enabled = should_enable_escalation

        db.session.commit()
        flash("Module settings updated successfully.", "success")
        return redirect(url_for("admin.admin_module_settings", organisation_id=org.id))

    settings = {}
    for module_key, _label in DEFAULT_MODULE_LABELS:
        module_defaults = DEFAULT_MODULE_SETTINGS.get(
            module_key,
            {
                "is_enabled": True,
                "ai_enabled": True,
                "escalation_enabled": True,
            },
        )
        setting = existing_settings.get(module_key)

        settings[module_key] = {
            "is_enabled": bool(setting.is_enabled) if setting else bool(module_defaults["is_enabled"]),
            "ai_enabled": bool(getattr(setting, "ai_enabled", module_defaults["ai_enabled"])) if setting else bool(module_defaults["ai_enabled"]),
            "escalation_enabled": bool(getattr(setting, "escalation_enabled", module_defaults["escalation_enabled"])) if setting else bool(module_defaults["escalation_enabled"]),
        }

    enabled_count = sum(1 for module_key, _label in DEFAULT_MODULE_LABELS if settings[module_key]["is_enabled"])
    ai_enabled_count = sum(1 for module_key, _label in DEFAULT_MODULE_LABELS if settings[module_key]["ai_enabled"])
    escalation_enabled_count = sum(1 for module_key, _label in DEFAULT_MODULE_LABELS if settings[module_key]["escalation_enabled"])

    return render_template(
        "admin_module_settings.html",
        settings=settings,
        module_labels=DEFAULT_MODULE_LABELS,
        organisation=org,
        organisations=organisations,
        selected_organisation_id=org.id if org else None,
        enabled_count=enabled_count,
        ai_enabled_count=ai_enabled_count,
        escalation_enabled_count=escalation_enabled_count,
    )


@admin_bp.route("/admin/escalations")
@login_required
def advisor_escalation_queue():
    access_check = _admin_queue_access_required()
    if access_check:
        return access_check

    status_filter = (request.args.get("status") or "").strip().lower()
    module_filter = (request.args.get("module_key") or "").strip().lower()
    assigned_filter = (request.args.get("assigned") or "").strip().lower()
    sla_filter = (request.args.get("sla") or "").strip().lower()
    sort_by = (request.args.get("sort") or "oldest").strip().lower()

    if sort_by not in SORT_OPTIONS:
        sort_by = "oldest"

    query = _scoped_escalation_query()

    if sort_by == "newest":
        query = query.order_by(AdvisorEscalation.created_at.desc())
    else:
        query = query.order_by(AdvisorEscalation.created_at.asc())

    if status_filter:
        query = query.filter(AdvisorEscalation.status == status_filter)

    if module_filter:
        query = query.filter(AdvisorEscalation.module_key == module_filter)

    if assigned_filter == "me":
        query = query.filter(AdvisorEscalation.assigned_to_user_id == current_user.id)
    elif assigned_filter == "unassigned":
        query = query.filter(AdvisorEscalation.assigned_to_user_id.is_(None))

    escalations = query.all()
    assignable_users = _scoped_assignable_users()

    escalation_rows = []
    for escalation in escalations:
        source = _build_escalation_source_context(escalation)
        age_data = _calculate_escalation_age_data(escalation)

        if sla_filter and age_data["sla_status"] != sla_filter:
            continue

        escalation_rows.append(
            {
                "escalation": escalation,
                "source": source,
                "is_active": escalation.status in ACTIVE_ESCALATION_STATUSES,
                "age_data": age_data,
            }
        )

    open_count = _scoped_escalation_query().filter(
        AdvisorEscalation.status.in_(list(QUEUE_ESCALATION_STATUSES))
    ).count()
    unassigned_count = _scoped_escalation_query().filter(
        AdvisorEscalation.status.in_(list(QUEUE_ESCALATION_STATUSES)),
        AdvisorEscalation.assigned_to_user_id.is_(None),
    ).count()
    my_queue_count = _scoped_escalation_query().filter(
        AdvisorEscalation.status.in_(list(QUEUE_ESCALATION_STATUSES)),
        AdvisorEscalation.assigned_to_user_id == current_user.id,
    ).count()

    return render_template(
        "admin_escalations.html",
        escalation_rows=escalation_rows,
        status_filter=status_filter,
        module_filter=module_filter,
        assigned_filter=assigned_filter,
        sla_filter=sla_filter,
        sort_by=sort_by,
        escalation_status_labels=ESCALATION_STATUS_LABELS,
        sla_filter_options=SLA_FILTER_OPTIONS,
        sort_options=SORT_OPTIONS,
        open_count=open_count,
        unassigned_count=unassigned_count,
        my_queue_count=my_queue_count,
        assignable_users=assignable_users,
    )


@admin_bp.route("/admin/escalations/<int:escalation_id>")
@login_required
def advisor_escalation_detail(escalation_id):
    access_check = _admin_queue_access_required()
    if access_check:
        return access_check

    escalation = _get_escalation_or_404(escalation_id)
    source = _build_escalation_source_context(escalation)
    assignable_users = _scoped_assignable_users()
    age_data = _calculate_escalation_age_data(escalation)

    return render_template(
        "admin_escalation_detail.html",
        escalation=escalation,
        source=source,
        escalation_status_labels=ESCALATION_STATUS_LABELS,
        assignable_users=assignable_users,
        age_data=age_data,
    )


@admin_bp.route("/admin/escalations/<int:escalation_id>/assign", methods=["POST"])
@login_required
def assign_advisor_escalation(escalation_id):
    access_check = _admin_queue_access_required()
    if access_check:
        return access_check

    escalation = _get_escalation_or_404(escalation_id)

    assigned_to_raw = (request.form.get("assigned_to_user_id") or "").strip()
    if not assigned_to_raw:
        new_user = None
        new_user_id = None
    else:
        try:
            new_user_id = int(assigned_to_raw)
        except (TypeError, ValueError):
            flash("Invalid assignee selected.", "danger")
            return redirect(url_for("admin.advisor_escalation_detail", escalation_id=escalation.id))

        assignable_user_ids = {user.id for user in _scoped_assignable_users()}
        if new_user_id not in assignable_user_ids:
            flash("Selected user cannot be assigned to this escalation.", "danger")
            return redirect(url_for("admin.advisor_escalation_detail", escalation_id=escalation.id))

        new_user = User.query.get(new_user_id)
        if new_user is None:
            flash("Selected user could not be found.", "danger")
            return redirect(url_for("admin.advisor_escalation_detail", escalation_id=escalation.id))

    old_user = escalation.assigned_to
    old_user_id = escalation.assigned_to_user_id

    if old_user_id == new_user_id:
        flash("Escalation assignment is unchanged.", "info")
        return redirect(url_for("admin.advisor_escalation_detail", escalation_id=escalation.id))

    escalation.assigned_to_user_id = new_user_id
    _log_escalation_assignment_change(escalation, old_user, new_user)

    db.session.commit()
    flash("Escalation assignment updated successfully.", "success")
    return redirect(url_for("admin.advisor_escalation_detail", escalation_id=escalation.id))


@admin_bp.route("/admin/escalations/<int:escalation_id>/update", methods=["POST"])
@login_required
def update_advisor_escalation(escalation_id):
    access_check = _admin_queue_access_required()
    if access_check:
        return access_check

    escalation = _get_escalation_or_404(escalation_id)
    new_status = (request.form.get("status") or "").strip().lower()
    advisor_notes = request.form.get("advisor_notes") or ""

    if new_status not in ALL_ESCALATION_STATUSES:
        flash("Invalid escalation status selected.", "danger")
        return redirect(url_for("admin.advisor_escalation_detail", escalation_id=escalation.id))

    current_status = escalation.status

    allowed_transitions = {
        "draft": {"submitted", "acknowledged", "in_review", "closed", "cancelled"},
        "submitted": {"acknowledged", "in_review", "closed", "cancelled"},
        "acknowledged": {"in_review", "closed", "cancelled"},
        "in_review": {"closed", "cancelled"},
        "closed": set(),
        "cancelled": set(),
    }

    if new_status != current_status and new_status not in allowed_transitions.get(current_status, set()):
        flash("That escalation status change is not allowed from the current state.", "danger")
        return redirect(url_for("admin.advisor_escalation_detail", escalation_id=escalation.id))

    _apply_escalation_status_change(
        escalation,
        new_status=new_status,
        advisor_notes=advisor_notes,
    )

    db.session.commit()
    flash("Escalation updated successfully.", "success")
    return redirect(url_for("admin.advisor_escalation_detail", escalation_id=escalation.id))


@admin_bp.route("/admin/export")
@login_required
@superuser_required
def export_data():
    zip_buffer = BytesIO()

    with tempfile.TemporaryDirectory() as tmpdir:
        def write_csv(filename, fieldnames, rows, export_zip_obj):
            filepath = os.path.join(tmpdir, filename)
            with open(filepath, "w", newline="", encoding="utf-8") as file_obj:
                writer = csv.DictWriter(file_obj, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(rows)
            export_zip_obj.write(filepath, arcname=filename)

        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as export_zip:
            employees = Employee.query.all()
            write_csv(
                "employees.csv",
                [
                    "id",
                    "first_name",
                    "last_name",
                    "job_title",
                    "line_manager",
                    "service",
                    "start_date",
                    "team_id",
                    "email",
                ],
                [
                    {
                        "id": employee.id,
                        "first_name": getattr(employee, "first_name", ""),
                        "last_name": getattr(employee, "last_name", ""),
                        "job_title": employee.job_title,
                        "line_manager": employee.line_manager,
                        "service": employee.service,
                        "start_date": employee.start_date.strftime("%Y-%m-%d") if employee.start_date else "",
                        "team_id": employee.team_id,
                        "email": employee.email,
                    }
                    for employee in employees
                ],
                export_zip,
            )

            pips = PIPRecord.query.all()
            write_csv(
                "pip_records.csv",
                [
                    "id",
                    "employee_id",
                    "concerns",
                    "concern_category",
                    "severity",
                    "frequency",
                    "tags",
                    "start_date",
                    "review_date",
                    "status",
                    "created_by",
                ],
                [
                    {
                        "id": pip_record.id,
                        "employee_id": pip_record.employee_id,
                        "concerns": pip_record.concerns,
                        "concern_category": getattr(pip_record, "concern_category", ""),
                        "severity": getattr(pip_record, "severity", ""),
                        "frequency": getattr(pip_record, "frequency", ""),
                        "tags": getattr(pip_record, "tags", ""),
                        "start_date": pip_record.start_date.strftime("%Y-%m-%d") if pip_record.start_date else "",
                        "review_date": pip_record.review_date.strftime("%Y-%m-%d") if pip_record.review_date else "",
                        "status": pip_record.status,
                        "created_by": getattr(pip_record, "created_by", ""),
                    }
                    for pip_record in pips
                ],
                export_zip,
            )

            events = TimelineEvent.query.all()
            write_csv(
                "timeline_events.csv",
                ["id", "pip_record_id", "employee_id", "event_type", "notes", "updated_by", "timestamp"],
                [
                    {
                        "id": event.id,
                        "pip_record_id": event.pip_record_id if event.pip_record_id else "",
                        "employee_id": event.pip_record.employee_id if event.pip_record else "",
                        "event_type": getattr(event, "event_type", ""),
                        "notes": getattr(event, "notes", ""),
                        "updated_by": getattr(event, "updated_by", ""),
                        "timestamp": event.timestamp.strftime("%Y-%m-%d %H:%M:%S") if event.timestamp else "",
                    }
                    for event in events
                ],
                export_zip,
            )

            users = User.query.all()
            write_csv(
                "users.csv",
                ["id", "username", "email", "admin_level", "team_id", "organisation_id"],
                [
                    {
                        "id": user.id,
                        "username": user.username,
                        "email": user.email,
                        "admin_level": user.admin_level,
                        "team_id": user.team_id,
                        "organisation_id": user.organisation_id,
                    }
                    for user in users
                ],
                export_zip,
            )

            probations = ProbationRecord.query.all()
            write_csv(
                "probation_records.csv",
                ["id", "employee_id", "status", "start_date", "expected_end_date", "notes"],
                [
                    {
                        "id": probation.id,
                        "employee_id": probation.employee_id,
                        "status": probation.status,
                        "start_date": probation.start_date.strftime("%Y-%m-%d") if probation.start_date else "",
                        "expected_end_date": probation.expected_end_date.strftime("%Y-%m-%d") if probation.expected_end_date else "",
                        "notes": probation.notes,
                    }
                    for probation in probations
                ],
                export_zip,
            )

            reviews = ProbationReview.query.all()
            write_csv(
                "probation_reviews.csv",
                ["id", "probation_id", "review_date", "reviewer", "summary", "concerns_flag"],
                [
                    {
                        "id": review.id,
                        "probation_id": review.probation_id,
                        "review_date": review.review_date.strftime("%Y-%m-%d") if review.review_date else "",
                        "reviewer": review.reviewer,
                        "summary": review.summary,
                        "concerns_flag": review.concerns_flag,
                    }
                    for review in reviews
                ],
                export_zip,
            )

            plans = ProbationPlan.query.all()
            write_csv(
                "probation_plans.csv",
                ["id", "probation_id", "objectives", "outcome", "deadline"],
                [
                    {
                        "id": plan.id,
                        "probation_id": plan.probation_id,
                        "objectives": getattr(plan, "objectives", ""),
                        "outcome": getattr(plan, "outcome", ""),
                        "deadline": plan.deadline.strftime("%Y-%m-%d") if getattr(plan, "deadline", None) else "",
                    }
                    for plan in plans
                ],
                export_zip,
            )

    zip_buffer.seek(0)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
    return send_file(
        zip_buffer,
        mimetype="application/zip",
        as_attachment=True,
        download_name=f"export_{timestamp}.zip",
    )


@admin_bp.route("/admin/users")
@login_required
def manage_users():
    if not current_user.is_superuser():
        flash("Access denied.", "danger")
        return redirect(url_for("dashboard"))
    users = User.query.all()
    return render_template("admin_users.html", users=users)


@admin_bp.route("/admin/users/edit/<int:user_id>", methods=["GET", "POST"])
@login_required
def edit_user(user_id):
    if not current_user.is_superuser():
        flash("Access denied.", "danger")
        return redirect(url_for("dashboard"))

    user = User.query.get_or_404(user_id)
    form = UserForm(obj=user)
    form.organisation_id.choices = _organisation_choices()

    if request.method == "GET":
        form.organisation_id.data = user.organisation_id or 0

    if form.validate_on_submit():
        user.username = form.username.data
        user.email = form.email.data
        user.admin_level = form.admin_level.data
        user.team_id = form.team_id.data
        user.organisation_id = form.organisation_id.data or None
        db.session.commit()
        flash("User updated successfully.", "success")
        return redirect(url_for("admin.manage_users"))

    return render_template("edit_user.html", form=form, user=user)


@admin_bp.route("/admin/users/create", methods=["GET", "POST"])
@login_required
def create_user():
    if not current_user.is_superuser():
        flash("Access denied: Superuser only.", "danger")
        return redirect(url_for("dashboard"))

    organisations = Organisation.query.order_by(Organisation.name.asc()).all()

    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        email = (request.form.get("email") or "").strip()
        password = request.form.get("password")
        admin_level = int(request.form.get("admin_level", 0))
        team_id_raw = (request.form.get("team_id") or "").strip()
        organisation_id_raw = (request.form.get("organisation_id") or "").strip()

        team_id = int(team_id_raw) if team_id_raw else None
        organisation_id = int(organisation_id_raw) if organisation_id_raw else None

        if not username or not email or not password:
            flash("All fields except team ID and organisation are required.", "danger")
            return redirect(request.url)

        if organisation_id is not None:
            organisation = db.session.get(Organisation, organisation_id)
            if organisation is None:
                flash("Selected organisation could not be found.", "danger")
                return redirect(request.url)

        if User.query.filter_by(username=username).first():
            flash("Username already exists.", "danger")
            return redirect(request.url)

        if User.query.filter_by(email=email).first():
            flash("Email already in use.", "danger")
            return redirect(request.url)

        hashed_pw = generate_password_hash(password)
        new_user = User(
            username=username,
            email=email,
            password_hash=hashed_pw,
            admin_level=admin_level,
            team_id=team_id,
            organisation_id=organisation_id,
        )
        db.session.add(new_user)
        db.session.commit()

        flash("User created successfully.", "success")
        return redirect(url_for("admin.manage_users"))

    return render_template("admin_create_user.html", organisations=organisations)


@admin_bp.route("/admin/users/delete/<int:user_id>", methods=["POST"])
@login_required
def delete_user(user_id):
    if not current_user.is_superuser():
        flash("Access denied: Superuser only.", "danger")
        return redirect(url_for("dashboard"))

    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash("You cannot delete your own account while logged in.", "warning")
        return redirect(url_for("admin.manage_users"))

    db.session.delete(user)
    db.session.commit()
    flash("User deleted successfully.", "success")
    return redirect(url_for("admin.manage_users"))


@admin_bp.route("/admin/backup")
@login_required
def backup_database():
    if not current_user.is_superuser():
        flash("Access denied: Superuser only.", "danger")
        return redirect(url_for("main.home"))

    db_path = os.path.join(os.getcwd(), "pip_crm.db")
    if os.path.exists(db_path):
        return send_file(db_path, as_attachment=True)

    flash("Database file not found.", "danger")
    return redirect(url_for("admin.admin_dashboard"))