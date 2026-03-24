from __future__ import annotations

from flask import Blueprint, flash, jsonify, redirect, render_template, request, session, url_for
from flask_login import current_user, login_required
from sqlalchemy import or_

from forms import ProbationPlanForm, ProbationRecordForm, ProbationReviewForm
from models import db, DraftProbation, Employee, ProbationPlan, ProbationRecord, ProbationReview, TimelineEvent
from pip_app.services.time_utils import today_local

probation_bp = Blueprint("probation", __name__)


def get_active_probation_draft_for_user(user_id: int):
    return DraftProbation.query.filter_by(user_id=user_id, is_dismissed=False).first()


def _scoped_employee_query():
    q = Employee.query
    if current_user.admin_level == 0:
        if current_user.team_id:
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
                Employee.id == include_employee_id
            )
        )
    else:
        q = q.filter(Employee.is_leaver.is_(False))

    return q.order_by(Employee.last_name.asc(), Employee.first_name.asc())


@probation_bp.route("/probation/create-wizard", methods=["GET"])
@login_required
def probation_create_wizard():
    session["active_module"] = "Probation"
    draft = DraftProbation.query.filter_by(user_id=current_user.id, is_dismissed=False).first()
    step = draft.step if draft else 1
    data = draft.payload if draft else {}

    selected_employee_id = None
    try:
        if data and data.get("employee_id"):
            selected_employee_id = int(data.get("employee_id"))
    except (TypeError, ValueError):
        selected_employee_id = None

    employees = _active_employee_query(include_employee_id=selected_employee_id).all()

    return render_template(
        "probation_create_wizard.html",
        step=step,
        data=data,
        draft=draft,
        employees=employees,
    )


@probation_bp.route("/probation/save-draft", methods=["POST"])
@login_required
def probation_save_draft():
    session["active_module"] = "Probation"
    payload = request.json or {}
    step = payload.get("step", 1)

    draft = DraftProbation.query.filter_by(user_id=current_user.id, is_dismissed=False).first()
    if not draft:
        draft = DraftProbation(user_id=current_user.id, step=step, payload=payload)
        db.session.add(draft)
    else:
        draft.step = step
        draft.payload = payload

    db.session.commit()
    return jsonify({"success": True, "updated_at": draft.updated_at.strftime("%Y-%m-%d %H:%M:%S")})


@probation_bp.route("/probation/resume-draft")
@login_required
def probation_resume_draft():
    session["active_module"] = "Probation"
    draft = DraftProbation.query.filter_by(user_id=current_user.id, is_dismissed=False).first()
    if draft:
        return redirect(url_for("probation.probation_create_wizard"))
    flash("No probation draft available.", "info")
    return redirect(url_for("probation.probation_dashboard"))


@probation_bp.route("/probation/dismiss-draft", methods=["POST"])
@login_required
def dismiss_probation_draft():
    session["active_module"] = "Probation"
    draft = DraftProbation.query.filter_by(user_id=current_user.id, is_dismissed=False).first()
    if not draft:
        return jsonify({"success": False, "message": "No active draft"}), 400
    draft.is_dismissed = True
    db.session.commit()
    return jsonify({"success": True})


@probation_bp.route("/probation/<int:id>")
@login_required
def view_probation(id):
    session["active_module"] = "Probation"
    probation = ProbationRecord.query.get_or_404(id)
    employee = probation.employee
    return render_template("view_probation.html", probation=probation, employee=employee)


@probation_bp.route("/probation/<int:id>/review/add", methods=["GET", "POST"])
@login_required
def add_probation_review(id):
    session["active_module"] = "Probation"
    probation = ProbationRecord.query.get_or_404(id)
    form = ProbationReviewForm()

    if form.validate_on_submit():
        review = ProbationReview(
            probation_id=probation.id,
            review_date=form.review_date.data,
            reviewer=form.reviewer.data,
            summary=form.summary.data,
            concerns_flag=(form.concerns_flag.data.lower() == "yes"),
        )
        db.session.add(review)

        event = TimelineEvent(
            pip_record_id=None,
            event_type="Probation Review",
            notes=f"Review added by {current_user.username}",
            updated_by=current_user.username,
        )
        db.session.add(event)
        db.session.commit()

        flash("Probation review added.", "success")
        return redirect(url_for("probation.view_probation", id=probation.id))

    return render_template("add_probation_review.html", form=form, probation=probation)


@probation_bp.route("/probation/<int:id>/plan/add", methods=["GET", "POST"])
@login_required
def add_probation_plan(id):
    session["active_module"] = "Probation"
    probation = ProbationRecord.query.get_or_404(id)
    form = ProbationPlanForm()

    if form.validate_on_submit():
        plan = ProbationPlan(
            probation_id=probation.id,
            objectives=form.objectives.data,
            deadline=form.deadline.data,
            outcome=form.outcome.data,
        )
        db.session.add(plan)

        event = TimelineEvent(
            pip_record_id=None,
            event_type="Probation Plan Added",
            notes=f"Plan created by {current_user.username}",
            updated_by=current_user.username,
        )
        db.session.add(event)
        db.session.commit()

        flash("Development plan added.", "success")
        return redirect(url_for("probation.view_probation", id=probation.id))

    return render_template("add_probation_plan.html", form=form, probation=probation)


@probation_bp.route("/probation/<int:id>/edit", methods=["GET", "POST"])
@login_required
def edit_probation(id):
    session["active_module"] = "Probation"
    probation = ProbationRecord.query.get_or_404(id)
    form = ProbationRecordForm(obj=probation)

    if form.validate_on_submit():
        probation.start_date = form.start_date.data
        probation.expected_end_date = form.expected_end_date.data
        probation.notes = form.notes.data
        db.session.commit()
        flash("Probation record updated.", "success")
        return redirect(url_for("probation.view_probation", id=probation.id))

    return render_template("edit_probation.html", form=form, probation=probation)


@probation_bp.route("/probation/<int:id>/status/<new_status>", methods=["POST"])
@login_required
def update_probation_status(id, new_status):
    session["active_module"] = "Probation"
    probation = ProbationRecord.query.get_or_404(id)
    valid_statuses = ["Completed", "Extended", "Failed"]

    if new_status not in valid_statuses:
        flash("Invalid status update.", "danger")
        return redirect(url_for("probation.view_probation", id=id))

    probation.status = new_status
    db.session.add(probation)

    event = TimelineEvent(
        pip_record_id=None,
        event_type="Probation Status Updated",
        notes=f"Status changed to {new_status} by {current_user.username}",
        updated_by=current_user.username,
    )
    db.session.add(event)
    db.session.commit()

    flash(f"Status updated to {new_status}.", "success")
    return redirect(url_for("probation.view_probation", id=id))


@probation_bp.route("/probation/create/<int:employee_id>", methods=["GET", "POST"])
@login_required
def create_probation(employee_id):
    session["active_module"] = "Probation"
    employee = _scoped_employee_query().filter(Employee.id == employee_id).first_or_404()

    if employee.is_leaver:
        flash("You cannot start a new probation record for an employee who is marked as a leaver.", "warning")
        return redirect(url_for("manage_employee.detail", employee_id=employee.id))

    form = ProbationRecordForm()

    if form.validate_on_submit():
        probation = ProbationRecord(
            employee_id=employee.id,
            start_date=form.start_date.data,
            expected_end_date=form.expected_end_date.data,
            notes=form.notes.data,
        )
        db.session.add(probation)
        db.session.commit()

        flash("Probation record created successfully.", "success")
        return redirect(url_for("probation.view_probation", id=probation.id))

    return render_template("create_probation.html", form=form, employee=employee)


@probation_bp.route("/probation/dashboard")
@login_required
def probation_dashboard():
    session["active_module"] = "Probation"

    from datetime import timedelta

    global_active = ProbationRecord.query.filter_by(status="Active").count()
    global_completed = ProbationRecord.query.filter_by(status="Completed").count()
    global_extended = ProbationRecord.query.filter_by(status="Extended").count()

    today = today_local()
    soon = today + timedelta(days=14)

    q_records = ProbationRecord.query.join(Employee)
    q_reviews = ProbationReview.query.join(
        ProbationRecord, ProbationReview.probation_id == ProbationRecord.id
    ).join(Employee)

    if current_user.admin_level == 0:
        q_records = q_records.filter(Employee.team_id == current_user.team_id)
        q_reviews = q_reviews.filter(Employee.team_id == current_user.team_id)

    active_probations = (
        q_records.filter(ProbationRecord.status == "Active")
        .order_by(ProbationRecord.expected_end_date.asc().nullslast())
        .all()
    )

    upcoming_reviews = (
        q_reviews.filter(
            ProbationRecord.status == "Active",
            ProbationReview.review_date >= today,
            ProbationReview.review_date <= soon,
        )
        .order_by(ProbationReview.review_date.asc())
        .all()
    )

    overdue_reviews = (
        q_reviews.filter(
            ProbationRecord.status == "Active",
            ProbationReview.review_date < today,
        ).count()
    )

    due_soon_count = (
        q_records.filter(
            ProbationRecord.status == "Active",
            ProbationRecord.expected_end_date >= today,
            ProbationRecord.expected_end_date <= soon,
        ).count()
    )

    probation_draft = get_active_probation_draft_for_user(current_user.id)

    return render_template(
        "probation_dashboard.html",
        active_module="Probation",
        global_active=global_active,
        global_completed=global_completed,
        global_extended=global_extended,
        active_probations=active_probations,
        upcoming_reviews=upcoming_reviews,
        overdue_reviews=overdue_reviews,
        due_soon_count=due_soon_count,
        draft=probation_draft,
    )


@probation_bp.route("/probation/employees")
@login_required
def probation_employee_list():
    session["active_module"] = "Probation"
    employees = _active_employee_query().all()
    return render_template("probation_employee_list.html", employees=employees)