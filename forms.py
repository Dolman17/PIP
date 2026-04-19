from flask_wtf import FlaskForm
from wtforms import (
    StringField,
    TextAreaField,
    DateField,
    SubmitField,
    IntegerField,
    SelectField,
    FieldList,
    FormField,
    PasswordField,
    BooleanField,
)
from wtforms.validators import DataRequired, Optional, Email, Length


# ---------------------- PIP Action Subform ----------------------


class PIPActionForm(FlaskForm):
    description = TextAreaField("Description", validators=[DataRequired()])
    status = SelectField(
        "Status",
        choices=[
            ("Outstanding", "Outstanding"),
            ("In Progress", "In Progress"),
            ("Completed", "Completed"),
        ],
        validators=[DataRequired()],
    )


# ---------------------- PIP Form ----------------------


class PIPForm(FlaskForm):
    concerns = TextAreaField("Concerns", validators=[DataRequired()])
    start_date = DateField("Start Date", validators=[DataRequired()])
    review_date = DateField("Review Date", validators=[DataRequired()])
    actions = FieldList(FormField(PIPActionForm), min_entries=1, max_entries=10)
    meeting_notes = TextAreaField("Meeting Notes")
    status = SelectField(
        "Status",
        choices=[("Open", "Open"), ("Completed", "Completed"), ("Closed", "Closed")],
    )
    submit = SubmitField("Submit")
    capability_meeting_date = DateField(
        "Capability Meeting Date", format="%Y-%m-%d", validators=[Optional()]
    )
    capability_meeting_time = StringField(
        "Capability Meeting Time", validators=[Optional()]
    )
    capability_meeting_venue = StringField("Meeting Venue", validators=[Optional()])


# ---------------------- Employee Form ----------------------


class EmployeeForm(FlaskForm):
    first_name = StringField("First Name", validators=[DataRequired()])
    last_name = StringField("Last Name", validators=[DataRequired()])
    job_title = StringField("Job Title", validators=[DataRequired()])
    line_manager = StringField("Line Manager")
    service = StringField("Service", validators=[DataRequired()])
    start_date = DateField("Start Date", validators=[DataRequired()])
    team_id = IntegerField("Team ID")
    submit = SubmitField("Add Employee")
    email = StringField("Email", validators=[Optional(), Email()])


# ---------------------- Login Form ----------------------


class LoginForm(FlaskForm):
    username = StringField("Username", validators=[DataRequired()])
    password = PasswordField("Password", validators=[DataRequired()])
    remember = BooleanField("Remember Me")
    submit = SubmitField("Login")


# ---------------------- Probation Forms ----------------------


class ProbationRecordForm(FlaskForm):
    start_date = DateField("Start Date", validators=[DataRequired()])
    expected_end_date = DateField("Expected End Date", validators=[DataRequired()])
    notes = TextAreaField("Notes", validators=[Optional()])
    submit = SubmitField("Create Probation Record")


class ProbationReviewForm(FlaskForm):
    review_date = DateField("Review Date", validators=[DataRequired()])
    reviewer = StringField("Reviewer", validators=[DataRequired()])
    summary = TextAreaField("Review Summary", validators=[DataRequired()])
    concerns_flag = StringField("Concerns (Yes/No)", validators=[Optional()])
    submit = SubmitField("Submit Review")


class ProbationPlanForm(FlaskForm):
    objectives = TextAreaField("Objectives", validators=[DataRequired()])
    deadline = DateField("Deadline", validators=[DataRequired()])
    outcome = StringField("Outcome (e.g. Met, Not Met)", validators=[Optional()])
    submit = SubmitField("Save Plan")


# ---------------------- User Admin Form ----------------------


class UserForm(FlaskForm):
    username = StringField("Username", validators=[DataRequired()])
    email = StringField("Email", validators=[DataRequired(), Email()])
    admin_level = SelectField(
        "Admin Level",
        choices=[(0, "Line Manager"), (1, "Admin"), (2, "Superuser")],
        coerce=int,
        validators=[DataRequired()],
    )
    team_id = IntegerField("Team ID (optional)")
    organisation_id = SelectField(
        "Organisation",
        choices=[],
        coerce=int,
        validators=[Optional()],
    )
    submit = SubmitField("Save Changes")


# ---------------------- Organisation Admin Form ----------------------


class OrganisationForm(FlaskForm):
    name = StringField(
        "Organisation Name",
        validators=[DataRequired(), Length(max=255)],
    )
    submit = SubmitField("Save Organisation")


# ---------------------- Sickness Forms ----------------------


class SicknessCaseForm(FlaskForm):
    start_date = DateField(
        "Start date",
        validators=[DataRequired(message="Start date is required.")],
        format="%Y-%m-%d",
    )
    end_date = DateField(
        "End date (if known)",
        validators=[Optional()],
        format="%Y-%m-%d",
    )
    reason = StringField(
        "Reason (headline)",
        validators=[Optional(), Length(max=255)],
    )
    trigger_type = SelectField(
        "Trigger type (if applicable)",
        choices=[
            ("", "No specific trigger / just log"),
            ("short_term", "Short-term trigger reached"),
            ("long_term", "Long-term absence"),
            ("pattern", "Pattern concern / frequent short absences"),
            ("other", "Other"),
        ],
        validators=[Optional()],
    )
    notes = TextAreaField(
        "Context / notes",
        validators=[Optional()],
        render_kw={"rows": 4},
    )

    submit = SubmitField("Create Sickness Case")


class SicknessMeetingForm(FlaskForm):
    meeting_date = DateField(
        "Meeting date",
        validators=[DataRequired(message="Please select a meeting date.")],
        format="%Y-%m-%d",
    )

    meeting_type = SelectField(
        "Meeting type",
        choices=[
            ("RTW", "Return to Work"),
            ("WELFARE", "Welfare Meeting"),
            ("OH", "Occupational Health"),
            ("DISCIPLINARY", "Disciplinary / Capability"),
            ("OTHER", "Other"),
        ],
        validators=[DataRequired(message="Please choose a meeting type.")],
    )

    chair = StringField(
        "Chair",
        validators=[DataRequired(message="Please enter who is chairing the meeting.")],
    )

    location = StringField(
        "Location",
        validators=[Optional(), Length(max=255)],
    )

    outcome = StringField(
        "Outcome / decision (optional)",
        validators=[Optional(), Length(max=255)],
    )

    notes = TextAreaField(
        "Notes",
        validators=[Optional(), Length(max=2000)],
    )

    submit = SubmitField("Save meeting")
