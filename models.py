from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.sql import func
import json  # needed for ImportJob.errors()

db = SQLAlchemy()

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    admin_level = db.Column(db.Integer, default=0)  # 0 = line mgr, 1 = admin, 2 = superuser
    team_id = db.Column(db.Integer, nullable=True)

    def is_admin(self):
        return self.admin_level >= 1

    def is_superuser(self):
        return self.admin_level == 2


class Employee(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(100))
    last_name = db.Column(db.String(100))
    job_title = db.Column(db.String(100))
    line_manager = db.Column(db.String(100))
    service = db.Column(db.String(100))
    start_date = db.Column(db.Date)
    team_id = db.Column(db.Integer)
    email = db.Column(db.String(120), nullable=True)

    pips = db.relationship('PIPRecord', back_populates='employee', lazy=True)


class PIPRecord(db.Model):
    __tablename__ = 'pip_record'

    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employee.id'), nullable=False)

    # Core PIP fields
    concerns = db.Column(db.Text, nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    review_date = db.Column(db.Date, nullable=False)
    meeting_notes = db.Column(db.Text)
    status = db.Column(db.String(20), default='Open')
    created_by = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Legacy/simple AI field (kept for backward compatibility)
    ai_advice = db.Column(db.Text)
    ai_advice_generated_at = db.Column(db.DateTime)

    # Invitation (capability/initial meeting) details used by the Invite letter
    capability_meeting_date = db.Column(db.DateTime, nullable=True)
    capability_meeting_time = db.Column(db.String, nullable=True)
    capability_meeting_venue = db.Column(db.String, nullable=True)

    # Classification / tagging
    concern_category = db.Column(db.String(100))
    severity = db.Column(db.String(50))
    frequency = db.Column(db.String(50))
    tags = db.Column(db.Text)

    # -------- New AI-integrated structured fields for documents --------
    # High-level AI narrative summary to include in letters
    ai_summary = db.Column(db.Text, nullable=True)

    # Raw structured suggestions returned by AI (list[dict] or list[str])
    ai_action_suggestions = db.Column(JSON, nullable=True)

    # “Next up” nudges from AI (list[dict] or list[str])
    ai_next_up = db.Column(JSON, nullable=True)

    # Subset of suggestions the manager accepted for the plan (list[dict] or list[str])
    ai_actions_accepted = db.Column(JSON, nullable=True)

    # Outcome fields for the outcome letter
    outcome_status = db.Column(db.String(50), nullable=True)  # e.g., Successful, Extended, Unsuccessful
    outcome_notes = db.Column(db.Text, nullable=True)
    # -------------------------------------------------------------------

    # Relationships
    employee = db.relationship('Employee', back_populates='pips')
    action_items = db.relationship(
        'PIPActionItem',
        back_populates='pip_record',
        cascade='all, delete-orphan',
        lazy=True
    )
    timeline_events = db.relationship(
        'TimelineEvent',
        back_populates='pip_record',
        cascade='all, delete-orphan',
        lazy=True
    )


class PIPActionItem(db.Model):
    __tablename__ = 'pip_action_item'

    id = db.Column(db.Integer, primary_key=True)
    pip_record_id = db.Column(db.Integer, db.ForeignKey('pip_record.id'), nullable=False)
    description = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default='Outstanding')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    pip_record = db.relationship(
        'PIPRecord',
        back_populates='action_items'
    )


class TimelineEvent(db.Model):
    __tablename__ = 'timeline_event'

    id = db.Column(db.Integer, primary_key=True)
    pip_record_id = db.Column(db.Integer, db.ForeignKey('pip_record.id'), nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    event_type = db.Column(db.String(100))
    notes = db.Column(db.Text)
    updated_by = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    pip_record = db.relationship(
        'PIPRecord',
        back_populates='timeline_events'
    )


class ProbationRecord(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employee.id'), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    expected_end_date = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(50), default="Active")  # Active, Extended, Completed, Failed
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    reviews = db.relationship('ProbationReview', backref='probation', lazy=True, cascade="all, delete-orphan")
    plans = db.relationship('ProbationPlan', backref='probation', lazy=True, cascade="all, delete-orphan")

    employee = db.relationship('Employee', backref=db.backref('probation_records', lazy=True))


class ProbationReview(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    probation_id = db.Column(db.Integer, db.ForeignKey('probation_record.id'), nullable=False)
    review_date = db.Column(db.Date, nullable=False)
    reviewer = db.Column(db.String(100))
    summary = db.Column(db.Text)
    concerns_flag = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class ProbationPlan(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    probation_id = db.Column(db.Integer, db.ForeignKey('probation_record.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    objectives = db.Column(db.Text)  # Optionally replace with structured fields later
    deadline = db.Column(db.Date)
    outcome = db.Column(db.String(100))  # e.g., Met, Not Met, Ongoing


class DraftPIP(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    step = db.Column(db.Integer)
    data = db.Column(db.JSON)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_dismissed = db.Column(db.Boolean, default=False)

    user = db.relationship('User', backref='draft_pips')


class DraftProbation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    employee_id = db.Column(db.Integer, nullable=True)
    step = db.Column(db.Integer, default=1)
    name = db.Column(db.String(120), default="Untitled Probation Draft")
    payload = db.Column(db.JSON, default={})  # store step data incrementally
    is_dismissed = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now())
    updated_at = db.Column(db.DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

    __table_args__ = (
        db.Index('ix_probation_draft_user_active', 'user_id', 'is_dismissed'),
    )


class ImportJob(db.Model):
    __tablename__ = 'import_jobs'
    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    created_by = db.Column(db.String(120), nullable=False)
    source_filename = db.Column(db.String(255), nullable=False)
    total_rows = db.Column(db.Integer, nullable=False)
    imported_rows = db.Column(db.Integer, nullable=False, default=0)
    skipped_rows = db.Column(db.Integer, nullable=False, default=0)
    errors_json = db.Column(db.Text, nullable=True)  # store per-row errors / warnings

    def errors(self):
        try:
            return json.loads(self.errors_json or '[]')
        except Exception:
            return []
