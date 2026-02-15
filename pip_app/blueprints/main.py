from flask import Blueprint, render_template
from flask_login import login_required

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
@login_required
def home():
    # Same as old root route
    return render_template(
        "select_module.html",
        hide_sidebar=True,
        layout="fullscreen",
    )
