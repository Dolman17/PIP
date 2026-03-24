from __future__ import annotations

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import or_
from sqlalchemy.orm import joinedload

from models import Employee, db
from pip_app.services.employee_lifecycle_service import (
    get_employee_status_label,
    mark_employee_as_leaver,
    reactivate_employee,
)
from pip_app.services.import_utils import parse_iso_date

manage_employee_bp = Blueprint("manage_employee", __name__)


LEAVING_REASON_CHOICES = [
    "Resignation",
    "Dismissal",
    "Redundancy",
    "Retirement",
    "End of Fixed Term",
    "TUPE Transfer Out",
    "Death in Service",
    "Other",
]


def _scoped_employee_query():
    q = Employee.query
    if current_user.admin_level == 0:
        if current_user.team_id:
            q = q.filter(Employee.team_id == current_user.team_id)
        else:
            q = q.filter(False)
    return q


def _get_scoped_employee_or_404(employee_id: int):
    return _scoped_employee_query().filter(Employee.id == employee_id).first_or_404()


@manage_employee_bp.route("/manage-employees")
@login_required
def index():
    status = (request.args.get("status") or "active").strip().lower()
    search = (request.args.get("q") or "").strip()

    q = _scoped_employee_query()

    if status == "leavers":
        q = q.filter(Employee.is_leaver.is_(True))
    elif status == "all":
        pass
    else:
        status = "active"
        q = q.filter(Employee.is_leaver.is_(False))

    if search:
        like = f"%{search}%"
        q = q.filter(
            or_(
                Employee.first_name.ilike(like),
                Employee.last_name.ilike(like),
                Employee.job_title.ilike(like),
                Employee.service.ilike(like),
                Employee.line_manager.ilike(like),
                Employee.email.ilike(like),
            )
        )

    employees = q.order_by(Employee.last_name.asc(), Employee.first_name.asc()).all()

    counts_base = _scoped_employee_query()
    counts = {
        "active": counts_base.filter(Employee.is_leaver.is_(False)).count(),
        "leavers": counts_base.filter(Employee.is_leaver.is_(True)).count(),
        "all": counts_base.count(),
    }

    return render_template(
        "manage_employee/index.html",
        employees=employees,
        status=status,
        search=search,
        counts=counts,
    )


@manage_employee_bp.route("/manage-employees/<int:employee_id>")
@login_required
def detail(employee_id):
    employee = (
        _scoped_employee_query()
        .options(
            joinedload(Employee.pips),
            joinedload(Employee.probation_records),
            joinedload(Employee.sickness_cases),
            joinedload(Employee.employee_relations_cases),
        )
        .filter(Employee.id == employee_id)
        .first_or_404()
    )

    return render_template(
        "manage_employee/detail.html",
        employee=employee,
        status_label=get_employee_status_label(employee),
    )


@manage_employee_bp.route("/manage-employees/<int:employee_id>/mark-leaver", methods=["GET", "POST"])
@login_required
def mark_leaver(employee_id):
    employee = _get_scoped_employee_or_404(employee_id)

    if request.method == "POST":
        leaving_date = parse_iso_date(request.form.get("leaving_date"))
        reason_category = request.form.get("leaving_reason_category")
        reason_detail = request.form.get("leaving_reason_detail")
        leaving_notes = request.form.get("leaving_notes")

        try:
            mark_employee_as_leaver(
                employee=employee,
                leaving_date=leaving_date,
                reason_category=reason_category,
                reason_detail=reason_detail,
                notes=leaving_notes,
                changed_by=current_user.username,
            )
            db.session.commit()

            flash(f"{employee.full_name} has been marked as a leaver.", "success")
            return redirect(url_for("manage_employee.detail", employee_id=employee.id))

        except ValueError as exc:
            db.session.rollback()
            flash(str(exc), "error")
            return render_template(
                "manage_employee/mark_leaver.html",
                employee=employee,
                leaving_reason_choices=LEAVING_REASON_CHOICES,
                form_data=request.form,
            )

    return render_template(
        "manage_employee/mark_leaver.html",
        employee=employee,
        leaving_reason_choices=LEAVING_REASON_CHOICES,
        form_data={},
    )


@manage_employee_bp.route("/manage-employees/<int:employee_id>/reactivate", methods=["POST"])
@login_required
def reactivate(employee_id):
    employee = _get_scoped_employee_or_404(employee_id)

    try:
        reactivate_employee(employee, changed_by=current_user.username)
        db.session.commit()
        flash(f"{employee.full_name} has been reactivated.", "success")

    except ValueError as exc:
        db.session.rollback()
        flash(str(exc), "info")

    return redirect(url_for("manage_employee.detail", employee_id=employee.id))