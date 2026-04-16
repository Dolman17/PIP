from __future__ import annotations

from datetime import datetime
from functools import wraps

from flask import abort, g

from pip_app.extensions import db
from models import APIKey
from pip_app.security import get_bearer_token, hash_api_key


def require_api_key(scope: str):
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(*args, **kwargs):
            token = get_bearer_token()
            if not token:
                abort(401)

            key_hash = hash_api_key(token)
            api_key = APIKey.query.filter_by(key_hash=key_hash, is_active=True).first()
            if not api_key:
                abort(401)

            if api_key.expires_at and api_key.expires_at < datetime.utcnow():
                abort(401)

            if not api_key.has_scope(scope):
                abort(403)

            api_key.last_used_at = datetime.utcnow()
            db.session.commit()

            g.api_key = api_key
            return view_func(*args, **kwargs)

        return wrapper

    return decorator