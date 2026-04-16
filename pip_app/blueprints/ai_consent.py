from __future__ import annotations

from flask import Blueprint, jsonify, request, g
from flask_login import current_user, login_required

from pip_app.extensions import db
from models import AIConsentLog

ai_consent_bp = Blueprint("ai_consent", __name__)


@ai_consent_bp.route("/ai/consent", methods=["POST"])
@login_required
def record_ai_consent():
    payload = request.get_json(silent=True) or {}

    context = (payload.get("context") or "").strip()
    accepted = bool(payload.get("accepted"))

    if not context:
        return jsonify({"ok": False, "error": "Missing context"}), 400

    consent = AIConsentLog(
        user_id=current_user.id,
        context=context[:100],
        accepted=accepted,
        request_ip=getattr(g, "request_ip", None),
        user_agent=getattr(g, "user_agent", None),
    )
    db.session.add(consent)
    db.session.commit()

    return jsonify({"ok": True})