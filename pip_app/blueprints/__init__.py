from .admin import admin_bp
from .auth import auth_bp
from .main import main_bp
from .probation import probation_bp
from .sickness import sickness_bp
from .employees import employees_bp
from .pip import pip_bp
from .taxonomy import taxonomy_bp

CORE_BLUEPRINTS = (
    auth_bp,
    main_bp,
    taxonomy_bp,
    admin_bp,
    probation_bp,
    sickness_bp,
    employees_bp,
    pip_bp,
)

__all__ = [
    "auth_bp",
    "main_bp",
    "taxonomy_bp",
    "admin_bp",
    "probation_bp",
    "sickness_bp",
    "employees_bp",
    "pip_bp",
    "CORE_BLUEPRINTS",
]