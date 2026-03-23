"""Shared Flask extension instances.

These are the canonical extension objects for the refactor.

Phase 1A note:
- The live app is still initialised in app.py.
- We are not yet calling init_app() from pip_app.create_app().
- This file exists so models, future blueprints, and service modules can
  import a single source of truth instead of creating duplicate extension
  objects later.
"""

from flask_login import LoginManager
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect

db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
csrf = CSRFProtect()