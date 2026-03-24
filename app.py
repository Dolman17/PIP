import os
import zipfile

from datetime import timedelta

from flask import (
    Flask, session, render_template, request, jsonify
)
from flask_migrate import Migrate
from flask_login import (
    LoginManager, login_required, current_user
)
from flask_wtf.csrf import CSRFProtect, generate_csrf

from dotenv import load_dotenv
load_dotenv()

from forms import (
    LoginForm,
    UserForm,
)

from models import (
    db,
    User,
    Employee,
    PIPRecord,
    PIPActionItem,
    TimelineEvent,
    DraftPIP,
    ImportJob,
    DocumentFile,
    SicknessCase,
)

from pip_app.services.ai_utils import client
from pip_app.services.auth_utils import superuser_required
from pip_app.services.dashboard_utils import counts_by_field, open_pips_scoped_query
from pip_app.services.document_utils import (
    BASE_DIR,
    build_doc_rel_dir,
    build_placeholder_mapping,
    docx_to_html,
    generate_docx_bytes,
    html_to_docx_bytes,
    render_docx,
    replace_placeholders_docx,
    sanitize_html,
    strip_outcome_conditionals,
)
from pip_app.services.import_utils import (
    ALLOWED_EXTS,
    EMPLOYEE_FIELDS,
    REQUIRED_FIELDS,
    XLSX_ENABLED,
    normalize_header,
    parse_iso_date,
    read_csv_bytes,
    read_xlsx_bytes,
    try_parse_date,
)
from pip_app.services.sickness_metrics import compute_sickness_trigger_metrics
from pip_app.services.storage_utils import next_version_for, save_file
from pip_app.services.time_utils import LONDON_TZ, auto_review_date, now_local, now_utc, today_local
from pip_app.services.timeline_utils import log_timeline_event
from pip_app.services.taxonomy import (
    ACTION_TEMPLATES,
    CURATED_TAGS,
    merge_curated_and_recent as _merge_curated_and_recent,
    pick_actions_from_templates as _pick_actions_from_templates,
)

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-only-secret')
app.jinja_env.globals["now_utc"] = now_utc
app.jinja_env.globals["now_local"] = now_local
app.jinja_env.globals["today_local"] = today_local

DB_PATH = os.path.join(BASE_DIR, 'pip_crm.db')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + DB_PATH
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads', 'documents')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

app.config['WTF_CSRF_ENABLED'] = True
app.config['WTF_CSRF_TIME_LIMIT'] = None
csrf = CSRFProtect(app)

db.init_app(app)
migrate = Migrate(app, db)

from pip_app.blueprints.auth import auth_bp
from pip_app.blueprints.main import main_bp
from pip_app.blueprints.taxonomy import taxonomy_bp
from pip_app.blueprints.admin import admin_bp
from pip_app.blueprints.probation import probation_bp
from pip_app.blueprints.sickness import sickness_bp
from pip_app.blueprints.employees import employees_bp
from pip_app.blueprints.pip import pip_bp, get_active_draft_for_user
from pip_app.blueprints.employee_relations import employee_relations_bp
from pip_app.blueprints.manage_employee import manage_employee_bp

login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message_category = 'info'
login_manager.init_app(app)

app.register_blueprint(auth_bp)
app.register_blueprint(main_bp)
app.register_blueprint(taxonomy_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(probation_bp)
app.register_blueprint(sickness_bp)
app.register_blueprint(employees_bp)
app.register_blueprint(pip_bp)
app.register_blueprint(employee_relations_bp)
app.register_blueprint(manage_employee_bp)

csrf.exempt(app.view_functions['employees.quick_add_employee'])
csrf.exempt(app.view_functions['pip.suggest_actions_ai'])
csrf.exempt(app.view_functions['pip.dismiss_draft'])
csrf.exempt(app.view_functions['pip.save_pip_draft'])


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


@app.context_processor
def inject_module():
    return dict(active_module=session.get('active_module'))


@app.context_processor
def inject_csrf_token():
    return dict(csrf_token=generate_csrf)


@app.context_processor
def inject_time_helpers():
    return {
        "now_local": now_local,
        "today_local": today_local,
        "now_utc": now_utc,
    }


# Template endpoint compatibility for moved blueprints
LEGACY_ENDPOINT_ALIASES = {
    "admin_dashboard": "admin.admin_dashboard",
    "manage_users": "admin.manage_users",
    "edit_user": "admin.edit_user",
    "create_user": "admin.create_user",
    "delete_user": "admin.delete_user",
    "backup_database": "admin.backup_database",
    "export_data": "admin.export_data",

    "taxonomy_predefined_tags": "taxonomy.taxonomy_predefined_tags",
    "taxonomy_categories": "taxonomy.taxonomy_categories",
    "taxonomy_tags_suggest": "taxonomy.taxonomy_tags_suggest",
    "taxonomy_action_templates": "taxonomy.taxonomy_action_templates",

    "employee_detail": "employees.employee_detail",
    "edit_employee": "employees.edit_employee",
    "add_employee": "employees.add_employee",
    "quick_add_employee": "employees.quick_add_employee",
    "employee_list": "employees.employee_list",
    "employee_import": "employees.employee_import",
    "employee_import_validate": "employees.employee_import_validate",
    "employee_import_commit": "employees.employee_import_commit",

    "pip_detail": "pip.pip_detail",
    "edit_pip": "pip.edit_pip",
    "generate_ai_advice": "pip.generate_ai_advice",
    "create_pip": "pip.create_pip",
    "pip_list": "pip.pip_list",
    "select_employee_for_pip": "pip.select_employee_for_pip",
    "create_pip_wizard": "pip.create_pip_wizard",
    "validate_wizard_step": "pip.validate_wizard_step",
    "suggest_actions_ai": "pip.suggest_actions_ai",
    "dismiss_draft": "pip.dismiss_draft",
    "save_pip_draft": "pip.save_pip_draft",
    "pip_wizard_resume": "pip.pip_wizard_resume",
    "pip_documents": "pip.pip_documents",
    "create_pip_doc_draft": "pip.create_pip_doc_draft",
    "edit_pip_doc": "pip.edit_pip_doc",
    "finalise_pip_doc": "pip.finalise_pip_doc",
    "download_doc": "pip.download_doc",

    "probation_create_wizard": "probation.probation_create_wizard",
    "probation_save_draft": "probation.probation_save_draft",
    "probation_resume_draft": "probation.probation_resume_draft",
    "dismiss_probation_draft": "probation.dismiss_probation_draft",
    "view_probation": "probation.view_probation",
    "add_probation_review": "probation.add_probation_review",
    "add_probation_plan": "probation.add_probation_plan",
    "edit_probation": "probation.edit_probation",
    "update_probation_status": "probation.update_probation_status",
    "create_probation": "probation.create_probation",
    "probation_dashboard": "probation.probation_dashboard",
    "probation_employee_list": "probation.probation_employee_list",

    "sickness_dashboard": "sickness.sickness_dashboard",
    "sickness_list": "sickness.sickness_list",
    "sickness_create_for_employee": "sickness.sickness_create_for_employee",
    "create_sickness_case": "sickness.create_sickness_case",
    "view_sickness_case": "sickness.view_sickness_case",
    "add_sickness_meeting": "sickness.add_sickness_meeting",
    "update_sickness_status": "sickness.update_sickness_status",

    "employee_relations_dashboard": "employee_relations.dashboard",
    "employee_relations_case_list": "employee_relations.case_list",
    "employee_relations_create_case": "employee_relations.create_case",
    "employee_relations_view_case": "employee_relations.view_case",
    "employee_relations_edit_case": "employee_relations.edit_case",

    "manage_employee_index": "manage_employee.index",
    "manage_employee_detail": "manage_employee.detail",
    "manage_employee_mark_leaver": "manage_employee.mark_leaver",
    "manage_employee_reactivate": "manage_employee.reactivate",
}

from flask import url_for as flask_url_for


def compat_url_for(endpoint, **values):
    endpoint = LEGACY_ENDPOINT_ALIASES.get(endpoint, endpoint)
    return flask_url_for(endpoint, **values)


app.jinja_env.globals["url_for"] = compat_url_for


@app.before_request
def set_active_module():
    path = (request.path or "").lower()
    if path.startswith('/pip/') or path.startswith('/employee/') or path in (
        '/dashboard', '/pip_list', '/employee/list', '/employee/add', '/pip/select-employee'
    ):
        session['active_module'] = 'PIP'
    elif path.startswith('/probation/'):
        session['active_module'] = 'Probation'
    elif path.startswith('/sickness/'):
        session['active_module'] = 'Sickness'
    elif path.startswith('/employee-relations/'):
        session['active_module'] = 'Employee Relations'
    elif path == '/':
        session.pop('active_module', None)


@app.route('/dashboard')
@login_required
def dashboard():
    total_employees = Employee.query.count()
    active_pips = PIPRecord.query.filter_by(status='Open').count()
    completed_pips = PIPRecord.query.filter_by(status='Completed').count()

    today = today_local()
    upcoming_deadline = today + timedelta(days=7)

    if current_user.admin_level == 0:
        q_base = (
            PIPRecord.query
            .join(Employee)
            .filter(Employee.team_id == current_user.team_id)
            .filter(PIPRecord.assigned_to == current_user.id)
        )

        overdue_reviews = q_base.filter(
            PIPRecord.status == 'Open',
            PIPRecord.review_date < today
        ).count()

        open_pips = q_base.filter(PIPRecord.status == 'Open') \
            .order_by(PIPRecord.review_date.asc().nullslast()) \
            .all()

        q_upcoming = q_base.filter(
            PIPRecord.status == 'Open',
            PIPRecord.review_date >= today,
            PIPRecord.review_date <= upcoming_deadline
        )
        upcoming_pips = q_upcoming.order_by(PIPRecord.review_date.asc()).all()
        due_soon_count = q_upcoming.count()

        recent_activity = (
            TimelineEvent.query
            .join(PIPRecord, TimelineEvent.pip_record_id == PIPRecord.id)
            .filter(PIPRecord.assigned_to == current_user.id)
            .order_by(TimelineEvent.timestamp.desc())
            .limit(10)
            .all()
        )
    else:
        overdue_reviews = PIPRecord.query.filter(
            PIPRecord.status == 'Open',
            PIPRecord.review_date < today
        ).count()

        open_pips = PIPRecord.query.filter(PIPRecord.status == 'Open') \
            .join(Employee) \
            .order_by(PIPRecord.review_date.asc().nullslast()) \
            .all()

        upcoming_pips = PIPRecord.query.filter(
            PIPRecord.status == 'Open',
            PIPRecord.review_date >= today,
            PIPRecord.review_date <= upcoming_deadline
        ).order_by(PIPRecord.review_date.asc()).all()

        due_soon_count = PIPRecord.query.filter(
            PIPRecord.status == 'Open',
            PIPRecord.review_date >= today,
            PIPRecord.review_date <= upcoming_deadline
        ).count()

        recent_activity = TimelineEvent.query.order_by(TimelineEvent.timestamp.desc()).limit(10).all()

    draft = get_active_draft_for_user(current_user.id)

    return render_template(
        'dashboard.html',
        total_employees=total_employees,
        active_pips=active_pips,
        completed_pips=completed_pips,
        overdue_reviews=overdue_reviews,
        recent_activity=recent_activity,
        upcoming_pips=upcoming_pips,
        open_pips=open_pips,
        due_soon_count=due_soon_count,
        draft=draft
    )


@app.route('/dashboard/stats.json')
@login_required
def dashboard_stats_json():
    today = today_local()
    upcoming_deadline = today + timedelta(days=7)

    base = open_pips_scoped_query()
    by_category = counts_by_field(PIPRecord.concern_category)
    by_severity = counts_by_field(PIPRecord.severity)

    open_total = base.count()
    due_soon = base.filter(
        PIPRecord.review_date >= today,
        PIPRecord.review_date <= upcoming_deadline
    ).count()
    overdue = base.filter(PIPRecord.review_date < today).count()

    return jsonify({
        "by_category": by_category,
        "by_severity": by_severity,
        "totals": {"open": open_total, "due_soon": due_soon, "overdue": overdue}
    })


@app.route('/ping')
def ping():
    return 'Pong!'


print('✅ Flask app initialized and ready.')

if __name__ == "__main__":
    with app.app_context():
        app.run(host="0.0.0.0")