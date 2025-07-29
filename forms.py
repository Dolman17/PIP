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
    HiddenField,
    BooleanField
)
from wtforms.validators import DataRequired, Optional, Email

# ---------------------- PIP Action Subform ----------------------

class PIPActionForm(FlaskForm):
    description = TextAreaField('Description', validators=[DataRequired()])
    status = SelectField(
        'Status',
        choices=[
            ('Outstanding', 'Outstanding'),
            ('In Progress', 'In Progress'),
            ('Completed', 'Completed')
        ],
        validators=[DataRequired()]
    )

# ---------------------- PIP Form ----------------------

class PIPForm(FlaskForm):
    concerns = TextAreaField('Concerns', validators=[DataRequired()])
    start_date = DateField('Start Date', validators=[DataRequired()])
    review_date = DateField('Review Date', validators=[DataRequired()])
    actions = FieldList(FormField(PIPActionForm), min_entries=1, max_entries=10)
    meeting_notes = TextAreaField('Meeting Notes')
    status = SelectField('Status', choices=[('Open', 'Open'), ('Completed', 'Completed'), ('Closed', 'Closed')])
    submit = SubmitField('Submit')
    capability_meeting_date = DateField('Capability Meeting Date', format='%Y-%m-%d', validators=[Optional()])
    capability_meeting_time = StringField('Capability Meeting Time', validators=[Optional()])
    capability_meeting_venue = StringField('Meeting Venue', validators=[Optional()])

# ---------------------- Employee Form ----------------------

class EmployeeForm(FlaskForm):
    first_name = StringField('First Name', validators=[DataRequired()])
    last_name = StringField('Last Name', validators=[DataRequired()])
    job_title = StringField('Job Title', validators=[DataRequired()])
    line_manager = StringField('Line Manager')
    service = StringField('Service', validators=[DataRequired()])
    start_date = DateField('Start Date', validators=[DataRequired()])
    team_id = IntegerField('Team ID')
    submit = SubmitField('Add Employee')
    email = StringField('Email', validators=[Optional(), Email()])  # 👈 New field

# ---------------------- Login Form ----------------------

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember = BooleanField('Remember Me')
    submit = SubmitField('Login')

# ---------------------- Probation Record Form ----------------------


class ProbationRecordForm(FlaskForm):
    start_date = DateField('Start Date', validators=[DataRequired()])
    expected_end_date = DateField('Expected End Date', validators=[DataRequired()])
    notes = TextAreaField('Notes', validators=[Optional()])
    submit = SubmitField('Create Probation Record')


class ProbationReviewForm(FlaskForm):
    review_date = DateField('Review Date', validators=[DataRequired()])
    reviewer = StringField('Reviewer', validators=[DataRequired()])
    summary = TextAreaField('Review Summary', validators=[DataRequired()])
    concerns_flag = StringField('Concerns (Yes/No)', validators=[Optional()])  # can convert to Boolean later
    submit = SubmitField('Submit Review')

class ProbationPlanForm(FlaskForm):
    objectives = TextAreaField('Objectives', validators=[DataRequired()])
    deadline = DateField('Deadline', validators=[DataRequired()])
    outcome = StringField('Outcome (e.g. Met, Not Met)', validators=[Optional()])
    submit = SubmitField('Save Plan')
