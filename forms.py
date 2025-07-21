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
    HiddenField
)
from wtforms.validators import DataRequired

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

# ---------------------- Login Form ----------------------

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')
