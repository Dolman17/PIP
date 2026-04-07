from __future__ import annotations

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import case, func, or_
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


def _apply_service_filter(query, service_value: str):
    if service_value:
        query = query.filter(Employee.service == service_value)
    return query


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


@manage_employee_bp.route("/manage-employees/reporting")
@login_required
def reporting():
    start_date_raw = (request.args.get("start_date") or "").strip()
    end_date_raw = (request.args.get("end_date") or "").strip()
    selected_service = (request.args.get("service") or "").strip()

    start_date = parse_iso_date(start_date_raw) if start_date_raw else None
    end_date = parse_iso_date(end_date_raw) if end_date_raw else None

    if start_date and end_date and start_date > end_date:
        flash("Start date cannot be after end date.", "error")
        return redirect(url_for("manage_employee.reporting"))

    base_query = _scoped_employee_query()
    filtered_base_query = _apply_service_filter(base_query, selected_service)

    available_services_rows = (
        _scoped_employee_query()
        .with_entities(Employee.service)
        .filter(Employee.service.isnot(None), Employee.service != "")
        .distinct()
        .order_by(Employee.service.asc())
        .all()
    )
    available_services = [row[0] for row in available_services_rows]

    total_employees = filtered_base_query.count()
    active_employees = filtered_base_query.filter(Employee.is_leaver.is_(False)).count()
    leavers_count = filtered_base_query.filter(Employee.is_leaver.is_(True)).count()

    monthly_rows = (
        filtered_base_query.filter(
            Employee.is_leaver.is_(True),
            Employee.leaving_date.isnot(None),
        )
        .with_entities(
            func.extract("year", Employee.leaving_date).label("year"),
            func.extract("month", Employee.leaving_date).label("month"),
            func.count(Employee.id).label("count"),
        )
        .group_by(
            func.extract("year", Employee.leaving_date),
            func.extract("month", Employee.leaving_date),
        )
        .order_by(
            func.extract("year", Employee.leaving_date).asc(),
            func.extract("month", Employee.leaving_date).asc(),
        )
        .all()
    )

    leavers_by_month = []
    max_month_count = max((row.count for row in monthly_rows), default=0)

    for row in monthly_rows:
        year = int(row.year) if row.year is not None else None
        month = int(row.month) if row.month is not None else None
        label = f"{year}-{month:02d}" if year and month else "Unknown"
        width_pct = int((row.count / max_month_count) * 100) if max_month_count else 0
        leavers_by_month.append(
            {
                "year": year,
                "month": month,
                "label": label,
                "count": row.count,
                "width_pct": width_pct,
            }
        )

    reason_rows = (
        filtered_base_query.filter(Employee.is_leaver.is_(True))
        .with_entities(
            func.coalesce(Employee.leaving_reason_category, "Not Recorded").label("reason"),
            func.count(Employee.id).label("count"),
        )
        .group_by(func.coalesce(Employee.leaving_reason_category, "Not Recorded"))
        .order_by(func.count(Employee.id).desc())
        .all()
    )

    leavers_by_reason = [{"reason": row.reason, "count": row.count} for row in reason_rows]

    service_rows = (
        filtered_base_query.filter(Employee.is_leaver.is_(True))
        .with_entities(
            func.coalesce(Employee.service, "Not Recorded").label("service"),
            func.count(Employee.id).label("count"),
        )
        .group_by(func.coalesce(Employee.service, "Not Recorded"))
        .order_by(func.count(Employee.id).desc())
        .limit(20)
        .all()
    )

    leavers_by_service = [{"service": row.service, "count": row.count} for row in service_rows]

    period_leavers = None
    opening_headcount = None
    closing_headcount = None
    average_headcount = None
    turnover_percent = None

    if start_date and end_date:
        period_scope = _apply_service_filter(_scoped_employee_query(), selected_service)

        period_leavers = period_scope.filter(
            Employee.is_leaver.is_(True),
            Employee.leaving_date.isnot(None),
            Employee.leaving_date >= start_date,
            Employee.leaving_date <= end_date,
        ).count()

        opening_headcount = period_scope.filter(
            or_(Employee.start_date.is_(None), Employee.start_date <= start_date),
            or_(
                Employee.is_leaver.is_(False),
                Employee.leaving_date.is_(None),
                Employee.leaving_date >= start_date,
            ),
        ).count()

        closing_headcount = period_scope.filter(
            or_(Employee.start_date.is_(None), Employee.start_date <= end_date),
            or_(
                Employee.is_leaver.is_(False),
                Employee.leaving_date.is_(None),
                Employee.leaving_date >= end_date,
            ),
        ).count()

        average_headcount = round((opening_headcount + closing_headcount) / 2, 2)

        if average_headcount > 0:
            turnover_percent = round((period_leavers / average_headcount) * 100, 2)
        else:
            turnover_percent = 0.0

    service_split_rows = (
        filtered_base_query.with_entities(
            func.coalesce(Employee.service, "Not Recorded").label("service"),
            func.sum(
                case(
                    (Employee.is_leaver.is_(False), 1),
                    else_=0,
                )
            ).label("active_count"),
            func.sum(
                case(
                    (Employee.is_leaver.is_(True), 1),
                    else_=0,
                )
            ).label("leaver_count"),
        )
        .group_by(func.coalesce(Employee.service, "Not Recorded"))
        .order_by(func.coalesce(Employee.service, "Not Recorded").asc())
        .all()
    )

    active_vs_leavers_by_service = [
        {
            "service": row.service,
            "active_count": int(row.active_count or 0),
            "leaver_count": int(row.leaver_count or 0),
        }
        for row in service_split_rows
    ]

    return render_template(
        "manage_employee/reporting.html",
        total_employees=total_employees,
        active_employees=active_employees,
        leavers_count=leavers_count,
        leavers_by_month=leavers_by_month,
        leavers_by_reason=leavers_by_reason,
        leavers_by_service=leavers_by_service,
        available_services=available_services,
        selected_service=selected_service,
        start_date_raw=start_date_raw,
        end_date_raw=end_date_raw,
        period_leavers=period_leavers,
        opening_headcount=opening_headcount,
        closing_headcount=closing_headcount,
        average_headcount=average_headcount,
        turnover_percent=turnover_percent,
        active_vs_leavers_by_service=active_vs_leavers_by_service,
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
