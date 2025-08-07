
import os
import zipfile
import tempfile
import csv
import threading
import time
from io import BytesIO
from flask import Flask, session, render_template, redirect, url_for, request, flash, send_file, jsonify
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

from models import db, User, Employee, PIPRecord, PIPActionItem, TimelineEvent, ProbationRecord, ProbationReview, ProbationPlan, PIPDraft
from forms import PIPForm, EmployeeForm, LoginForm, ProbationRecordForm, ProbationReviewForm, ProbationPlanForm, UserForm
from flask_wtf import FlaskForm
from flask_wtf.csrf import CSRFProtect, validate_csrf, CSRFError

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

@app.context_processor
def inject_module():
    return dict(active_module=session.get('active_module'))



# Initialize Login
login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)

# ----- User Loader -----
@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

from functools import wraps
from flask import abort

def superuser_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_superuser():
            abort(403)  # Forbidden
        return f(*args, **kwargs)
    return decorated_function



# ----- Set active module in session -----
@app.before_request
def set_active_module():
    path = request.path.lower()

    if path.startswith('/pip/') or \
       path.startswith('/employee/') or \
       path in ['/dashboard', '/pip_list', '/employee/list', '/employee/add', '/pip/select-employee']:
        session['active_module'] = 'PIP'
    elif path.startswith('/probation/'):
        session['active_module'] = 'Probation'
    elif path == '/':
        session.pop('active_module', None)



# ----- Routes -----
@app.route('/')
@login_required
def home():
    return render_template('select_module.html', hide_sidebar=True)



@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if request.method == 'POST' and form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and check_password_hash(user.password_hash, form.password.data):
            login_user(user, remember=form.remember.data)
            return redirect(url_for('home'))
        flash('Invalid username or password', 'danger')
    return render_template('login.html', form=form, hide_sidebar=True, current_year=datetime.now().year)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))


@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    if not current_user.is_superuser():
        flash('You do not have permission to access the admin dashboard.', 'danger')
        return redirect(url_for('home'))
    return render_template('admin_dashboard.html')


import threading
import time

from io import BytesIO
import zipfile
import csv
from flask import send_file


@app.route('/admin/export')
@login_required
@superuser_required
def export_data():
    # In-memory buffer for the ZIP file
    zip_buffer = BytesIO()

    with tempfile.TemporaryDirectory() as tmpdir:
        # Helper to write a list of dicts to CSV
        def write_csv(filename, fieldnames, rows):
            filepath = os.path.join(tmpdir, filename)
            with open(filepath, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(rows)
            export_zip.write(filepath, arcname=filename)

        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as export_zip:

            # Export Employees
            employees = Employee.query.all()
            write_csv('employees.csv', ['id', 'name', 'job_title', 'line_manager', 'service', 'start_date'], [
                {
                    'id': e.id,
                    'name': f'{getattr(e, "first_name", "")} {getattr(e, "last_name", "")}',
                    'job_title': e.job_title,
                    'line_manager': e.line_manager,
                    'service': e.service,
                    'start_date': e.start_date.strftime('%Y-%m-%d') if e.start_date else ''
                } for e in employees
            ])

            # Export PIPs
            pips = PIPRecord.query.all()
            write_csv('pip_records.csv', ['id', 'employee_id', 'concerns', 'start_date', 'review_date', 'status'], [
                {
                    'id': p.id,
                    'employee_id': p.employee_id,
                    'concerns': p.concerns,
                    'start_date': p.start_date.strftime('%Y-%m-%d') if p.start_date else '',
                    'review_date': p.review_date.strftime('%Y-%m-%d') if p.review_date else '',
                    'status': p.status
                } for p in pips
            ])

            # Export Timeline Events
            events = TimelineEvent.query.all()
            write_csv('timeline_events.csv', ['id', 'employee_id', 'description', 'timestamp'], [
                {
                    'id': t.id,
                    'employee_id': t.pip_record.employee_id if t.pip_record else '',
                    'description': f"{t.event_type or ''}: {t.notes or ''}",
                    'timestamp': t.timestamp.strftime('%Y-%m-%d %H:%M:%S')
                } for t in events
        ])


            # Export Users
            users = User.query.all()
            write_csv('users.csv', ['id', 'email', 'admin_level'], [
                {
                    'id': u.id,
                    'email': u.email,
                    'admin_level': u.admin_level
                } for u in users
            ])

            # Export Probation Records
            probations = ProbationRecord.query.all()
            write_csv('probation_records.csv', ['id', 'employee_id', 'status', 'start_date', 'end_date'], [
                {
                    'id': p.id,
                    'employee_id': p.employee_id,
                    'status': p.status,
                    'start_date': p.start_date.strftime('%Y-%m-%d') if p.start_date else '',
                    'end_date': p.expected_end_date.strftime('%Y-%m-%d') if p.expected_end_date else ''
                } for p in probations
            ])

            # Export Probation Reviews
            reviews = ProbationReview.query.all()
            write_csv('probation_reviews.csv', ['id', 'probation_id', 'review_date', 'notes'], [
                {
                    'id': r.id,
                    'probation_id': r.probation_id,
                    'review_date': r.review_date.strftime('%Y-%m-%d') if r.review_date else '',
                    'notes': r.notes
                } for r in reviews
            ])

            # Export Probation Plans
            plans = ProbationPlan.query.all()
            write_csv('probation_plans.csv', ['id', 'probation_id', 'objective', 'support', 'deadline'], [
                {
                    'id': p.id,
                    'probation_id': p.probation_id,
                    'objective': p.objective,
                    'support': p.support,
                    'deadline': p.deadline.strftime('%Y-%m-%d') if p.deadline else ''
                } for p in plans
            ])

    # Finalize ZIP buffer and return file
    zip_buffer.seek(0)
    timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M')
    return send_file(zip_buffer, mimetype='application/zip', as_attachment=True, download_name=f'export_{timestamp}.zip')




# ----- User Management -----


@app.route('/admin/users/edit/<int:user_id>', methods=['GET', 'POST'])
@login_required
def edit_user(user_id):
    if not current_user.is_superuser():
        flash('Access denied.', 'danger')
        return redirect(url_for('dashboard'))

    user = User.query.get_or_404(user_id)
    form = UserForm(obj=user)

    if form.validate_on_submit():
        user.username = form.username.data
        user.email = form.email.data
        user.admin_level = form.admin_level.data
        user.team_id = form.team_id.data
        db.session.commit()
        flash('User updated successfully.', 'success')
        return redirect(url_for('manage_users'))

    return render_template('edit_user.html', form=form, user=user)


@app.route('/admin/users/create', methods=['GET', 'POST'])
@login_required
def create_user():
    if not current_user.is_superuser():
        flash("Access denied: Superuser only.", "danger")
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        admin_level = int(request.form.get('admin_level', 0))
        team_id = request.form.get('team_id') or None

        # Basic checks
        if not username or not email or not password:
            flash("All fields except team ID are required.", "danger")
            return redirect(request.url)

        if User.query.filter_by(username=username).first():
            flash("Username already exists.", "danger")
            return redirect(request.url)

        if User.query.filter_by(email=email).first():
            flash("Email already in use.", "danger")
            return redirect(request.url)

        hashed_pw = generate_password_hash(password)
        new_user = User(username=username, email=email, password_hash=hashed_pw, admin_level=admin_level, team_id=team_id)
        db.session.add(new_user)
        db.session.commit()
        flash("User created successfully.", "success")
        return redirect(url_for('manage_users'))

    return render_template('admin_create_user.html')

@app.route('/admin/users/delete/<int:user_id>', methods=['POST'])
@login_required
def delete_user(user_id):
    if not current_user.is_superuser():
        flash("Access denied: Superuser only.", "danger")
        return redirect(url_for('dashboard'))

    user = User.query.get_or_404(user_id)

    if user.id == current_user.id:
        flash("You cannot delete your own account while logged in.", "warning")
        return redirect(url_for('manage_users'))

    db.session.delete(user)
    db.session.commit()
    flash("User deleted successfully.", "success")
    return redirect(url_for('manage_users'))









#Employee and PIP management


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


#@app.route('/pip/create/<int:employee_id>', methods=['GET', 'POST'])
@login_required
def create_pip(employee_id):
    employee = Employee.query.get_or_404(employee_id)
    if current_user.admin_level == 0 and employee.team_id != current_user.team_id:
        flash('Access denied.')
        return redirect(url_for('dashboard'))

    form = PIPForm()

    # ✅ Append empty action entry on GET to prevent Jinja error
    if request.method == 'GET' and len(form.actions.entries) == 0:
        form.actions.append_entry()

    # ✅ Recalculate min_entries for dynamic action field JS handling
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

@app.route('/employee/edit/<int:employee_id>', methods=['GET', 'POST'])
@login_required
def edit_employee(employee_id):
    employee = Employee.query.get_or_404(employee_id)
    
    if current_user.admin_level == 0 and employee.team_id != current_user.team_id:
        flash('Access denied.')
        return redirect(url_for('dashboard'))

    form = EmployeeForm(obj=employee)

    if form.validate_on_submit():
        employee.first_name   = form.first_name.data
        employee.last_name    = form.last_name.data
        employee.job_title    = form.job_title.data
        employee.line_manager = form.line_manager.data
        employee.service      = form.service.data
        employee.start_date   = form.start_date.data
        employee.team_id      = form.team_id.data
        employee.email        = form.email.data

        db.session.commit()
        flash('Employee details updated.', 'success')
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
    active_pips = PIPRecord.query.filter_by(status='Open').count()
    completed_pips = PIPRecord.query.filter_by(status='Completed').count()

    today = datetime.utcnow().date()
    overdue_reviews = PIPRecord.query.filter(
        PIPRecord.review_date < today,
        PIPRecord.status == 'Open'
    ).count()

    recent_activity = TimelineEvent.query.order_by(TimelineEvent.timestamp.desc()).limit(10).all()
    upcoming_deadline = today + timedelta(days=7)

    if current_user.admin_level == 0:
        upcoming_pips = PIPRecord.query.join(Employee).filter(
            Employee.team_id == current_user.team_id,
            PIPRecord.status == 'Open',
            PIPRecord.review_date >= today,
            PIPRecord.review_date <= upcoming_deadline
        ).order_by(PIPRecord.review_date).all()
    else:
        upcoming_pips = PIPRecord.query.filter(
            PIPRecord.status == 'Open',
            PIPRecord.review_date >= today,
            PIPRecord.review_date <= upcoming_deadline
        ).order_by(PIPRecord.review_date).all()

    draft = PIPDraft.query.filter_by(user_id=current_user.id).first()

    return render_template(
        'dashboard.html',
        total_employees=total_employees,
        active_pips=active_pips,
        completed_pips=completed_pips,
        overdue_reviews=overdue_reviews,
        recent_activity=recent_activity,
        upcoming_pips=upcoming_pips,
        draft=draft
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
    if session.get('active_module') == 'probation':
        return render_template('probation_employee_list.html', employees=Employee.query.all())
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


from datetime import datetime, timezone

class DummyForm(FlaskForm):
    pass

from flask_wtf import FlaskForm

class DummyForm(FlaskForm):
    pass

from datetime import datetime, timezone

@app.route('/pip/create-wizard', methods=['GET', 'POST'])
@login_required
def create_pip_wizard():
    if 'wizard_step' not in session:
        session['wizard_step'] = 1
        session['pip_data'] = {}

    step = session['wizard_step']
    data = session['pip_data']
    wizard_errors = {}

    if request.method == 'POST':
        print(f"[DEBUG] POST request received at step {step}")
        print(f"[DEBUG] Form data: {request.form}")

        if step == 1:
            employee_id = request.form.get('employee_id')
            if not employee_id:
                wizard_errors['employee_id'] = "Please select an employee."
            else:
                data['employee_id'] = int(employee_id)

        elif step == 2:
            concerns = request.form.get('concerns', '').strip()
            if not concerns:
                wizard_errors['concerns'] = "Concerns cannot be empty."
            else:
                data['concerns'] = concerns

        elif step == 3:
            start_date = request.form.get('start_date')
            review_date = request.form.get('review_date')
            if not start_date:
                wizard_errors['start_date'] = "Start date is required."
            if not review_date:
                wizard_errors['review_date'] = "Review date is required."
            if not wizard_errors:
                data['start_date'] = start_date
                data['review_date'] = review_date

        elif step == 4:
            data['capability_meeting_date'] = request.form.get('capability_meeting_date')
            data['capability_meeting_time'] = request.form.get('capability_meeting_time')
            data['capability_meeting_venue'] = request.form.get('capability_meeting_venue')

        elif step == 5:
            action_items = request.form.getlist('action_plan_items[]')
            valid_items = [item.strip() for item in action_items if item.strip()]
            if not valid_items:
                wizard_errors['action_plan_items'] = "Add at least one action plan item."
            else:
                try:
                    pip = PIPRecord(
                        employee_id=int(data['employee_id']),
                        concerns=data['concerns'],
                        start_date=datetime.strptime(data['start_date'], '%Y-%m-%d').date(),
                        review_date=datetime.strptime(data['review_date'], '%Y-%m-%d').date(),
                        capability_meeting_date=datetime.strptime(data['capability_meeting_date'], '%Y-%m-%d') if data.get('capability_meeting_date') else None,
                        capability_meeting_time=data.get('capability_meeting_time'),
                        capability_meeting_venue=data.get('capability_meeting_venue'),
                        created_by=current_user.username
                    )
                    db.session.add(pip)
                    db.session.commit()

                    for item_text in valid_items:
                        action = PIPActionItem(pip_record_id=pip.id, description=item_text)
                        db.session.add(action)

                    # 🔹 Add timeline event
                    timeline = TimelineEvent(
                        pip_record_id=pip.id,
                        event_type="PIP Created",
                        notes="PIP created via multi-step wizard",
                        updated_by=current_user.username
                    )
                    db.session.add(timeline)

                    db.session.commit()
                    session.pop('wizard_step', None)
                    session.pop('pip_data', None)
                    flash("PIP created successfully!", "success")
                    return redirect(url_for('dashboard'))

                except Exception as e:
                    print(f"[ERROR] Failed to save PIP: {e}")
                    flash(f"Error creating PIP: {str(e)}", "danger")

        # Step failed validation or processing
        session['pip_data'] = data
        if not wizard_errors and step < 5:
            session['wizard_step'] = step + 1
            return redirect(url_for('create_pip_wizard'))

    # GET or failed POST – render step
    employees = Employee.query.all() if step == 1 else []
    print(f"[DEBUG] Rendering step {step} with data: {data}")
    return render_template(
        'create_pip_wizard.html',
        step=step,
        employees=employees,
        data=data or {},
        wizard_errors=wizard_errors
    )



from flask import request, jsonify
from flask_login import login_required
from flask_wtf.csrf import validate_csrf, CSRFError

from flask import request, jsonify
from flask_login import login_required
from flask_wtf.csrf import validate_csrf, CSRFError

from flask import request, jsonify
from flask_login import login_required
from flask_wtf.csrf import validate_csrf, CSRFError

@app.route("/validate-wizard-step", methods=["POST"])
@login_required
def validate_wizard_step():
    try:
        # ✅ Extract CSRF token from header
        csrf_token = request.headers.get('X-CSRFToken')
        if not csrf_token:
            return jsonify({"success": False, "errors": {"csrf_token": "CSRF token missing"}}), 400

        try:
            validate_csrf(csrf_token)
        except CSRFError as e:
            return jsonify({"success": False, "errors": {"csrf_token": str(e)}}), 400

        # ✅ Get step from form data
        step = int(request.form.get('step', 1))
        errors = {}

        # ✅ Step-specific validation
        if step == 1:
            if not request.form.get("employee_id"):
                errors["employee_id"] = "Employee is required."

        elif step == 2:
            if not request.form.get("concerns", "").strip():
                errors["concerns"] = "Please describe the concerns."

        elif step == 3:
            if not request.form.get("start_date"):
                errors["start_date"] = "Start date is required."
            if not request.form.get("review_date"):
                errors["review_date"] = "Review date is required."

        elif step == 5:
            items = request.form.getlist("action_plan_items[]")
            if not any(i.strip() for i in items):
                errors["action_plan_items"] = "Please enter at least one action item."

        return jsonify({
            "success": len(errors) == 0,
            "errors": errors
        })

    except Exception as e:
        return jsonify({
            "success": False,
            "errors": {"form": f"Server error: {str(e)}"}
        }), 500


@app.route("/pip/save-draft", methods=["POST"])
@login_required
def save_pip_draft():
    try:
        # ✅ CSRF token from header
        csrf_token = request.headers.get('X-CSRFToken')
        if not csrf_token:
            return jsonify({"success": False, "message": "CSRF token missing."}), 400

        try:
            validate_csrf(csrf_token)
        except CSRFError as e:
            return jsonify({"success": False, "message": f"CSRF validation failed: {str(e)}"}), 400

        # ✅ Parse JSON body
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "message": "No JSON data received."}), 400

        # ✅ Save or update draft
        draft = PIPDraft.query.filter_by(user_id=current_user.id).first()
        if not draft:
            draft = PIPDraft(user_id=current_user.id)

        draft.data = data
        draft.step = data.get("step", 1)
        draft.last_updated = datetime.utcnow()

        db.session.add(draft)
        db.session.commit()

        return jsonify({"success": True, "message": "Draft saved."})

    except Exception as e:
        return jsonify({"success": False, "message": f"Error: {str(e)}"}), 500


# --- View probation record ---
@app.route('/probation/<int:id>')
@login_required
def view_probation(id):
    probation = ProbationRecord.query.get_or_404(id)
    employee = probation.employee
    return render_template('view_probation.html', probation=probation, employee=employee)

# --- View Probation Review ---
@app.route('/probation/<int:id>/review/add', methods=['GET', 'POST'])
@login_required
def add_probation_review(id):
    probation = ProbationRecord.query.get_or_404(id)
    form = ProbationReviewForm()

    if form.validate_on_submit():
        review = ProbationReview(
            probation_id = probation.id,
            review_date  = form.review_date.data,
            reviewer     = form.reviewer.data,
            summary      = form.summary.data,
            concerns_flag = (form.concerns_flag.data.lower() == 'yes')
        )
        db.session.add(review)

        # Log to timeline
        event = TimelineEvent(
            pip_record_id=None,  # not a PIP
            event_type="Probation Review",
            notes=f"Review added by {current_user.username}",
            updated_by=current_user.username
        )
        db.session.add(event)

        db.session.commit()
        flash('Probation review added.', 'success')
        return redirect(url_for('view_probation', id=probation.id))

    return render_template('add_probation_review.html', form=form, probation=probation)

@app.route('/probation/<int:id>/plan/add', methods=['GET', 'POST'])
@login_required
def add_probation_plan(id):
    probation = ProbationRecord.query.get_or_404(id)
    form = ProbationPlanForm()

    if form.validate_on_submit():
        plan = ProbationPlan(
            probation_id = probation.id,
            objectives   = form.objectives.data,
            deadline     = form.deadline.data,
            outcome      = form.outcome.data
        )
        db.session.add(plan)

        # Log to timeline
        event = TimelineEvent(
            pip_record_id=None,
            event_type="Probation Plan Added",
            notes=f"Plan created by {current_user.username}",
            updated_by=current_user.username
        )
        db.session.add(event)

        db.session.commit()
        flash('Development plan added.', 'success')
        return redirect(url_for('view_probation', id=probation.id))

    return render_template('add_probation_plan.html', form=form, probation=probation)

@app.route('/probation/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit_probation(id):
    probation = ProbationRecord.query.get_or_404(id)
    form = ProbationRecordForm(obj=probation)

    if form.validate_on_submit():
        probation.start_date       = form.start_date.data
        probation.expected_end_date= form.expected_end_date.data
        probation.notes            = form.notes.data
        db.session.commit()
        flash('Probation record updated.', 'success')
        return redirect(url_for('view_probation', id=probation.id))

    return render_template('edit_probation.html', form=form, probation=probation)


@app.route('/probation/<int:id>/status/<new_status>', methods=['POST'])
@login_required
def update_probation_status(id, new_status):
    probation = ProbationRecord.query.get_or_404(id)
    valid_statuses = ['Completed', 'Extended', 'Failed']

    if new_status not in valid_statuses:
        flash('Invalid status update.', 'danger')
        return redirect(url_for('view_probation', id=id))

    probation.status = new_status
    db.session.add(probation)

    event = TimelineEvent(
        pip_record_id=None,
        event_type="Probation Status Updated",
        notes=f"Status changed to {new_status} by {current_user.username}",
        updated_by=current_user.username
    )
    db.session.add(event)

    db.session.commit()
    flash(f'Status updated to {new_status}.', 'success')
    return redirect(url_for('view_probation', id=id))

@app.route('/probation/create/<int:employee_id>', methods=['GET', 'POST'])
@login_required
def create_probation(employee_id):
    employee = Employee.query.get_or_404(employee_id)
    form = ProbationRecordForm()

    if form.validate_on_submit():
        probation = ProbationRecord(
            employee_id=employee.id,
            start_date=form.start_date.data,
            expected_end_date=form.expected_end_date.data,
            notes=form.notes.data
        )
        db.session.add(probation)
        db.session.commit()
        flash('Probation record created successfully.', 'success')
        return redirect(url_for('view_probation', id=probation.id))

    return render_template('create_probation.html', form=form, employee=employee)



@app.route('/probation/dashboard')
@login_required
def probation_dashboard():
    # This will be replaced with the real dashboard later
    records = ProbationRecord.query.all()
    return render_template('probation_dashboard.html', records=records)


@app.route('/probation/employees')
@login_required
def probation_employee_list():
    session['active_module'] = 'Probation'
    employees = Employee.query.all()
    return render_template('probation_employee_list.html', employees=employees)


@app.route('/admin/users')
@login_required
def manage_users():
    if not current_user.is_superuser():
        flash('Access denied.', 'danger')
        return redirect(url_for('dashboard'))
    users = User.query.all()
    return render_template('admin_users.html', users=users)



@app.route('/admin/backup')
@login_required
def backup_database():
    if not current_user.is_superuser():
        flash('Access denied: Superuser only.', 'danger')
        return redirect(url_for('home'))

    db_path = os.path.join(os.getcwd(), 'pip_crm.db')
    if os.path.exists(db_path):
        return send_file(db_path, as_attachment=True)
    else:
        flash('Database file not found.', 'danger')
        return redirect(url_for('admin_dashboard'))



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
