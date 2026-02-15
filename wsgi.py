"""WSGI entrypoint for the PIP Web App.

Production servers (e.g. Gunicorn/Railway) should point at
`wsgi:app`. The actual Flask application is created by the
application factory in pip_app.
"""

from pip_app import create_app

app = create_app()
