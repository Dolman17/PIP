from datetime import date, timedelta

from flask import Blueprint, render_template
from flask_login import current_user, login_required
from sqlalchemy import or_

from models import (
    Employee,
    EmployeeRelationsCase,
    PIPRecord,
    ProbationRecord,
    SicknessCase,
    SupervisionAction,
    SupervisionRecord,
)
from pip_app.services.module_settings import get_enabled_modules

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
@login_required
def home():
    enabled_modules = get_enabled_modules(user=current_user)

    today = date.today()
<<<<<<< HEAD
    next_14_days = today + timedelta(days=14)
    missing_supervision_cutoff = today - timedelta(days=60)

    active_employees_query = Employee.query.filter(Employee.is_leaver.is_(False))
    leavers_query = Employee.query.filter(Employee.is_leaver.is_(True))

    if getattr(current_user, "organisation_id", None):
        active_employees_query = active_employees_query.filter(
            Employee.organisation_id == current_user.organisation_id
        )
        leavers_query = leavers_query.filter(
            Employee.organisation_id == current_user.organisation_id
        )

    if current_user.admin_level == 0:
        if current_user.team_id:
            active_employees_query = active_employees_query.filter(
                Employee.team_id == current_user.team_id
            )
            leavers_query = leavers_query.filter(Employee.team_id == current_user.team_id)
        else:
            active_employees_query = active_employees_query.filter(False)
            leavers_query = leavers_query.filter(False)

    active_employees = active_employees_query.count()
    leavers = leavers_query.count()

    open_pips = 0
    pip_reviews_due = 0
    recent_pips = []

    if enabled_modules.get("pip", True):
        pip_query = PIPRecord.query.join(Employee)

        if getattr(current_user, "organisation_id", None):
            pip_query = pip_query.filter(Employee.organisation_id == current_user.organisation_id)

        if current_user.admin_level == 0:
            if current_user.team_id:
                pip_query = pip_query.filter(Employee.team_id == current_user.team_id)
            else:
                pip_query = pip_query.filter(False)

        open_pips = pip_query.filter(PIPRecord.status != "Closed").count()
        pip_reviews_due = pip_query.filter(PIPRecord.status != "Closed").count()

        recent_pips = (
            pip_query.order_by(PIPRecord.last_updated.desc().nullslast())
=======
    next_7_days = today + timedelta(days=7)

    active_employees = Employee.query.filter(Employee.is_leaver.is_(False)).count()
    leavers = Employee.query.filter(Employee.is_leaver.is_(True)).count()

    open_pips = 0
    pip_reviews_due = 0
    overdue_pips_count = 0
    due_soon_pips_count = 0
    recent_pips = []
    overdue_pips = []
    due_soon_pips = []

    if enabled_modules.get("pip", True):
        pip_open_query = PIPRecord.query.filter(PIPRecord.status != "Closed")

        open_pips = pip_open_query.count()

        overdue_pips = (
            pip_open_query.filter(
                PIPRecord.review_date.isnot(None),
                PIPRecord.review_date < today,
            )
            .order_by(PIPRecord.review_date.asc())
            .limit(5)
            .all()
        )
        overdue_pips_count = (
            pip_open_query.filter(
                PIPRecord.review_date.isnot(None),
                PIPRecord.review_date < today,
            ).count()
        )

        due_soon_pips = (
            pip_open_query.filter(
                PIPRecord.review_date.isnot(None),
                PIPRecord.review_date >= today,
                PIPRecord.review_date <= next_7_days,
            )
            .order_by(PIPRecord.review_date.asc())
            .limit(5)
            .all()
        )
        due_soon_pips_count = (
            pip_open_query.filter(
                PIPRecord.review_date.isnot(None),
                PIPRecord.review_date >= today,
                PIPRecord.review_date <= next_7_days,
            ).count()
        )

        pip_reviews_due = overdue_pips_count + due_soon_pips_count

        recent_pips = (
            PIPRecord.query.order_by(PIPRecord.last_updated.desc().nullslast())
>>>>>>> dffbed5134b4aeee3524feace0664247e17912a1
            .limit(5)
            .all()
        )

    active_probations = 0
    probation_reviews_due = 0
    overdue_probations_count = 0
    due_soon_probations_count = 0
    recent_probations = []
<<<<<<< HEAD

    if enabled_modules.get("probation", True):
        probation_query = ProbationRecord.query.join(Employee)

        if getattr(current_user, "organisation_id", None):
            probation_query = probation_query.filter(
                Employee.organisation_id == current_user.organisation_id
            )

        if current_user.admin_level == 0:
            if current_user.team_id:
                probation_query = probation_query.filter(Employee.team_id == current_user.team_id)
            else:
                probation_query = probation_query.filter(False)

        active_probations = probation_query.filter(
            ProbationRecord.status.in_(["Active", "Extended"])
        ).count()

        probation_reviews_due = probation_query.filter(
=======
    overdue_probations = []
    due_soon_probations = []

    if enabled_modules.get("probation", True):
        probation_open_query = ProbationRecord.query.filter(
>>>>>>> dffbed5134b4aeee3524feace0664247e17912a1
            ProbationRecord.status.in_(["Active", "Extended"])
        )

        active_probations = probation_open_query.count()

        overdue_probations = (
            probation_open_query.filter(
                ProbationRecord.expected_end_date.isnot(None),
                ProbationRecord.expected_end_date < today,
            )
            .order_by(ProbationRecord.expected_end_date.asc())
            .limit(5)
            .all()
        )
        overdue_probations_count = (
            probation_open_query.filter(
                ProbationRecord.expected_end_date.isnot(None),
                ProbationRecord.expected_end_date < today,
            ).count()
        )

        due_soon_probations = (
            probation_open_query.filter(
                ProbationRecord.expected_end_date.isnot(None),
                ProbationRecord.expected_end_date >= today,
                ProbationRecord.expected_end_date <= next_7_days,
            )
            .order_by(ProbationRecord.expected_end_date.asc())
            .limit(5)
            .all()
        )
        due_soon_probations_count = (
            probation_open_query.filter(
                ProbationRecord.expected_end_date.isnot(None),
                ProbationRecord.expected_end_date >= today,
                ProbationRecord.expected_end_date <= next_7_days,
            ).count()
        )

        probation_reviews_due = overdue_probations_count + due_soon_probations_count

        recent_probations = (
            probation_query.order_by(ProbationRecord.last_updated.desc().nullslast())
            .limit(5)
            .all()
        )

    open_sickness_cases = 0
    sickness_follow_up_needed = 0
    long_term_sickness_count = 0
    recent_sickness_cases = []
<<<<<<< HEAD

    if enabled_modules.get("sickness", True):
        sickness_query = SicknessCase.query.join(Employee)

        if getattr(current_user, "organisation_id", None):
            sickness_query = sickness_query.filter(
                Employee.organisation_id == current_user.organisation_id
            )

        if current_user.admin_level == 0:
            if current_user.team_id:
                sickness_query = sickness_query.filter(Employee.team_id == current_user.team_id)
            else:
                sickness_query = sickness_query.filter(False)

        open_sickness_cases = sickness_query.filter(
            SicknessCase.status.in_(["Open", "Monitoring"])
        ).count()

        sickness_follow_up_needed = sickness_query.filter(
=======
    open_sickness_case_list = []
    long_term_sickness_cases = []

    if enabled_modules.get("sickness", True):
        sickness_open_query = SicknessCase.query.filter(
>>>>>>> dffbed5134b4aeee3524feace0664247e17912a1
            SicknessCase.status.in_(["Open", "Monitoring"])
        )

        open_sickness_cases = sickness_open_query.count()

        open_sickness_case_list = (
            sickness_open_query.order_by(SicknessCase.start_date.asc().nullsfirst())
            .limit(5)
            .all()
        )

        long_term_sickness_cases = (
            sickness_open_query.filter(SicknessCase.trigger_type == "long_term")
            .order_by(SicknessCase.start_date.asc().nullsfirst())
            .limit(5)
            .all()
        )
        long_term_sickness_count = (
            sickness_open_query.filter(SicknessCase.trigger_type == "long_term").count()
        )

        sickness_follow_up_needed = open_sickness_cases

        recent_sickness_cases = (
            sickness_query.order_by(SicknessCase.updated_at.desc().nullslast())
            .limit(5)
            .all()
        )

    open_er_cases = 0
    overdue_er_cases_count = 0
    recent_er_cases = []
<<<<<<< HEAD

    if current_user.is_superuser() and enabled_modules.get("employee_relations", True):
        er_query = EmployeeRelationsCase.query.join(Employee)

        if getattr(current_user, "organisation_id", None):
            er_query = er_query.filter(Employee.organisation_id == current_user.organisation_id)

        open_er_cases = er_query.filter(EmployeeRelationsCase.status != "Closed").count()

        recent_er_cases = (
            er_query.order_by(EmployeeRelationsCase.updated_at.desc().nullslast())
=======
    overdue_er_cases = []

    if current_user.is_superuser() and enabled_modules.get("employee_relations", True):
        er_open_query = EmployeeRelationsCase.query.filter(
            EmployeeRelationsCase.status != "Closed"
        )

        open_er_cases = er_open_query.count()

        overdue_er_cases = (
            er_open_query.filter(
                EmployeeRelationsCase.next_action_date.isnot(None),
                EmployeeRelationsCase.next_action_date < today,
            )
            .order_by(EmployeeRelationsCase.next_action_date.asc())
>>>>>>> dffbed5134b4aeee3524feace0664247e17912a1
            .limit(5)
            .all()
        )
        overdue_er_cases_count = (
            er_open_query.filter(
                EmployeeRelationsCase.next_action_date.isnot(None),
                EmployeeRelationsCase.next_action_date < today,
            ).count()
        )

<<<<<<< HEAD
    scheduled_supervisions = 0
    overdue_supervisions_count = 0
    open_supervision_actions_count = 0
    actions_due_soon_count = 0
    employees_missing_supervision_count = 0
    recent_supervisions = []
    overdue_supervisions = []
    open_supervision_actions = []

    if enabled_modules.get("supervision", True):
        supervision_query = SupervisionRecord.query.join(Employee)

        if getattr(current_user, "organisation_id", None):
            supervision_query = supervision_query.filter(
                Employee.organisation_id == current_user.organisation_id
            )

        if current_user.admin_level == 0:
            if current_user.team_id:
                supervision_query = supervision_query.filter(Employee.team_id == current_user.team_id)
            else:
                supervision_query = supervision_query.filter(False)

        scheduled_supervisions = supervision_query.filter(
            SupervisionRecord.status == "Scheduled",
            SupervisionRecord.meeting_date >= today,
        ).count()

        overdue_supervisions_count = supervision_query.filter(
            or_(
                SupervisionRecord.status == "Overdue",
                (
                    (SupervisionRecord.status == "Scheduled")
                    & (SupervisionRecord.meeting_date < today)
                ),
            )
        ).count()

        recent_supervisions = (
            supervision_query.order_by(
                SupervisionRecord.meeting_date.desc(),
                SupervisionRecord.updated_at.desc(),
=======
        recent_er_cases = (
            EmployeeRelationsCase.query.order_by(
                EmployeeRelationsCase.updated_at.desc().nullslast()
>>>>>>> dffbed5134b4aeee3524feace0664247e17912a1
            )
            .limit(5)
            .all()
        )

        overdue_supervisions = (
            supervision_query.filter(
                or_(
                    SupervisionRecord.status == "Overdue",
                    (
                        (SupervisionRecord.status == "Scheduled")
                        & (SupervisionRecord.meeting_date < today)
                    ),
                )
            )
            .order_by(SupervisionRecord.meeting_date.asc())
            .limit(5)
            .all()
        )

        action_query = SupervisionAction.query.join(Employee)

        if getattr(current_user, "organisation_id", None):
            action_query = action_query.filter(
                Employee.organisation_id == current_user.organisation_id
            )

        if current_user.admin_level == 0:
            if current_user.team_id:
                action_query = action_query.filter(Employee.team_id == current_user.team_id)
            else:
                action_query = action_query.filter(False)

        open_supervision_actions_count = action_query.filter(
            SupervisionAction.status.in_(["Open", "Carried Forward"])
        ).count()

        actions_due_soon_count = action_query.filter(
            SupervisionAction.status.in_(["Open", "Carried Forward"]),
            SupervisionAction.due_date.isnot(None),
            SupervisionAction.due_date <= next_14_days,
        ).count()

        open_supervision_actions = (
            action_query.filter(SupervisionAction.status.in_(["Open", "Carried Forward"]))
            .order_by(SupervisionAction.due_date.asc().nullslast())
            .limit(5)
            .all()
        )

        employees_for_missing_check = active_employees_query.all()
        missing_count = 0

        for employee in employees_for_missing_check:
            latest = (
                supervision_query.filter(SupervisionRecord.employee_id == employee.id)
                .order_by(SupervisionRecord.meeting_date.desc())
                .first()
            )

            if latest is None or latest.meeting_date < missing_supervision_cutoff:
                missing_count += 1

        employees_missing_supervision_count = missing_count

    employee_records_missing_email_query = Employee.query.filter(
        Employee.is_leaver.is_(False),
        or_(Employee.email.is_(None), Employee.email == ""),
    )

    if getattr(current_user, "organisation_id", None):
        employee_records_missing_email_query = employee_records_missing_email_query.filter(
            Employee.organisation_id == current_user.organisation_id
        )

    if current_user.admin_level == 0:
        if current_user.team_id:
            employee_records_missing_email_query = employee_records_missing_email_query.filter(
                Employee.team_id == current_user.team_id
            )
        else:
            employee_records_missing_email_query = employee_records_missing_email_query.filter(False)

    employee_records_missing_email = employee_records_missing_email_query.count()

    recent_leavers = (
        leavers_query.order_by(Employee.leaving_date.desc().nullslast(), Employee.last_name.asc())
        .limit(5)
        .all()
    )

    module_count = 0
    if enabled_modules.get("pip", True):
        module_count += 1
    if enabled_modules.get("probation", True):
        module_count += 1
    if enabled_modules.get("sickness", True):
        module_count += 1
    if enabled_modules.get("supervision", True):
        module_count += 1
    if current_user.is_superuser() and enabled_modules.get("employee_relations", True):
        module_count += 1

    workspace_stats = {
        "active_employees": active_employees,
        "leavers": leavers,
        "open_pips": open_pips,
        "active_probations": active_probations,
        "open_sickness_cases": open_sickness_cases,
        "open_er_cases": open_er_cases,
        "module_count": module_count,
        "probation_reviews_due": probation_reviews_due,
        "pip_reviews_due": pip_reviews_due,
        "sickness_follow_up_needed": sickness_follow_up_needed,
        "employee_records_missing_email": employee_records_missing_email,
<<<<<<< HEAD
        "scheduled_supervisions": scheduled_supervisions,
        "overdue_supervisions": overdue_supervisions_count,
        "open_supervision_actions": open_supervision_actions_count,
        "supervision_actions_due_soon": actions_due_soon_count,
        "employees_missing_supervision": employees_missing_supervision_count,
=======
        "overdue_pips_count": overdue_pips_count,
        "due_soon_pips_count": due_soon_pips_count,
        "overdue_probations_count": overdue_probations_count,
        "due_soon_probations_count": due_soon_probations_count,
        "long_term_sickness_count": long_term_sickness_count,
        "overdue_er_cases_count": overdue_er_cases_count,
>>>>>>> dffbed5134b4aeee3524feace0664247e17912a1
    }

    return render_template(
        "select_module.html",
        hide_sidebar=True,
        layout="fullscreen",
        enabled_modules=enabled_modules,
        workspace_stats=workspace_stats,
        recent_leavers=recent_leavers,
        recent_pips=recent_pips,
        recent_probations=recent_probations,
        recent_sickness_cases=recent_sickness_cases,
        recent_er_cases=recent_er_cases,
<<<<<<< HEAD
        recent_supervisions=recent_supervisions,
        overdue_supervisions=overdue_supervisions,
        open_supervision_actions=open_supervision_actions,
    )
=======
        overdue_pips=overdue_pips,
        due_soon_pips=due_soon_pips,
        overdue_probations=overdue_probations,
        due_soon_probations=due_soon_probations,
        open_sickness_case_list=open_sickness_case_list,
        long_term_sickness_cases=long_term_sickness_cases,
        overdue_er_cases=overdue_er_cases,
        today=today,
        next_7_days=next_7_days,
    )
>>>>>>> dffbed5134b4aeee3524feace0664247e17912a1
