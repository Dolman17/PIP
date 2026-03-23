from __future__ import annotations

from flask import Blueprint, jsonify, request
from flask_login import login_required

from models import db, PIPRecord
from pip_app.services.taxonomy import (
    CURATED_TAGS,
    merge_curated_and_recent,
    pick_actions_from_templates,
)

taxonomy_bp = Blueprint("taxonomy", __name__)


@taxonomy_bp.route("/taxonomy/predefined_tags", methods=["GET"])
@login_required
def taxonomy_predefined_tags():
    category = (request.args.get("category") or "").strip()
    tags = CURATED_TAGS.get(category, [])
    return jsonify({"category": category, "tags": tags})


@taxonomy_bp.route("/taxonomy/categories", methods=["GET"])
@login_required
def taxonomy_categories():
    return jsonify({"categories": list(CURATED_TAGS.keys())})


@taxonomy_bp.route("/taxonomy/tags_suggest", methods=["GET"])
@login_required
def taxonomy_tags_suggest():
    q = (request.args.get("q") or "").strip().lower()
    category = (request.args.get("category") or "").strip()

    try:
        recent_rows = db.session.query(PIPRecord.tags).order_by(PIPRecord.id.desc()).limit(200).all()
    except Exception:
        recent_rows = []

    recent: list[str] = []
    for (tag_str,) in recent_rows:
        if not tag_str:
            continue
        if isinstance(tag_str, str):
            for tag in tag_str.split(","):
                clean = (tag or "").strip()
                if clean:
                    recent.append(clean)

    merged = merge_curated_and_recent(category, recent, cap=40)
    if q:
        merged = [tag for tag in merged if q in tag.lower()]

    return jsonify({"tags": merged[:30]})


@taxonomy_bp.route("/taxonomy/action_templates", methods=["GET"])
@login_required
def taxonomy_action_templates():
    category = (request.args.get("category") or "").strip()
    severity = (request.args.get("severity") or "").strip()
    items = pick_actions_from_templates(category, severity)
    return jsonify({"category": category, "severity": severity, "items": items})