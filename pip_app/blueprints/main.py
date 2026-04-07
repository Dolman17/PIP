from flask import Blueprint, render_template
from flask_login import current_user, login_required
from sqlalchemy import or_

from models import (
    Employee,
    EmployeeRelationsCase,
    PIPRecord,
    ProbationRecord,
    SicknessCase,
)

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
@login_required
def home():
    active_employees = Employee.query.filter(Employee.is_leaver.is_(False)).count()
    leavers = Employee.query.filter(Employee.is_leaver.is_(True)).count()

    open_pips = PIPRecord.query.filter(PIPRecord.status != "Closed").count()

    active_probations = ProbationRecord.query.filter(
        ProbationRecord.status.in_(["Active", "Extended"])
    ).count()

    open_sickness_cases = SicknessCase.query.filter(
        SicknessCase.status.in_(["Open", "Monitoring"])
    ).count()

    open_er_cases = 0
    if current_user.is_superuser():
        open_er_cases = EmployeeRelationsCase.query.filter(
            EmployeeRelationsCase.status != "Closed"
        ).count()

    probation_reviews_due = ProbationRecord.query.filter(
        ProbationRecord.status.in_(["Active", "Extended"])
    ).count()

    pip_reviews_due = PIPRecord.query.filter(PIPRecord.status != "Closed").count()

    sickness_follow_up_needed = SicknessCase.query.filter(
        SicknessCase.status.in_(["Open", "Monitoring"])
    ).count()

    employee_records_missing_email = Employee.query.filter(
        Employee.is_leaver.is_(False),
        or_(Employee.email.is_(None), Employee.email == ""),
    ).count()

    recent_leavers = (
        Employee.query.filter(Employee.is_leaver.is_(True))
        .order_by(Employee.leaving_date.desc().nullslast(), Employee.last_name.asc())
        .limit(5)
        .all()
    )

    recent_pips = (
        PIPRecord.query.order_by(PIPRecord.last_updated.desc().nullslast())
        .limit(5)
        .all()
    )

    recent_probations = (
        ProbationRecord.query.order_by(ProbationRecord.last_updated.desc().nullslast())
        .limit(5)
        .all()
    )

    recent_sickness_cases = (
        SicknessCase.query.order_by(SicknessCase.updated_at.desc().nullslast())
        .limit(5)
        .all()
    )

    recent_er_cases = []
    if current_user.is_superuser():
        recent_er_cases = (
            EmployeeRelationsCase.query.order_by(EmployeeRelationsCase.updated_at.desc().nullslast())
            .limit(5)
            .all()
        )

    workspace_stats = {
        "active_employees": active_employees,
        "leavers": leavers,
        "open_pips": open_pips,
        "active_probations": active_probations,
        "open_sickness_cases": open_sickness_cases,
        "open_er_cases": open_er_cases,
        "module_count": 4 if current_user.is_superuser() else 3,
        "probation_reviews_due": probation_reviews_due,
        "pip_reviews_due": pip_reviews_due,
        "sickness_follow_up_needed": sickness_follow_up_needed,
        "employee_records_missing_email": employee_records_missing_email,
    }

    return render_template(
        "select_module.html",
        hide_sidebar=True,
        layout="fullscreen",
        workspace_stats=workspace_stats,
        recent_leavers=recent_leavers,
        recent_pips=recent_pips,
        recent_probations=recent_probations,
        recent_sickness_cases=recent_sickness_cases,
        recent_er_cases=recent_er_cases,
    )
