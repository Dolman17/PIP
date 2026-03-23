from __future__ import annotations

from flask import current_app
from flask_login import current_user

from models import TimelineEvent, db


def log_timeline_event(pip_id: int, event_type: str, notes: str):
    try:
        ev = TimelineEvent(
            pip_record_id=pip_id,
            event_type=event_type,
            notes=notes,
            updated_by=getattr(current_user, "username", None) or "system",
        )
        db.session.add(ev)
        db.session.commit()
    except Exception as e:
        current_app.logger.exception(f"TimelineEvent failed: {e}")