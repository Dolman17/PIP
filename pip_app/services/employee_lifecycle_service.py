from __future__ import annotations

from typing import Optional

from pip_app.services.time_utils import now_local


def _clean_text(value: Optional[str]) -> Optional[str]:
    return (value or "").strip() or None


def get_employee_status_label(employee) -> str:
    if getattr(employee, "is_leaver", False):
        return "Leaver"
    return getattr(employee, "employment_status", None) or "Active"


def mark_employee_as_leaver(
    employee,
    leaving_date,
    reason_category: Optional[str] = None,
    reason_detail: Optional[str] = None,
    notes: Optional[str] = None,
    changed_by: Optional[str] = None,
):
    if getattr(employee, "is_leaver", False):
        raise ValueError("Employee is already marked as a leaver.")

    if not leaving_date:
        raise ValueError("A valid leaving date is required.")

    cleaned_reason_category = _clean_text(reason_category)
    if not cleaned_reason_category:
        raise ValueError("A leaving reason category is required.")

    employee.employment_status = "Leaver"
    employee.is_leaver = True
    employee.leaving_date = leaving_date
    employee.leaving_reason_category = cleaned_reason_category
    employee.leaving_reason_detail = _clean_text(reason_detail)
    employee.leaving_notes = _clean_text(notes)
    employee.marked_as_leaver_at = now_local()
    employee.marked_as_leaver_by = _clean_text(changed_by)

    return {
        "action": "marked_as_leaver",
        "employee_id": getattr(employee, "id", None),
        "employee_name": getattr(employee, "full_name", None) or f"{getattr(employee, 'first_name', '')} {getattr(employee, 'last_name', '')}".strip(),
        "employment_status": employee.employment_status,
        "leaving_date": employee.leaving_date,
        "leaving_reason_category": employee.leaving_reason_category,
        "changed_by": employee.marked_as_leaver_by,
        "changed_at": employee.marked_as_leaver_at,
    }


def reactivate_employee(
    employee,
    changed_by: Optional[str] = None,
):
    if not getattr(employee, "is_leaver", False):
        raise ValueError("Employee is already active.")

    employee.employment_status = "Active"
    employee.is_leaver = False
    employee.reactivated_at = now_local()
    employee.reactivated_by = _clean_text(changed_by)

    # Keep historic leave fields intact for now so historic leave data is preserved.

    return {
        "action": "reactivated",
        "employee_id": getattr(employee, "id", None),
        "employee_name": getattr(employee, "full_name", None) or f"{getattr(employee, 'first_name', '')} {getattr(employee, 'last_name', '')}".strip(),
        "employment_status": employee.employment_status,
        "changed_by": employee.reactivated_by,
        "changed_at": employee.reactivated_at,
    }