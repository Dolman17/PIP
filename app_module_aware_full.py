
import os
from flask import Flask, session, render_template, redirect, url_for, request, flash, send_file, session
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

from models import db, User, Employee, PIPRecord, PIPActionItem, TimelineEvent, ProbationRecord, ProbationReview, ProbationPlan
from forms import PIPForm, EmployeeForm, LoginForm, ProbationRecordForm, ProbationReviewForm, ProbationPlanForm
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

# ----- Set active module in session -----
@app.before_request
def set_active_module():
    path = request.path
    if path.startswith('/pip/'):
        session['active_module'] = 'pip'
    elif path.startswith('/probation/'):
        session['active_module'] = 'probation'
    elif path == '/':
        session.pop('active_module', None)

# ... Remaining unchanged app logic here ...
