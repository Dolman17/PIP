import os
from flask import Flask, render_template, redirect, url_for, request, flash, send_file
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flask_login import (
    LoginManager, login_user, login_required,
    logout_user, current_user
)
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
from io import BytesIO
from docxtpl import DocxTemplate
from openai import OpenAI
from dotenv import load_dotenv
load_dotenv()

from models import db, User, Employee, PIPRecord, PIPActionItem, TimelineEvent
from forms import PIPForm, EmployeeForm, LoginForm
from flask_wtf.csrf import CSRFProtect


# Initialize OpenAI v1 client (will pick up OPENAI_API_KEY env var)
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

# Initialize Flask
app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key'
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'pip_crm.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
csrf = CSRFProtect(app)



db.init_app(app)
migrate = Migrate(app, db)

# Initialize Login
login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)


# ----- User Loader -----
@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

# ----- Routes -----
@app.route('/')
@login_required
def home():
    return render_template('landing.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if request.method == 'POST' and form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and check_password_hash(user.password_hash, form.password.data):
            login_user(user)
            return redirect(url_for('home'))
        flash('Invalid username or password', 'danger')
    return render_template('login.html', form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/employee/<int:employee_id>')
@login_required
def employee_detail(employee_id):
    employee = Employee.query.options(db.joinedload(Employee.pips)).get_or_404(employee_id)
    if current_user.admin_level == 0 and employee.team_id != current_user.team_id:
        flash('Access denied')
        return redirect(url_for('dashboard'))
    return render_template('employee_detail.html', employee=employee)

@app.route('/pip/<int:id>')
@login_required
def pip_detail(id):
    pip = PIPRecord.query.get_or_404(id)
    employee = pip.employee
    return render_template('pip_detail.html', pip=pip, employee=employee)

@app.route('/pip/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_pip(id):
    pip      = PIPRecord.query.get_or_404(id)
    employee = pip.employee

    # Bind GET or POST into the form
    if request.method == 'POST':
        form = PIPForm()
        form.process(request.form)
    else:
        form = PIPForm(obj=pip)
        # Pre‐populate action items on GET
        for _ in range(len(pip.action_items) - len(form.actions.entries)):
            form.actions.append_entry()
        for idx, ai in enumerate(pip.action_items):
            form.actions.entries[idx].form.description.data = ai.description
            form.actions.entries[idx].form.status.data      = ai.status

    advice_text = None

    # 1) AI Advice branch
    if request.method == 'POST' and 'generate_advice' in request.form:
        # Build prompt
        prompt = (
            f"You are a performance coach.\n"
            f"Employee: {employee.first_name} {employee.last_name}\n"
            f"Job Title: {employee.job_title}\n"
            f"Concerns: {form.concerns.data or '[none]'}\n"
            "Action Items:\n"
        )
        for ai_field in form.actions.entries:
            desc = ai_field.form.description.data or '[no description]'
            stat = ai_field.form.status.data      or '[no status]'
            prompt += f"- {desc} [{stat}]\n"
        prompt += f"Meeting Notes: {form.meeting_notes.data or '[none]'}\n"
        prompt += "Provide 3 bulleted actionable tips for the manager to support this employee."

        # Call the new API
        resp = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role":"user","content":prompt}],
            temperature=0.7,
        )
        # In v1, the choices list still lives under resp.choices
        advice_text = resp.choices[0].message.content.strip()

        return render_template(
            'edit_pip.html',
            form=form,
            pip=pip,
            employee=employee,
            advice_text=advice_text
        )

    # 2) Save branch
    if form.validate_on_submit():
        pip.concerns      = form.concerns.data
        pip.start_date    = form.start_date.data
        pip.review_date   = form.review_date.data
        pip.status        = form.status.data
        pip.meeting_notes = form.meeting_notes.data
        pip.capability_meeting_date  = form.capability_meeting_date.data
        pip.capability_meeting_time  = form.capability_meeting_time.data
        pip.capability_meeting_venue = form.capability_meeting_venue.data


        pip.action_items.clear()
        for ai_field in form.actions.entries:
            pip.action_items.append(
                PIPActionItem(
                    description=ai_field.form.description.data,
                    status     =ai_field.form.status.data
                )
            )

        db.session.commit()
        flash('PIP updated successfully.', 'success')
        return redirect(url_for('pip_detail', id=pip.id))

    # 3) Final render
    return render_template(
        'edit_pip.html',
        form=form,
        pip=pip,
        employee=employee,
        advice_text=advice_text
    )

@app.route('/pip/<int:id>/generate/advice', methods=['POST'])
@login_required
def generate_ai_advice(id):
    pip = PIPRecord.query.get_or_404(id)
    employee = pip.employee

    prompt = (
        "You are an experienced HR Line Manager based in the UK. "
        "Using the information below, provide three clear and practical suggestions for how a line manager "
        "can support the employee's performance improvement. Your advice should reflect HR best practice in the UK.\n\n"
        f"Employee Name: {employee.first_name} {employee.last_name}\n"
        f"Job Title: {employee.job_title}\n"
        f"Concerns: {pip.concerns or '[none]'}\n"
        "Action Items:\n"
    )
    for item in pip.action_items:
        prompt += f"- {item.description or '[no description]'} [{item.status or '[no status]'}]\n"

    prompt += f"Meeting Notes: {pip.meeting_notes or '[none]'}\n\n"
    prompt += "Provide your advice as a bullet-pointed list."

    resp = client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
    )
    pip.ai_advice = resp.choices[0].message.content.strip()
    pip.ai_advice_generated_at = datetime.utcnow()

    # Log timeline event
    event = TimelineEvent(
        pip_record_id=pip.id,
        event_type="AI Advice Generated",
        notes="Advice generated using OpenAI",
        updated_by=current_user.username
    )
    db.session.add(event)

    db.session.commit()
    flash('AI advice generated.', 'success')
    return redirect(url_for('pip_detail', id=pip.id))


@app.route('/pip/create/<int:employee_id>', methods=['GET', 'POST'])
@login_required
def create_pip(employee_id):
    employee = Employee.query.get_or_404(employee_id)
    if current_user.admin_level == 0 and employee.team_id != current_user.team_id:
        flash('Access denied.')
        return redirect(url_for('dashboard'))
    form = PIPForm()
    if request.method == 'POST':
        action_fields = [k for k in request.form if 'actions-' in k and '-description' in k]
        form.actions.min_entries = len(set(k.split('-')[1] for k in action_fields))
    if form.validate_on_submit():
        pip = PIPRecord(
            employee_id   = employee.id,
            concerns      = form.concerns.data,
            start_date    = form.start_date.data,
            review_date   = form.review_date.data,
            meeting_notes = form.meeting_notes.data
        )
        db.session.add(pip)
        db.session.flush()
        for action_form in form.actions.entries:
            item = PIPActionItem(
                pip_record_id = pip.id,
                description   = action_form.form.description.data,
                status        = action_form.form.status.data
            )
            db.session.add(item)
        db.session.commit()
        flash('New PIP created.')
        return redirect(url_for('employee_detail', employee_id=employee.id))
    return render_template('create_pip.html', form=form, employee=employee)

@app.route('/employee/<int:employee_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_employee(employee_id):
    employee = Employee.query.get_or_404(employee_id)
    form = EmployeeForm(obj=employee)

    if form.validate_on_submit():
        form.populate_obj(employee)
        db.session.commit()
        flash('Employee updated successfully!', 'success')
        return redirect(url_for('employee_detail', employee_id=employee.id))

    return render_template('edit_employee.html', form=form, employee=employee)




@app.route('/pip/list')
@login_required
def pip_list():
    pips = PIPRecord.query.join(Employee).all()
    return render_template('pip_list.html', pips=pips)

@app.route('/dashboard')
@login_required
def dashboard():
    total_employees = Employee.query.count()
    active_pips     = PIPRecord.query.filter_by(status='Open').count()
    completed_pips  = PIPRecord.query.filter_by(status='Completed').count()
    today           = datetime.utcnow().date()
    overdue_reviews = PIPRecord.query.filter(
        PIPRecord.review_date < today, PIPRecord.status=='Open'
    ).count()
    recent_activity   = TimelineEvent.query.order_by(TimelineEvent.timestamp.desc()).limit(10).all()
    upcoming_deadline = today + timedelta(days=7)
    if current_user.admin_level == 0:
        upcoming_pips = PIPRecord.query.join(Employee).filter(
            Employee.team_id==current_user.team_id,
            PIPRecord.status=='Open',
            PIPRecord.review_date>=today,
            PIPRecord.review_date<=upcoming_deadline
        ).order_by(PIPRecord.review_date).all()
    else:
        upcoming_pips = PIPRecord.query.filter(
            PIPRecord.status=='Open',
            PIPRecord.review_date>=today,
            PIPRecord.review_date<=upcoming_deadline
        ).order_by(PIPRecord.review_date).all()
    return render_template(
        'dashboard.html', total_employees=total_employees,
        active_pips=active_pips, completed_pips=completed_pips,
        overdue_reviews=overdue_reviews, recent_activity=recent_activity,
        upcoming_pips=upcoming_pips
    )

@app.route('/employee/add', methods=['GET', 'POST'])
@login_required
def add_employee():
    if current_user.admin_level < 1:
        flash('Access denied.')
        return redirect(url_for('home'))
    form = EmployeeForm()
    if form.validate_on_submit():
        emp = Employee(
            first_name  = form.first_name.data,
            last_name   = form.last_name.data,
            job_title   = form.job_title.data,
            line_manager= form.line_manager.data,
            service     = form.service.data,
            start_date  = form.start_date.data,
            team_id     = form.team_id.data,
            email       = form.email.data
        )
        db.session.add(emp)
        db.session.commit()
        flash('New employee added.')
        return redirect(url_for('employee_list'))
    return render_template('add_employee.html', form=form)

@app.route('/employee/list')
@login_required
def employee_list():
    return render_template('employee_list.html', employees=Employee.query.all())

@app.route('/pip/select-employee', methods=['GET', 'POST'])
@login_required
def select_employee_for_pip():
    employees = Employee.query.order_by(Employee.last_name).all()
    if request.method == 'POST':
        return redirect(url_for('create_pip', employee_id=request.form.get('employee_id')))
    return render_template('pip_select_employee.html', employees=employees)

# Document Generation
@app.route('/pip/<int:id>/generate/invite')
@login_required
def generate_invite_letter(id):
    pip = PIPRecord.query.get_or_404(id)
    tpl = DocxTemplate('templates/docx/invite_letter_template.docx')

    context = {
        'employee': pip.employee,
        'pip': pip,
        'current_user': current_user,
        'current_date': datetime.utcnow().strftime('%d %B %Y'),
        'created_by': pip.created_by or current_user.username
    }

    tpl.render(context)
    out = BytesIO()
    tpl.save(out)
    out.seek(0)

    return send_file(
        out,
        as_attachment=True,
        download_name=f"Invite_Letter_{pip.employee.last_name}_{pip.id}.docx",
        mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    )

@app.route('/pip/<int:id>/generate/plan')
@login_required
def generate_plan_document(id):
    pip = PIPRecord.query.get_or_404(id)
    tpl = DocxTemplate('templates/docx/plan_template.docx')
    tpl.render({'employee': pip.employee, 'pip': pip, 'current_user': current_user})
    out = BytesIO(); tpl.save(out); out.seek(0)
    return send_file(out, as_attachment=True,
                     download_name=f"PIP_Plan_{pip.employee.last_name}_{pip.id}.docx",
                     mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document')

@app.route('/pip/<int:id>/generate/outcome')
@login_required
def generate_outcome_letter(id):
    pip = PIPRecord.query.get_or_404(id)
    tpl = DocxTemplate('templates/docx/outcome_letter_template.docx')
    # safe date
    date_obj = pip.last_updated or pip.created_at or pip.start_date
    date_str = date_obj.strftime('%d %b %Y')
    tpl.render({'employee': pip.employee, 'pip': pip, 'current_user': current_user, 'date_str': date_str})
    out = BytesIO(); tpl.save(out); out.seek(0)
    return send_file(out, as_attachment=True,
                     download_name=f"Outcome_Letter_{pip.employee.last_name}_{pip.id}.docx",
                     mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document')

# Create DB if missing
#with app.app_context():
    if not os.path.exists('pip_crm.db'):
        db.create_all()
        print('✅ Database created')

@app.route('/ping')
def ping():
    return 'Pong!'

print('✅ Flask app initialized and ready.')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
