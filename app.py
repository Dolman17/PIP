from flask import Flask, render_template, redirect, url_for, request, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

from models import db, User, Employee, PIPRecord, TimelineEvent
from forms import PIPForm, EmployeeForm

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///pip_crm.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)
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
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form['username']).first()
        if user and check_password_hash(user.password_hash, request.form['password']):
            login_user(user)
            return redirect(url_for('home'))
        else:
            flash('Invalid username or password')
    return render_template('login.html')


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


@app.route('/pip/edit/<int:pip_id>', methods=['GET', 'POST'])
@login_required
def edit_pip(pip_id):
    pip = PIPRecord.query.get_or_404(pip_id)
    employee = pip.employee
    form = PIPForm(obj=pip)
    original_status = pip.status

    if form.validate_on_submit():
        pip.concerns = form.concerns.data
        pip.start_date = form.start_date.data
        pip.review_date = form.review_date.data
        pip.action_plan = form.action_plan.data
        pip.meeting_notes = form.meeting_notes.data
        pip.status = request.form.get("status") or "Open"
        pip.last_updated = datetime.utcnow()
        db.session.commit()

        if pip.status != original_status:
            status_event = TimelineEvent(
                pip_id=pip.id,
                event_type="Status Change",
                notes=f"Status changed from {original_status} to {pip.status}",
                updated_by=current_user.username
            )
            db.session.add(status_event)
            db.session.commit()

        flash("PIP updated.")
        return redirect(url_for('employee_detail', employee_id=employee.id))

    return render_template('edit_pip.html', form=form, pip=pip, employee=employee)


@app.route('/pip/create/<int:employee_id>', methods=['GET', 'POST'])
@login_required
def create_pip(employee_id):
    employee = Employee.query.get_or_404(employee_id)
    if current_user.admin_level == 0 and employee.team_id != current_user.team_id:
        flash("Access denied.")
        return redirect(url_for('dashboard'))

    form = PIPForm()
    if form.validate_on_submit():
        pip = PIPRecord(
            employee_id=employee.id,
            concerns=form.concerns.data,
            start_date=form.start_date.data,
            review_date=form.review_date.data,
            action_plan=form.action_plan.data,
            meeting_notes=form.meeting_notes.data,
            created_by=current_user.username
        )
        db.session.add(pip)
        db.session.commit()
        flash("New PIP created.")
        return redirect(url_for('employee_detail', employee_id=employee.id))

    return render_template('create_pip.html', form=form, employee=employee)

@app.route("/pip/<int:pip_id>")
@login_required
def pip_detail(pip_id):
    pip = PIPRecord.query.options(db.joinedload(PIPRecord.employee)).get_or_404(pip_id)
    employee = pip.employee
    timeline = TimelineEvent.query.filter_by(pip_id=pip.id).order_by(TimelineEvent.timestamp.desc()).all()
    return render_template("pip_detail.html", pip=pip, employee=employee)


from sqlalchemy import and_, or_
from datetime import datetime, timedelta

@app.route('/dashboard')
@login_required
def dashboard():
    # Top Summary Cards
    total_employees = Employee.query.count()
    active_pips = PIPRecord.query.filter_by(status='Open').count()
    completed_pips = PIPRecord.query.filter_by(status='Completed').count()
    overdue_reviews = PIPRecord.query.filter(
        and_(PIPRecord.review_date < datetime.utcnow(), PIPRecord.status == 'Open')
    ).count()

    # Middle: Recent Timeline Activity (last 10 events)
    recent_activity = TimelineEvent.query.order_by(TimelineEvent.timestamp.desc()).limit(10).all()

    # Bottom: Upcoming Reviews (next 7 days)
    today = datetime.utcnow().date()
    upcoming_deadline = today + timedelta(days=7)

    if current_user.admin_level == 0:
        # Restrict to team members only
        upcoming_pips = PIPRecord.query.join(Employee).filter(
            and_(
                Employee.team_id == current_user.team_id,
                PIPRecord.review_date >= today,
                PIPRecord.review_date <= upcoming_deadline,
                PIPRecord.status == 'Open'
            )
        ).order_by(PIPRecord.review_date).all()
    else:
        # Show all
        upcoming_pips = PIPRecord.query.filter(
            and_(
                PIPRecord.review_date >= today,
                PIPRecord.review_date <= upcoming_deadline,
                PIPRecord.status == 'Open'
            )
        ).order_by(PIPRecord.review_date).all()

    return render_template(
        "dashboard.html",
        total_employees=total_employees,
        active_pips=active_pips,
        completed_pips=completed_pips,
        overdue_reviews=overdue_reviews,
        recent_activity=recent_activity,
        upcoming_pips=upcoming_pips
    )



@app.route('/employee/add', methods=['GET', 'POST'])
@login_required
def add_employee():
    if current_user.admin_level < 1:
        flash("Access denied.")
        return redirect(url_for('home'))

    form = EmployeeForm()
    if form.validate_on_submit():
        new_employee = Employee(
            first_name=form.first_name.data,
            last_name=form.last_name.data,
            job_title=form.job_title.data,
            line_manager=form.line_manager.data,
            service=form.service.data,
            start_date=form.start_date.data,
            team_id=form.team_id.data
        )
        db.session.add(new_employee)
        db.session.commit()
        flash("New employee added.")
        return redirect(url_for('employee_list'))

    return render_template('add_employee.html', form=form)


@app.route('/employee/list')
@login_required
def employee_list():
    employees = Employee.query.all()
    return render_template("employee_list.html", employees=employees)


@app.route("/pip/select-employee", methods=["GET", "POST"])
@login_required
def select_employee_for_pip():
    employees = Employee.query.order_by(Employee.last_name).all()
    if request.method == "POST":
        selected_id = request.form.get("employee_id")
        return redirect(url_for("create_pip", employee_id=selected_id))
    return render_template("pip_select_employee.html", employees=employees)


# ✅ Create DB if it doesn't exist (fix for Railway startup crash)
import os

with app.app_context():
    if not os.path.exists("pip_crm.db"):
        db.create_all()
        print("✅ Database created")


# ✅ Debug/test route
@app.route("/ping")
def ping():
    return "Pong!"

print("✅ Flask app initialized and ready.")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
