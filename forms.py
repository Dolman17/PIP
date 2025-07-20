from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, DateField, SubmitField, IntegerField, SelectField, FieldList, FormField, PasswordField
from wtforms.validators import DataRequired
from wtforms.validators import DataRequired
from wtforms import IntegerField, SelectField
from wtforms.validators import DataRequired


class PIPActionForm(FlaskForm):
    description = StringField('Description', validators=[DataRequired()])
    status = SelectField('Status', choices=[('Outstanding', 'Outstanding'), ('Completed', 'Completed')])

class PIPForm(FlaskForm):
    concerns = TextAreaField('Concerns', validators=[DataRequired()])
    start_date = DateField('Start Date', validators=[DataRequired()])
    review_date = DateField('Review Date', validators=[DataRequired()])
    actions = FieldList(FormField(PIPActionForm), min_entries=1, max_entries=10)
    meeting_notes = TextAreaField('Meeting Notes')
    submit = SubmitField('Submit')
    status = SelectField('Status', choices=[('Open', 'Open'), ('Completed', 'Completed'), ('Closed', 'Closed')])



class EmployeeForm(FlaskForm):
    first_name = StringField('First Name', validators=[DataRequired()])
    last_name = StringField('Last Name', validators=[DataRequired()])
    job_title = StringField('Job Title', validators=[DataRequired()])
    line_manager = StringField('Line Manager')
    service = StringField('Service', validators=[DataRequired()])
    start_date = DateField('Start Date', validators=[DataRequired()])
    team_id = IntegerField('Team ID')
    submit = SubmitField('Add Employee')

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')