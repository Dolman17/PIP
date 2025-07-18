from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, DateField, SubmitField
from wtforms.validators import DataRequired
from wtforms.validators import DataRequired
from wtforms import IntegerField, SelectField
from wtforms.validators import DataRequired

class PIPForm(FlaskForm):
    concerns = TextAreaField('Concerns', validators=[DataRequired()])
    start_date = DateField('Start Date', validators=[DataRequired()])
    review_date = DateField('Review Date', validators=[DataRequired()])
    action_plan = TextAreaField('Action Plan')
    meeting_notes = TextAreaField('Meeting Notes')
    submit = SubmitField('Create PIP')

class EmployeeForm(FlaskForm):
    first_name = StringField('First Name', validators=[DataRequired()])
    last_name = StringField('Last Name', validators=[DataRequired()])
    job_title = StringField('Job Title', validators=[DataRequired()])
    line_manager = StringField('Line Manager')
    service = StringField('Service', validators=[DataRequired()])
    start_date = DateField('Start Date', validators=[DataRequired()])
    team_id = IntegerField('Team ID')
    submit = SubmitField('Add Employee')
