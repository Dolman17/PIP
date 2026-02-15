from datetime import datetime

from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    session,
)
from flask_login import login_user, logout_user
from werkzeug.security import check_password_hash

from models import User  # uses the shim -> pip_app.models
from forms import LoginForm

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    form = LoginForm()
    if request.method == "POST" and form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and check_password_hash(user.password_hash, form.password.data):
            login_user(user, remember=form.remember.data)
            # home now lives in the main blueprint
            return redirect(url_for("main.home"))
        flash("Invalid username or password", "danger")
    return render_template(
        "login.html",
        form=form,
        hide_sidebar=True,
        current_year=datetime.now().year,
    )


@auth_bp.route("/logout", methods=["POST", "GET"])
def logout():
    try:
        logout_user()
    finally:
        session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("auth.login"))
