from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime


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

    pips = db.relationship('PIPRecord', back_populates='employee', lazy=True)

class PIPRecord(db.Model):
    __tablename__ = 'pip_record'

    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employee.id'), nullable=False)
    concerns = db.Column(db.Text, nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    review_date = db.Column(db.Date, nullable=False)
    meeting_notes = db.Column(db.Text)
    status = db.Column(db.String(20), default='Open')
    created_by = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

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
    pip_record_id = db.Column(db.Integer, db.ForeignKey('pip_record.id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    event_type = db.Column(db.String(100))
    notes = db.Column(db.Text)
    updated_by = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    pip_record = db.relationship(
        'PIPRecord',
        back_populates='timeline_events'
    )
