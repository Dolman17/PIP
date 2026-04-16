from __future__ import annotations

import hashlib
import secrets
from datetime import datetime
from typing import Optional

from flask import abort, g, request, session
from flask_login import current_user

from pip_app.extensions import db
from pip_app.models import TimelineEvent


def init_security(app):
    @app.before_request
    def capture_request_context():
        g.request_ip = get_request_ip()
        g.user_agent = (request.headers.get("User-Agent") or "")[:500]
        session.permanent = True

    @app.after_request
    def apply_security_headers(response):
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        response.headers["Cross-Origin-Opener-Policy"] = "same-origin"

        # Keep this pragmatic for current Jinja/Tailwind setup.
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "img-src 'self' data: https:; "
            "style-src 'self' 'unsafe-inline' https:; "
            "script-src 'self' 'unsafe-inline' https:; "
            "font-src 'self' https: data:; "
            "connect-src 'self' https:; "
            "frame-ancestors 'self'; "
            "base-uri 'self'; "
            "form-action 'self'"
        )
        return response


def get_request_ip() -> str:
    forwarded_for = request.headers.get("X-Forwarded-For", "")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()[:100]
    return (request.remote_addr or "")[:100]


def is_admin_user() -> bool:
    return bool(
        current_user.is_authenticated
        and hasattr(current_user, "is_admin")
        and current_user.is_admin()
    )


def is_line_manager_user() -> bool:
    return bool(
        current_user.is_authenticated
        and getattr(current_user, "admin_level", None) == 0
    )


def can_access_team(team_id: Optional[int]) -> bool:
    if not current_user.is_authenticated:
        return False
    if is_admin_user():
        return True
    return bool(team_id and getattr(current_user, "team_id", None) == team_id)


def scoped_employee_query(query, employee_model):
    if not current_user.is_authenticated:
        return query.filter(False)

    if is_admin_user():
        return query

    if getattr(current_user, "team_id", None):
        return query.filter(employee_model.team_id == current_user.team_id)

    return query.filter(False)


def require_employee_access(employee):
    if is_admin_user():
        return

    if not current_user.is_authenticated:
        abort(401)

    if getattr(employee, "team_id", None) != getattr(current_user, "team_id", None):
        abort(403)


def require_pip_access(pip_record):
    employee = getattr(pip_record, "employee", None)
    if employee is None:
        abort(403)
    require_employee_access(employee)


def require_probation_access(probation_record):
    employee = getattr(probation_record, "employee", None)
    if employee is None:
        abort(403)
    require_employee_access(employee)


def require_sickness_access(sickness_case):
    employee = getattr(sickness_case, "employee", None)
    if employee is None:
        abort(403)
    require_employee_access(employee)


def require_er_case_access(er_case):
    employee = getattr(er_case, "employee", None)
    if employee is None:
        abort(403)
    require_employee_access(employee)


def log_security_event(
    *,
    event_type: str,
    notes: str = "",
    pip_record_id: Optional[int] = None,
    updated_by: Optional[str] = None,
    commit: bool = True,
):
    actor = updated_by or (
        current_user.username
        if getattr(current_user, "is_authenticated", False)
        else "system"
    )

    event = TimelineEvent(
        pip_record_id=pip_record_id,
        event_type=event_type,
        notes=notes,
        updated_by=actor,
        timestamp=datetime.utcnow(),
        created_at=datetime.utcnow(),
    )
    db.session.add(event)
    if commit:
        db.session.commit()
    return event


def generate_api_key_pair() -> tuple[str, str, str]:
    raw_key = f"ph_live_{secrets.token_urlsafe(32)}"
    key_prefix = raw_key[:12]
    key_hash = hashlib.sha256(raw_key.encode("utf-8")).hexdigest()
    return raw_key, key_prefix, key_hash


def hash_api_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


def get_bearer_token() -> Optional[str]:
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return None
    return auth_header.replace("Bearer ", "", 1).strip() or None