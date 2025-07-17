from flask import Flask, render_template, redirect, url_for, request, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from models import db, User, Employee, PIPRecord, TimelineEvent
from forms import PIPForm


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
    return User.query.get(int(user_id))


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


@app.route('/pip/<int:pip_id>')
@login_required
def pip_detail(pip_id):
    pip = PIPRecord.query.get_or_404(pip_id)
    employee = pip.employee
    if current_user.admin_level == 0 and employee.team_id != current_user.team_id:
        flash('Access denied')
        return redirect(url_for('dashboard'))
    return render_template('pip_detail.html', pip=pip, employee=employee)

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

@app.route('/pip/<int:pip_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_pip(pip_id):
    pip = PIPRecord.query.get_or_404(pip_id)
    employee = pip.employee

    if current_user.admin_level == 0 and employee.team_id != current_user.team_id:
        flash("Access denied.")
        return redirect(url_for('dashboard'))

    form = PIPForm(obj=pip)  # Pre-fill with current data

    if form.validate_on_submit():
        pip.concerns = form.concerns.data
        pip.start_date = form.start_date.data
        pip.review_date = form.review_date.data
        pip.action_plan = form.action_plan.data
        pip.meeting_notes = form.meeting_notes.data
        pip.last_updated = datetime.utcnow()
        db.session.commit()

        flash("PIP updated successfully.")
        return redirect(url_for('pip_detail', pip_id=pip.id))

    return render_template('edit_pip.html', form=form, pip=pip, employee=employee)

@app.route("/dashboard")
@login_required
def dashboard():
    return render_template("dashboard.html")

if __name__ == '__main__':
    app.run(debug=True)
