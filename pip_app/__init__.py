"""PIP Web App application package.

Phase 1: provide an application factory that simply returns
the existing app instance from app.py. This preserves all
current behaviour while giving us a standard entrypoint
for WSGI servers and future refactors.

IMPORTANT: We avoid importing `app` at module import time to
prevent circular imports when `models` imports `pip_app`.
"""

def create_app():
    """Return the existing Flask app instance.

    The import from `app` is done lazily inside this function
    to avoid circular imports during normal module loading.
    """
    from app import app as legacy_app  # local import to avoid cycles
    return legacy_app
