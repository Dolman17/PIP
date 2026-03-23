from __future__ import annotations

from datetime import datetime, timedelta, timezone

from flask import Blueprint, flash, jsonify, redirect, render_template, request, session, url_for
from flask_login import current_user, login_required
from flask_wtf import FlaskForm
from wtforms import DateField, SelectField, SubmitField, TextAreaField
from wtforms.validators import DataRequired

from forms import SicknessMeetingForm
from models import db, Employee, SicknessCase, SicknessMeeting, TimelineEvent
from pip_app.services.sickness_metrics import compute_sickness_trigger_metrics
from pip_app.services.time_utils import today_local

sickness_bp = Blueprint("sickness", __name__)


class SicknessCaseForm(FlaskForm):
    start_date = DateField("First day of absence", validators=[DataRequired()], format="%Y-%m-%d")
    status = SelectField(
        "Status",
        choices=[("Open", "Open"), ("Closed", "Closed")],
        default="Open",
    )
    notes = TextAreaField("Reason / notes")
    submit = SubmitField("Save sickness record")


@sickness_bp.route("/sickness/dashboard")
@login_required
def sickness_dashboard():
    session["active_module"] = "Sickness"
    
    today = today_local()
    long_term_threshold = today - timedelta(days=28)
    one_year_ago = today - timedelta(days=365)
    upcoming_from = today
    upcoming_to = today + timedelta(days=14)

    severity_filter = (request.args.get("severity") or "").strip().lower()
    service_filter = (request.args.get("service") or "").strip()

    q_cases = SicknessCase.query.join(Employee)
    q_meetings = SicknessMeeting.query.join(SicknessCase).join(Employee)

    if current_user.admin_level == 0:
        q_cases = q_cases.filter(Employee.team_id == current_user.team_id)
        q_meetings = q_meetings.filter(Employee.team_id == current_user.team_id)

    if service_filter:
        q_cases = q_cases.filter(Employee.service == service_filter)
        q_meetings = q_meetings.filter(Employee.service == service_filter)

    open_cases = (
        q_cases.filter(SicknessCase.status == "Open")
        .order_by(SicknessCase.start_date.desc())
        .all()
    )
    open_count = len(open_cases)

    closed_last_12m = (
        q_cases.filter(
            SicknessCase.status == "Closed",
            SicknessCase.end_date.isnot(None),
            SicknessCase.end_date >= one_year_ago,
        ).count()
    )

    upcoming_meetings = (
        q_meetings.filter(
            SicknessMeeting.meeting_date.isnot(None),
            SicknessMeeting.meeting_date >= upcoming_from,
            SicknessMeeting.meeting_date <= upcoming_to,
        )
        .order_by(SicknessMeeting.meeting_date.asc())
        .all()
    )

    long_term_cases = (
        q_cases.filter(
            SicknessCase.status == "Open",
            SicknessCase.start_date.isnot(None),
            SicknessCase.start_date <= long_term_threshold,
        ).count()
    )

    potential_triggers = compute_sickness_trigger_metrics(
        q_cases,
        today=today,
        window_days=365,
        bradford_medium=200,
        bradford_high=400,
        episodes_threshold=3,
        total_days_threshold=14,
        long_term_days=28,
    )

    if severity_filter in {"high", "medium", "low"}:
        potential_triggers = [
            t for t in (potential_triggers or [])
            if (t.get("severity") or "").lower() == severity_filter
        ]

    for t in potential_triggers or []:
        sev = (t.get("severity") or "").lower()
        flags_label = (t.get("flags_label") or "").lower()

        actions = ["Check last RTW note and update case notes"]

        if "long-term" in flags_label:
            actions.append("Consider Occupational Health referral / welfare review")
            actions.append("Confirm fit note status and expected return date")

        if sev == "high":
            actions.insert(0, "Escalate: formal absence review meeting (HR involved)")
            actions.append("Agree formal plan: review dates, adjustments, expectations")
        elif sev == "medium":
            actions.insert(0, "Schedule absence review meeting within 7 days")
            actions.append("Discuss patterns, support, adjustments and next steps")
        elif sev == "low":
            actions.insert(0, "Monitor and prompt manager to complete RTW process")
            actions.append("Watch for repeat episodes over next 4–8 weeks")

        t["recommended_actions"] = actions

    return render_template(
        "sickness_dashboard.html",
        active_module="Sickness",
        open_cases=open_cases,
        open_count=open_count,
        closed_last_12m=closed_last_12m,
        upcoming_meetings=upcoming_meetings,
        long_term_cases=long_term_cases,
        potential_triggers=potential_triggers,
        severity_filter=severity_filter,
        service_filter=service_filter,
    )


@sickness_bp.route("/sickness/list")
@login_required
def sickness_list():
    session["active_module"] = "Sickness"

    status = request.args.get("status", "open")
    service = request.args.get("service") or None
    trigger = request.args.get("trigger") or None

    q = SicknessCase.query.join(Employee)

    if current_user.admin_level == 0:
        q = q.filter(Employee.team_id == current_user.team_id)

    if status == "open":
        q = q.filter(SicknessCase.status == "Open")
    elif status == "closed":
        q = q.filter(SicknessCase.status == "Closed")

    if service:
        q = q.filter(Employee.service == service)

    if trigger:
        q = q.filter(SicknessCase.trigger_type == trigger)

    cases = q.order_by(SicknessCase.start_date.desc()).all()

    services_query = (
        db.session.query(Employee.service)
        .join(SicknessCase, SicknessCase.employee_id == Employee.id)
        .filter(Employee.service.isnot(None))
    )
    if current_user.admin_level == 0:
        services_query = services_query.filter(Employee.team_id == current_user.team_id)

    services = sorted({row[0] for row in services_query})

    trigger_types = [
        ("short_term", "Short-term trigger"),
        ("long_term", "Long-term"),
        ("pattern", "Pattern concern"),
        ("other", "Other"),
    ]

    return render_template(
        "sickness_list.html",
        active_module="Sickness",
        cases=cases,
        status=status,
        service=service,
        trigger=trigger,
        services=services,
        trigger_types=trigger_types,
    )


@sickness_bp.route("/employee/<int:employee_id>/sickness/new", methods=["GET", "POST"])
@login_required
def sickness_create_for_employee(employee_id):
    session["active_module"] = "Sickness"

    from app import today_local  # safe during hybrid phase

    employee = Employee.query.get_or_404(employee_id)
    form = SicknessCaseForm()

    if request.method == "GET" and not form.start_date.data:
        form.start_date.data = datetime.now(timezone.utc).date()

    if form.validate_on_submit():
        case = SicknessCase(
            employee_id=employee.id,
            start_date=form.start_date.data,
            status=form.status.data,
        )
        db.session.add(case)
        db.session.commit()
        flash("Sickness case created.", "success")
        return redirect(url_for("sickness.sickness_dashboard"))

    today = today_local()
    one_year_ago = today - timedelta(days=365)

    sickness_q = SicknessCase.query.filter_by(employee_id=employee.id)

    cases_last_12m = sickness_q.filter(SicknessCase.start_date >= one_year_ago).all()
    sickness_episodes_12m = len(cases_last_12m)

    sickness_days_lost_12m = 0
    for c in cases_last_12m:
        if c.start_date:
            end = c.end_date or today
            sickness_days_lost_12m += (end - c.start_date).days + 1

    open_sickness_case = (
        sickness_q.filter(SicknessCase.status == "Open")
        .order_by(SicknessCase.start_date.desc())
        .first()
    )

    recent_sickness_cases = (
        sickness_q.order_by(SicknessCase.start_date.desc())
        .limit(3)
        .all()
    )

    return render_template(
        "sickness_case_form.html",
        form=form,
        employee=employee,
        active_module="Sickness",
        sickness_episodes_12m=sickness_episodes_12m,
        sickness_days_lost_12m=sickness_days_lost_12m,
        open_sickness_case=open_sickness_case,
        recent_sickness_cases=recent_sickness_cases,
    )


@sickness_bp.route("/sickness/create/<int:employee_id>", methods=["GET", "POST"])
@login_required
def create_sickness_case(employee_id):
    session["active_module"] = "Sickness"

    employee = Employee.query.get_or_404(employee_id)
    form = SicknessCaseForm()

    if form.validate_on_submit():
        case = SicknessCase(
            employee_id=employee.id,
            start_date=form.start_date.data,
            end_date=getattr(form, "end_date", None).data if hasattr(form, "end_date") else None,
            reason=form.reason.data.strip() if hasattr(form, "reason") and form.reason.data else None,
            trigger_type=form.trigger_type.data if hasattr(form, "trigger_type") else None,
            notes=form.notes.data,
            status="Open",
            created_by=current_user.username,
        )
        db.session.add(case)
        db.session.flush()

        event = TimelineEvent(
            pip_record_id=None,
            event_type="Sickness Case Created",
            notes=f"Sickness case {case.id} created for {employee.first_name} {employee.last_name} by {current_user.username}",
            updated_by=current_user.username,
        )
        db.session.add(event)
        db.session.commit()

        flash("Sickness case created.", "success")
        return redirect(url_for("sickness.view_sickness_case", case_id=case.id))

    if request.method == "GET" and not form.start_date.data:
        form.start_date.data = datetime.utcnow().date()

    return render_template(
        "create_sickness_case.html",
        form=form,
        employee=employee,
    )


@sickness_bp.route("/sickness/<int:case_id>")
@login_required
def view_sickness_case(case_id):
    session["active_module"] = "Sickness"

    from app import today_local  # safe during hybrid phase

    case = SicknessCase.query.get_or_404(case_id)
    employee = case.employee
    meetings = (
        SicknessMeeting.query.filter_by(sickness_case_id=case.id)
        .order_by(SicknessMeeting.meeting_date.asc())
        .all()
    )

    today = today_local()

    return render_template(
        "view_sickness_case.html",
        case=case,
        employee=employee,
        meetings=meetings,
        today=today,
    )


@sickness_bp.route("/sickness/<int:case_id>/meeting/add", methods=["GET", "POST"])
@login_required
def add_sickness_meeting(case_id):
    session["active_module"] = "Sickness"

    case = SicknessCase.query.get_or_404(case_id)
    employee = case.employee
    form = SicknessMeetingForm()

    if form.validate_on_submit():
        meeting = SicknessMeeting(
            sickness_case_id=case.id,
            meeting_date=form.meeting_date.data,
            meeting_type=form.meeting_type.data,
            chair=form.chair.data.strip() if form.chair.data else None,
            notes=form.notes.data,
            outcome=form.outcome.data,
        )
        db.session.add(meeting)

        event = TimelineEvent(
            pip_record_id=None,
            event_type="Sickness Meeting Logged",
            notes=f"{form.meeting_type.data} for sickness case {case.id} ({employee.first_name} {employee.last_name}) logged by {current_user.username}",
            updated_by=current_user.username,
        )
        db.session.add(event)
        db.session.commit()

        flash("Sickness meeting saved.", "success")
        return redirect(url_for("sickness.view_sickness_case", case_id=case.id))

    if request.method == "GET" and not form.meeting_date.data:
        form.meeting_date.data = datetime.utcnow().date()

    return render_template(
        "add_sickness_meeting.html",
        form=form,
        case=case,
        employee=employee,
    )


@sickness_bp.route("/sickness/<int:case_id>/status/<new_status>", methods=["POST"])
@login_required
def update_sickness_status(case_id, new_status):
    session["active_module"] = "Sickness"

    case = SicknessCase.query.get_or_404(case_id)
    valid_statuses = ["Open", "Closed", "Under Review"]

    if new_status not in valid_statuses:
        flash("Invalid status update.", "danger")
        return redirect(url_for("sickness.view_sickness_case", case_id=case.id))

    case.status = new_status
    db.session.add(case)

    event = TimelineEvent(
        pip_record_id=None,
        event_type="Sickness Status Updated",
        notes=f"Sickness case {case.id} status changed to {new_status} by {current_user.username}",
        updated_by=current_user.username,
    )
    db.session.add(event)
    db.session.commit()

    flash(f"Status updated to {new_status}.", "success")
    return redirect(url_for("sickness.view_sickness_case", case_id=case.id))