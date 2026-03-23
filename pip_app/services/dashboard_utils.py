from __future__ import annotations

from flask_login import current_user
from sqlalchemy.sql import func

from models import Employee, PIPRecord


def open_pips_scoped_query():
    base = PIPRecord.query.filter(PIPRecord.status == 'Open')
    if current_user.admin_level == 0:
        base = base.join(Employee).filter(Employee.team_id == current_user.team_id)
    return base


def counts_by_field(field_expr):
    q = open_pips_scoped_query().with_entities(field_expr, func.count(PIPRecord.id)).group_by(field_expr)
    rows = q.all()
    out = {}
    for label, cnt in rows:
        out[(label or "Unspecified")] = int(cnt or 0)
    return out