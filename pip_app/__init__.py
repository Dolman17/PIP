"""Application package for the PIP Web App.

Phase 1A is intentionally conservative.

We expose a standard factory signature now:
    create_app(config_object=None)

But to preserve existing behaviour 1:1, the factory still returns the
current legacy Flask app instance from app.py. That lets us introduce a
proper package structure and shared services without breaking routes,
endpoint names, CSRF behaviour, or template wiring.

Later phases will move actual app creation, extension init, context
processors, and blueprint registration fully into this package.
"""

from __future__ import annotations

from typing import Any


def create_app(config_object: Any = None):
    """Return the current legacy Flask app instance.

    The import is intentionally lazy to avoid circular imports while the
    codebase is in a hybrid state.
    """
    from app import app as legacy_app  # local import on purpose

    if config_object is not None:
        if isinstance(config_object, dict):
            legacy_app.config.update(config_object)
        else:
            legacy_app.config.from_object(config_object)

    return legacy_app