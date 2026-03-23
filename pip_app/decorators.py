"""Reusable decorators for auth/role checks."""

from __future__ import annotations

from functools import wraps

from flask import abort
from flask_login import current_user


def superuser_required(func):
    """Allow access only to authenticated superusers.

    Mirrors current behaviour in app.py:
    - user must be authenticated
    - user must have is_superuser() returning True
    """
    @wraps(func)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            abort(401)

        checker = getattr(current_user, "is_superuser", None)

        allowed = False
        if callable(checker):
            allowed = bool(checker())
        else:
            allowed = bool(checker)

        if not allowed:
            abort(403)

        return func(*args, **kwargs)

    return decorated_function