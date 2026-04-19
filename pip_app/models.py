from pip_app.extensions import db
from flask_login import UserMixin
from datetime import datetime
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.sql import func
import json  # needed for ImportJob.errors()


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    admin_level = db.Column(db.Integer, default=0)  # 0 = line mgr, 1 = admin, 2 = superuser
    team_id = db.Column(db.Integer, nullable=True)

    organisation_id = db.Column(
        db.Integer,
        db.ForeignKey("organisations.id"),
        nullable=True,
        index=True,
    )

    organisation = db.relationship(
        "Organisation",
        backref=db.backref("users", lazy=True),
    )

    def is_admin(self):
        return self.admin_level >= 1

    def is_superuser(self):
        return self.admin_level == 2

    def is_manager(self):
        return self.admin_level == 0

    def can_access_team(self, team_id):
        if self.is_admin():
            return True
        return bool(self.team_id and team_id and self.team_id == team_id)


class Employee(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    organisation_id = db.Column(
        db.Integer,
        db.ForeignKey("organisations.id"),
        nullable=True,
        index=True,
    )

    first_name = db.Column(db.String(100))
    last_name = db.Column(db.String(100))
    job_title = db.Column(db.String(100))
    line_manager = db.Column(db.String(100))
    service = db.Column(db.String(100))
    start_date = db.Column(db.Date)
    team_id = db.Column(db.Integer)
    email = db.Column(db.String(120), nullable=True)

    # --- Manage Employee / lifecycle fields ---
    employment_status = db.Column(db.String(20), nullable=False, default="Active")
    is_leaver = db.Column(db.Boolean, nullable=False, default=False)

    leaving_date = db.Column(db.Date, nullable=True)
    leaving_reason_category = db.Column(db.String(100), nullable=True)
    leaving_reason_detail = db.Column(db.Text, nullable=True)
    leaving_notes = db.Column(db.Text, nullable=True)

    marked_as_leaver_at = db.Column(db.DateTime, nullable=True)
    marked_as_leaver_by = db.Column(db.String(120), nullable=True)

    reactivated_at = db.Column(db.DateTime, nullable=True)
    reactivated_by = db.Column(db.String(120), nullable=True)
    # --- end lifecycle fields ---

    organisation = db.relationship(
        "Organisation",
        backref=db.backref("employees", lazy=True),
    )

    pips = db.relationship("PIPRecord", back_populates="employee", lazy=True)

    @property
    def full_name(self):
        return f"{self.first_name or ''} {self.last_name or ''}".strip()

    @property
    def status_label(self):
        return "Leaver" if self.is_leaver else (self.employment_status or "Active")


class PIPRecord(db.Model):
    __tablename__ = "pip_record"

    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey("employee.id"), nullable=False)
    assigned_to = db.Column(
        db.Integer, db.ForeignKey("user.id"), nullable=True
    )

    # Core PIP fields
    concerns = db.Column(db.Text, nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    review_date = db.Column(db.Date, nullable=False)
    meeting_notes = db.Column(db.Text)
    status = db.Column(db.String(20), default="Open")
    created_by = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_updated = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

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
    ai_summary = db.Column(db.Text, nullable=True)
    ai_action_suggestions = db.Column(JSON, nullable=True)
    ai_next_up = db.Column(JSON, nullable=True)
    ai_actions_accepted = db.Column(JSON, nullable=True)

    # Outcome fields for the outcome letter
    outcome_status = db.Column(db.String(50), nullable=True)
    outcome_notes = db.Column(db.Text, nullable=True)
    # -------------------------------------------------------------------

    # Relationships
    employee = db.relationship("Employee", back_populates="pips")
    assignee = db.relationship("User", backref="assigned_pips")
    action_items = db.relationship(
        "PIPActionItem",
        back_populates="pip_record",
        cascade="all, delete-orphan",
        lazy=True,
    )
    timeline_events = db.relationship(
        "TimelineEvent",
        back_populates="pip_record",
        cascade="all, delete-orphan",
        lazy=True,
    )


class PIPActionItem(db.Model):
    __tablename__ = "pip_action_item"

    id = db.Column(db.Integer, primary_key=True)
    pip_record_id = db.Column(
        db.Integer, db.ForeignKey("pip_record.id"), nullable=False
    )
    description = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default="Outstanding")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    pip_record = db.relationship("PIPRecord", back_populates="action_items")


class TimelineEvent(db.Model):
    __tablename__ = "timeline_event"

    id = db.Column(db.Integer, primary_key=True)
    pip_record_id = db.Column(
        db.Integer, db.ForeignKey("pip_record.id"), nullable=True
    )
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    event_type = db.Column(db.String(100))
    notes = db.Column(db.Text)
    updated_by = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    pip_record = db.relationship("PIPRecord", back_populates="timeline_events")


class ProbationRecord(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(
        db.Integer, db.ForeignKey("employee.id"), nullable=False
    )
    start_date = db.Column(db.Date, nullable=False)
    expected_end_date = db.Column(db.Date, nullable=False)
    status = db.Column(
        db.String(50), default="Active"
    )  # Active, Extended, Completed, Failed
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_updated = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    reviews = db.relationship(
        "ProbationReview",
        backref="probation",
        lazy=True,
        cascade="all, delete-orphan",
    )
    plans = db.relationship(
        "ProbationPlan",
        backref="probation",
        lazy=True,
        cascade="all, delete-orphan",
    )

    employee = db.relationship(
        "Employee", backref=db.backref("probation_records", lazy=True)
    )


class ProbationReview(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    probation_id = db.Column(
        db.Integer, db.ForeignKey("probation_record.id"), nullable=False
    )
    review_date = db.Column(db.Date, nullable=False)
    reviewer = db.Column(db.String(100))
    summary = db.Column(db.Text)
    concerns_flag = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class ProbationPlan(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    probation_id = db.Column(
        db.Integer, db.ForeignKey("probation_record.id"), nullable=False
    )
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    objectives = db.Column(db.Text)
    deadline = db.Column(db.Date)
    outcome = db.Column(db.String(100))


class DraftPIP(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    step = db.Column(db.Integer)
    data = db.Column(db.JSON)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    is_dismissed = db.Column(db.Boolean, default=False)

    user = db.relationship("User", backref="draft_pips")


class DraftProbation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("user.id"), nullable=False, index=True
    )
    employee_id = db.Column(db.Integer, nullable=True)
    step = db.Column(db.Integer, default=1)
    name = db.Column(db.String(120), default="Untitled Probation Draft")
    payload = db.Column(db.JSON, default={})
    is_dismissed = db.Column(db.Boolean, default=False)
    created_at = db.Column(
        db.DateTime(timezone=True), server_default=func.now()
    )
    updated_at = db.Column(
        db.DateTime(timezone=True),
        onupdate=func.now(),
        server_default=func.now(),
    )

    __table_args__ = (
        db.Index("ix_probation_draft_user_active", "user_id", "is_dismissed"),
    )


class ImportJob(db.Model):
    __tablename__ = "import_jobs"
    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(
        db.DateTime, nullable=False, default=datetime.utcnow
    )
    created_by = db.Column(db.String(120), nullable=False)
    source_filename = db.Column(db.String(255), nullable=False)
    total_rows = db.Column(db.Integer, nullable=False)
    imported_rows = db.Column(db.Integer, nullable=False, default=0)
    skipped_rows = db.Column(db.Integer, nullable=False, default=0)
    errors_json = db.Column(
        db.Text, nullable=True
    )

    def errors(self):
        try:
            return json.loads(self.errors_json or "[]")
        except Exception:
            return []


class DocumentFile(db.Model):
    __tablename__ = "document_files"

    id = db.Column(db.Integer, primary_key=True)
    pip_id = db.Column(
        db.Integer,
        db.ForeignKey("pip_record.id"),
        index=True,
        nullable=False,
    )

    doc_type = db.Column(db.String(32), nullable=False)
    version = db.Column(db.Integer, nullable=False, default=1)
    status = db.Column(db.String(16), nullable=False, default="draft")
    docx_path = db.Column(db.String(255), nullable=False)
    pdf_path = db.Column(db.String(255))
    html_snapshot = db.Column(db.Text)
    notes = db.Column(db.String(255))
    created_at = db.Column(
        db.DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )
    created_by = db.Column(db.String(120))

    pip = db.relationship(
        "PIPRecord", backref=db.backref("documents", lazy="dynamic")
    )

    __table_args__ = (
        db.UniqueConstraint(
            "pip_id", "doc_type", "version", name="uq_pip_doctype_version"
        ),
    )


class SicknessCase(db.Model):
    __tablename__ = "sickness_cases"

    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(
        db.Integer, db.ForeignKey("employee.id"), nullable=False, index=True
    )

    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=True)

    reason = db.Column(db.String(255), nullable=True)
    trigger_type = db.Column(
        db.String(50), nullable=True
    )
    notes = db.Column(db.Text, nullable=True)

    status = db.Column(
        db.String(32), nullable=False, default="Open"
    )

    created_at = db.Column(
        db.DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    employee = db.relationship(
        "Employee", backref=db.backref("sickness_cases", lazy=True)
    )
    meetings = db.relationship(
        "SicknessMeeting",
        back_populates="case",
        cascade="all, delete-orphan",
        lazy=True,
    )

    def __repr__(self):
        return f"<SicknessCase {self.id} emp={self.employee_id} status={self.status}>"


class SicknessMeeting(db.Model):
    __tablename__ = "sickness_meetings"

    id = db.Column(db.Integer, primary_key=True)
    sickness_case_id = db.Column(
        db.Integer,
        db.ForeignKey("sickness_cases.id"),
        nullable=False,
        index=True,
    )

    meeting_date = db.Column(db.Date, nullable=False)
    meeting_type = db.Column(
        db.String(50), nullable=False
    )
    chair = db.Column(db.String(100), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    outcome = db.Column(db.Text, nullable=True)

    created_at = db.Column(
        db.DateTime, default=datetime.utcnow, nullable=False
    )

    case = db.relationship(
        "SicknessCase", back_populates="meetings"
    )

    def __repr__(self):
        return f"<SicknessMeeting {self.id} case={self.sickness_case_id} type={self.meeting_type}>"


class EmployeeRelationsCase(db.Model):
    __tablename__ = "employee_relations_cases"

    id = db.Column(db.Integer, primary_key=True)

    employee_id = db.Column(
        db.Integer, db.ForeignKey("employee.id"), nullable=False, index=True
    )

    case_type = db.Column(db.String(50), nullable=False, index=True)
    title = db.Column(db.String(255), nullable=False)
    summary = db.Column(db.Text, nullable=True)
    allegation_or_grievance = db.Column(db.Text, nullable=False)

    date_raised = db.Column(db.Date, nullable=False)
    raised_by = db.Column(db.String(120), nullable=True)

    status = db.Column(db.String(50), nullable=False, default="Draft", index=True)
    stage = db.Column(db.String(100), nullable=False, default="Allegation Logged")
    priority_level = db.Column(db.String(50), nullable=True)

    service_area = db.Column(db.String(120), nullable=True)
    department = db.Column(db.String(120), nullable=True)
    policy_type = db.Column(db.String(50), nullable=True)

    next_action_date = db.Column(db.Date, nullable=True)
    investigation_deadline = db.Column(db.Date, nullable=True)
    hearing_date = db.Column(db.Date, nullable=True)
    outcome_due_date = db.Column(db.Date, nullable=True)
    appeal_deadline = db.Column(db.Date, nullable=True)
    date_closed = db.Column(db.Date, nullable=True)

    outcome_status = db.Column(db.String(100), nullable=True)
    confidential_notes = db.Column(db.Text, nullable=True)

    hr_lead = db.Column(db.String(120), nullable=True)
    investigating_manager = db.Column(db.String(120), nullable=True)
    hearing_chair = db.Column(db.String(120), nullable=True)
    note_taker = db.Column(db.String(120), nullable=True)
    appeal_manager = db.Column(db.String(120), nullable=True)

    disciplinary_category = db.Column(db.String(120), nullable=True)
    gross_misconduct_flag = db.Column(db.Boolean, default=False)
    misconduct_date = db.Column(db.Date, nullable=True)
    suspension_flag = db.Column(db.Boolean, default=False)
    suspension_with_pay = db.Column(db.Boolean, default=True)
    previous_warnings_summary = db.Column(db.Text, nullable=True)
    recommended_sanction = db.Column(db.String(120), nullable=True)
    final_sanction = db.Column(db.String(120), nullable=True)
    warning_level = db.Column(db.String(120), nullable=True)
    warning_review_date = db.Column(db.Date, nullable=True)
    warning_expiry_date = db.Column(db.Date, nullable=True)

    grievance_category = db.Column(db.String(120), nullable=True)
    person_complained_about = db.Column(db.String(120), nullable=True)
    bullying_flag = db.Column(db.Boolean, default=False)
    harassment_flag = db.Column(db.Boolean, default=False)
    discrimination_flag = db.Column(db.Boolean, default=False)
    requested_resolution = db.Column(db.Text, nullable=True)
    mediation_considered = db.Column(db.Boolean, default=False)
    grievance_outcome = db.Column(db.String(120), nullable=True)

    investigation_scope = db.Column(db.Text, nullable=True)
    investigation_findings = db.Column(db.Text, nullable=True)
    recommended_next_step = db.Column(db.Text, nullable=True)

    appeal_requested_flag = db.Column(db.Boolean, default=False)
    appeal_request_date = db.Column(db.Date, nullable=True)
    appeal_reason = db.Column(db.Text, nullable=True)
    appeal_hearing_date = db.Column(db.Date, nullable=True)
    appeal_outcome = db.Column(db.String(120), nullable=True)
    appeal_outcome_date = db.Column(db.Date, nullable=True)

    created_by = db.Column(db.String(120), nullable=True)
    updated_by = db.Column(db.String(120), nullable=True)

    created_at = db.Column(
        db.DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    employee = db.relationship(
        "Employee",
        backref=db.backref("employee_relations_cases", lazy=True),
    )

    timeline_events = db.relationship(
        "EmployeeRelationsTimelineEvent",
        back_populates="case",
        cascade="all, delete-orphan",
        lazy=True,
        order_by="desc(EmployeeRelationsTimelineEvent.timestamp)",
    )

    meetings = db.relationship(
        "EmployeeRelationsMeeting",
        back_populates="case",
        cascade="all, delete-orphan",
        lazy=True,
        order_by="desc(EmployeeRelationsMeeting.meeting_datetime)",
    )

    attachments = db.relationship(
        "EmployeeRelationsAttachment",
        back_populates="case",
        cascade="all, delete-orphan",
        lazy=True,
        order_by="desc(EmployeeRelationsAttachment.uploaded_at)",
    )

    documents = db.relationship(
        "EmployeeRelationsDocument",
        back_populates="case",
        cascade="all, delete-orphan",
        lazy=True,
        order_by="desc(EmployeeRelationsDocument.updated_at)",
    )

    policy_texts = db.relationship(
        "EmployeeRelationsPolicyText",
        back_populates="case",
        cascade="all, delete-orphan",
        lazy=True,
        order_by="desc(EmployeeRelationsPolicyText.updated_at)",
    )

    ai_advice_records = db.relationship(
        "EmployeeRelationsAIAdvice",
        back_populates="case",
        cascade="all, delete-orphan",
        lazy=True,
        order_by="desc(EmployeeRelationsAIAdvice.created_at)",
    )

    def __repr__(self):
        return f"<EmployeeRelationsCase {self.id} type={self.case_type} status={self.status}>"


class EmployeeRelationsTimelineEvent(db.Model):
    __tablename__ = "employee_relations_timeline_events"

    id = db.Column(db.Integer, primary_key=True)

    case_id = db.Column(
        db.Integer,
        db.ForeignKey("employee_relations_cases.id"),
        nullable=False,
        index=True,
    )

    timestamp = db.Column(
        db.DateTime, default=datetime.utcnow, nullable=False, index=True
    )
    event_type = db.Column(db.String(100), nullable=False)
    notes = db.Column(db.Text, nullable=True)
    updated_by = db.Column(db.String(120), nullable=True)
    created_at = db.Column(
        db.DateTime, default=datetime.utcnow, nullable=False
    )

    case = db.relationship(
        "EmployeeRelationsCase",
        back_populates="timeline_events",
    )

    def __repr__(self):
        return f"<EmployeeRelationsTimelineEvent {self.id} case={self.case_id} type={self.event_type}>"


class EmployeeRelationsMeeting(db.Model):
    __tablename__ = "employee_relations_meetings"

    id = db.Column(db.Integer, primary_key=True)

    case_id = db.Column(
        db.Integer,
        db.ForeignKey("employee_relations_cases.id"),
        nullable=False,
        index=True,
    )

    meeting_type = db.Column(db.String(100), nullable=False)
    meeting_datetime = db.Column(db.DateTime, nullable=False, index=True)
    location = db.Column(db.String(255), nullable=True)
    attendees = db.Column(db.Text, nullable=True)
    notes = db.Column(db.Text, nullable=True)
    adjournment_notes = db.Column(db.Text, nullable=True)
    outcome_summary = db.Column(db.Text, nullable=True)

    created_by = db.Column(db.String(120), nullable=True)
    created_at = db.Column(
        db.DateTime, default=datetime.utcnow, nullable=False
    )

    case = db.relationship(
        "EmployeeRelationsCase",
        back_populates="meetings",
    )

    def __repr__(self):
        return f"<EmployeeRelationsMeeting {self.id} case={self.case_id} type={self.meeting_type}>"


class EmployeeRelationsAttachment(db.Model):
    __tablename__ = "employee_relations_attachments"

    id = db.Column(db.Integer, primary_key=True)

    case_id = db.Column(
        db.Integer,
        db.ForeignKey("employee_relations_cases.id"),
        nullable=False,
        index=True,
    )

    original_filename = db.Column(db.String(255), nullable=False)
    stored_filename = db.Column(db.String(255), nullable=False)
    stored_path = db.Column(db.String(500), nullable=False)
    document_category = db.Column(db.String(100), nullable=False, default="Other")
    notes = db.Column(db.Text, nullable=True)

    uploaded_by = db.Column(db.String(120), nullable=True)
    uploaded_at = db.Column(
        db.DateTime, default=datetime.utcnow, nullable=False, index=True
    )

    case = db.relationship(
        "EmployeeRelationsCase",
        back_populates="attachments",
    )

    def __repr__(self):
        return f"<EmployeeRelationsAttachment {self.id} case={self.case_id} file={self.original_filename}>"


class EmployeeRelationsPolicyText(db.Model):
    __tablename__ = "employee_relations_policy_texts"

    id = db.Column(db.Integer, primary_key=True)

    case_id = db.Column(
        db.Integer,
        db.ForeignKey("employee_relations_cases.id"),
        nullable=False,
        index=True,
    )

    title = db.Column(db.String(255), nullable=False)
    source_filename = db.Column(db.String(255), nullable=True)

    source_attachment_id = db.Column(
        db.Integer,
        db.ForeignKey("employee_relations_attachments.id"),
        nullable=True,
        index=True,
    )

    raw_text = db.Column(db.Text, nullable=True)
    cleaned_text = db.Column(db.Text, nullable=True)

    is_active = db.Column(db.Boolean, nullable=False, default=True)

    created_by = db.Column(db.String(120), nullable=True)
    updated_by = db.Column(db.String(120), nullable=True)

    created_at = db.Column(
        db.DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    case = db.relationship(
        "EmployeeRelationsCase",
        back_populates="policy_texts",
    )

    source_attachment = db.relationship(
        "EmployeeRelationsAttachment",
        foreign_keys=[source_attachment_id],
    )

    ai_advice_records = db.relationship(
        "EmployeeRelationsAIAdvice",
        back_populates="policy_text",
        lazy=True,
    )

    def __repr__(self):
        return f"<EmployeeRelationsPolicyText {self.id} case={self.case_id} title={self.title}>"


class EmployeeRelationsAIAdvice(db.Model):
    __tablename__ = "employee_relations_ai_advice"

    id = db.Column(db.Integer, primary_key=True)

    case_id = db.Column(
        db.Integer,
        db.ForeignKey("employee_relations_cases.id"),
        nullable=False,
        index=True,
    )

    policy_text_id = db.Column(
        db.Integer,
        db.ForeignKey("employee_relations_policy_texts.id"),
        nullable=True,
        index=True,
    )

    overall_risk_view = db.Column(db.Text, nullable=True)
    immediate_next_steps = db.Column(db.Text, nullable=True)
    investigation_questions = db.Column(db.Text, nullable=True)
    hearing_questions = db.Column(db.Text, nullable=True)
    outcome_sanction_guidance = db.Column(db.Text, nullable=True)
    fairness_process_checks = db.Column(db.Text, nullable=True)
    suggested_wording = db.Column(db.Text, nullable=True)
    missing_information = db.Column(db.Text, nullable=True)

    raw_response = db.Column(db.Text, nullable=True)
    model_name = db.Column(db.String(120), nullable=True)

    created_by = db.Column(db.String(120), nullable=True)
    created_at = db.Column(
        db.DateTime, default=datetime.utcnow, nullable=False, index=True
    )

    case = db.relationship(
        "EmployeeRelationsCase",
        back_populates="ai_advice_records",
    )

    policy_text = db.relationship(
        "EmployeeRelationsPolicyText",
        back_populates="ai_advice_records",
    )

    def __repr__(self):
        return f"<EmployeeRelationsAIAdvice {self.id} case={self.case_id} model={self.model_name}>"


class EmployeeRelationsDocument(db.Model):
    __tablename__ = "employee_relations_documents"

    id = db.Column(db.Integer, primary_key=True)

    case_id = db.Column(
        db.Integer,
        db.ForeignKey("employee_relations_cases.id"),
        nullable=False,
        index=True,
    )

    document_type = db.Column(db.String(100), nullable=False, index=True)
    title = db.Column(db.String(255), nullable=False)

    status = db.Column(db.String(50), nullable=False, default="Draft", index=True)
    version = db.Column(db.Integer, nullable=False, default=1)
    draft_origin = db.Column(
        db.String(50),
        nullable=False,
        default="plain",
        index=True,
    )

    html_content = db.Column(db.Text, nullable=True)
    finalised_at = db.Column(db.DateTime, nullable=True)

    file_path = db.Column(db.String(500), nullable=True)
    file_name = db.Column(db.String(255), nullable=True)

    created_by = db.Column(db.String(120), nullable=True)
    updated_by = db.Column(db.String(120), nullable=True)
    created_at = db.Column(
        db.DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    case = db.relationship(
        "EmployeeRelationsCase",
        back_populates="documents",
    )

    def __repr__(self):
        return (
            f"<EmployeeRelationsDocument {self.id} "
            f"case={self.case_id} type={self.document_type} "
            f"status={self.status} origin={self.draft_origin}>"
        )


class AIConsentLog(db.Model):
    __tablename__ = "ai_consent_logs"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    context = db.Column(db.String(100), nullable=False)
    accepted = db.Column(db.Boolean, default=False, nullable=False)
    accepted_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    request_ip = db.Column(db.String(100), nullable=True)
    user_agent = db.Column(db.String(500), nullable=True)

    user = db.relationship("User", backref=db.backref("ai_consents", lazy=True))

    def __repr__(self):
        return f"<AIConsentLog user_id={self.user_id} context={self.context} accepted={self.accepted}>"


class APIKey(db.Model):
    __tablename__ = "api_keys"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    key_prefix = db.Column(db.String(20), nullable=False, index=True)
    key_hash = db.Column(db.String(64), nullable=False, unique=True, index=True)

    organisation_id = db.Column(
        db.Integer,
        db.ForeignKey("organisations.id"),
        nullable=True,
        index=True,
    )
    created_by_user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

    is_active = db.Column(db.Boolean, default=True, nullable=False)
    scopes = db.Column(db.Text, nullable=True)
    last_used_at = db.Column(db.DateTime, nullable=True)
    expires_at = db.Column(db.DateTime, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    revoked_at = db.Column(db.DateTime, nullable=True)

    created_by = db.relationship("User", backref=db.backref("created_api_keys", lazy=True))
    organisation = db.relationship(
        "Organisation",
        backref=db.backref("api_keys", lazy=True),
    )

    def has_scope(self, scope: str) -> bool:
        if not self.scopes:
            return False
        allowed = {s.strip() for s in self.scopes.split(",") if s.strip()}
        return scope in allowed

    def revoke(self):
        self.is_active = False
        self.revoked_at = datetime.utcnow()

    def __repr__(self):
        return f"<APIKey id={self.id} name={self.name} active={self.is_active}>"


class Organisation(db.Model):
    __tablename__ = "organisations"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False, default="Default Organisation")
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<Organisation {self.name}>"


class OrganisationModuleSetting(db.Model):
    __tablename__ = "organisation_module_settings"

    id = db.Column(db.Integer, primary_key=True)

    organisation_id = db.Column(
        db.Integer,
        db.ForeignKey("organisations.id"),
        nullable=False,
        index=True
    )

    module_key = db.Column(db.String(50), nullable=False)
    is_enabled = db.Column(db.Boolean, default=True, nullable=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )

    organisation = db.relationship(
        "Organisation",
        backref=db.backref("module_settings", lazy=True)
    )

    __table_args__ = (
        db.UniqueConstraint("organisation_id", "module_key", name="uq_org_module"),
    )

    def __repr__(self):
        return f"<OrgModule {self.module_key} enabled={self.is_enabled}>"
