"""Extension instances shared across the PIP Web App.

Note: In this first refactor step these are not yet initialised
via an application factory; the legacy app.py still calls
db.init_app(app) directly. In later steps, create_app() will
own initialisation.
"""

from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect


db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
csrf = CSRFProtect()
