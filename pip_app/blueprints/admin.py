from __future__ import annotations

import csv
import os
import tempfile
import zipfile
from datetime import datetime
from io import BytesIO

from flask import Blueprint, flash, redirect, render_template, request, send_file, url_for
from flask_login import current_user, login_required
from werkzeug.security import generate_password_hash

from forms import UserForm
from models import (
    db,
    Employee,
    PIPRecord,
    ProbationPlan,
    ProbationRecord,
    ProbationReview,
    TimelineEvent,
    User,
    OrganisationModuleSetting,
)
from pip_app.decorators import superuser_required
from pip_app.services.module_settings import (
    DEFAULT_MODULE_LABELS,
    ensure_default_module_settings,
    get_module_settings_for_org,
)

admin_bp = Blueprint("admin", __name__)


@admin_bp.route("/admin/dashboard")
@login_required
def admin_dashboard():
    if not current_user.is_superuser():
        flash("You do not have permission to access the admin dashboard.", "danger")
        return redirect(url_for("main.home"))
    return render_template("admin_dashboard.html")


@admin_bp.route("/admin/modules", methods=["GET", "POST"])
@login_required
@superuser_required
def admin_module_settings():
    ensure_default_module_settings()
    org, existing_settings = get_module_settings_for_org()

    if request.method == "POST":
        for module_key, _label in DEFAULT_MODULE_LABELS:
            should_enable = request.form.get(module_key) == "on"
            setting = existing_settings.get(module_key)

            if setting is None:
                setting = OrganisationModuleSetting(
                    organisation_id=org.id,
                    module_key=module_key,
                    is_enabled=should_enable,
                )
                db.session.add(setting)
            else:
                setting.is_enabled = should_enable

        db.session.commit()
        flash("Module settings updated successfully.", "success")
        return redirect(url_for("admin.admin_module_settings"))

    settings = {
        module_key: bool(existing_settings.get(module_key).is_enabled) if existing_settings.get(module_key) else True
        for module_key, _label in DEFAULT_MODULE_LABELS
    }

    return render_template(
        "admin_module_settings.html",
        settings=settings,
        module_labels=DEFAULT_MODULE_LABELS,
        organisation=org,
    )


@admin_bp.route("/admin/export")
@login_required
@superuser_required
def export_data():
    zip_buffer = BytesIO()

    with tempfile.TemporaryDirectory() as tmpdir:
        def write_csv(filename, fieldnames, rows, export_zip_obj):
            filepath = os.path.join(tmpdir, filename)
            with open(filepath, "w", newline="", encoding="utf-8") as file_obj:
                writer = csv.DictWriter(file_obj, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(rows)
            export_zip_obj.write(filepath, arcname=filename)

        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as export_zip:
            employees = Employee.query.all()
            write_csv(
                "employees.csv",
                [
                    "id",
                    "first_name",
                    "last_name",
                    "job_title",
                    "line_manager",
                    "service",
                    "start_date",
                    "team_id",
                    "email",
                ],
                [
                    {
                        "id": employee.id,
                        "first_name": getattr(employee, "first_name", ""),
                        "last_name": getattr(employee, "last_name", ""),
                        "job_title": employee.job_title,
                        "line_manager": employee.line_manager,
                        "service": employee.service,
                        "start_date": employee.start_date.strftime("%Y-%m-%d") if employee.start_date else "",
                        "team_id": employee.team_id,
                        "email": employee.email,
                    }
                    for employee in employees
                ],
                export_zip,
            )

            pips = PIPRecord.query.all()
            write_csv(
                "pip_records.csv",
                [
                    "id",
                    "employee_id",
                    "concerns",
                    "concern_category",
                    "severity",
                    "frequency",
                    "tags",
                    "start_date",
                    "review_date",
                    "status",
                    "created_by",
                ],
                [
                    {
                        "id": pip_record.id,
                        "employee_id": pip_record.employee_id,
                        "concerns": pip_record.concerns,
                        "concern_category": getattr(pip_record, "concern_category", ""),
                        "severity": getattr(pip_record, "severity", ""),
                        "frequency": getattr(pip_record, "frequency", ""),
                        "tags": getattr(pip_record, "tags", ""),
                        "start_date": pip_record.start_date.strftime("%Y-%m-%d") if pip_record.start_date else "",
                        "review_date": pip_record.review_date.strftime("%Y-%m-%d") if pip_record.review_date else "",
                        "status": pip_record.status,
                        "created_by": getattr(pip_record, "created_by", ""),
                    }
                    for pip_record in pips
                ],
                export_zip,
            )

            events = TimelineEvent.query.all()
            write_csv(
                "timeline_events.csv",
                ["id", "pip_record_id", "employee_id", "event_type", "notes", "updated_by", "timestamp"],
                [
                    {
                        "id": event.id,
                        "pip_record_id": event.pip_record_id if event.pip_record_id else "",
                        "employee_id": event.pip_record.employee_id if event.pip_record else "",
                        "event_type": getattr(event, "event_type", ""),
                        "notes": getattr(event, "notes", ""),
                        "updated_by": getattr(event, "updated_by", ""),
                        "timestamp": event.timestamp.strftime("%Y-%m-%d %H:%M:%S") if event.timestamp else "",
                    }
                    for event in events
                ],
                export_zip,
            )

            users = User.query.all()
            write_csv(
                "users.csv",
                ["id", "username", "email", "admin_level", "team_id"],
                [
                    {
                        "id": user.id,
                        "username": user.username,
                        "email": user.email,
                        "admin_level": user.admin_level,
                        "team_id": user.team_id,
                    }
                    for user in users
                ],
                export_zip,
            )

            probations = ProbationRecord.query.all()
            write_csv(
                "probation_records.csv",
                ["id", "employee_id", "status", "start_date", "expected_end_date", "notes"],
                [
                    {
                        "id": probation.id,
                        "employee_id": probation.employee_id,
                        "status": probation.status,
                        "start_date": probation.start_date.strftime("%Y-%m-%d") if probation.start_date else "",
                        "expected_end_date": probation.expected_end_date.strftime("%Y-%m-%d") if probation.expected_end_date else "",
                        "notes": probation.notes,
                    }
                    for probation in probations
                ],
                export_zip,
            )

            reviews = ProbationReview.query.all()
            write_csv(
                "probation_reviews.csv",
                ["id", "probation_id", "review_date", "reviewer", "summary", "concerns_flag"],
                [
                    {
                        "id": review.id,
                        "probation_id": review.probation_id,
                        "review_date": review.review_date.strftime("%Y-%m-%d") if review.review_date else "",
                        "reviewer": review.reviewer,
                        "summary": review.summary,
                        "concerns_flag": review.concerns_flag,
                    }
                    for review in reviews
                ],
                export_zip,
            )

            plans = ProbationPlan.query.all()
            write_csv(
                "probation_plans.csv",
                ["id", "probation_id", "objectives", "outcome", "deadline"],
                [
                    {
                        "id": plan.id,
                        "probation_id": plan.probation_id,
                        "objectives": getattr(plan, "objectives", ""),
                        "outcome": getattr(plan, "outcome", ""),
                        "deadline": plan.deadline.strftime("%Y-%m-%d") if getattr(plan, "deadline", None) else "",
                    }
                    for plan in plans
                ],
                export_zip,
            )

    zip_buffer.seek(0)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
    return send_file(
        zip_buffer,
        mimetype="application/zip",
        as_attachment=True,
        download_name=f"export_{timestamp}.zip",
    )


@admin_bp.route("/admin/users")
@login_required
def manage_users():
    if not current_user.is_superuser():
        flash("Access denied.", "danger")
        return redirect(url_for("dashboard"))
    users = User.query.all()
    return render_template("admin_users.html", users=users)


@admin_bp.route("/admin/users/edit/<int:user_id>", methods=["GET", "POST"])
@login_required
def edit_user(user_id):
    if not current_user.is_superuser():
        flash("Access denied.", "danger")
        return redirect(url_for("dashboard"))

    user = User.query.get_or_404(user_id)
    form = UserForm(obj=user)

    if form.validate_on_submit():
        user.username = form.username.data
        user.email = form.email.data
        user.admin_level = form.admin_level.data
        user.team_id = form.team_id.data
        db.session.commit()
        flash("User updated successfully.", "success")
        return redirect(url_for("admin.manage_users"))

    return render_template("edit_user.html", form=form, user=user)


@admin_bp.route("/admin/users/create", methods=["GET", "POST"])
@login_required
def create_user():
    if not current_user.is_superuser():
        flash("Access denied: Superuser only.", "danger")
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        email = (request.form.get("email") or "").strip()
        password = request.form.get("password")
        admin_level = int(request.form.get("admin_level", 0))
        team_id_raw = (request.form.get("team_id") or "").strip()
        team_id = int(team_id_raw) if team_id_raw else None

        if not username or not email or not password:
            flash("All fields except team ID are required.", "danger")
            return redirect(request.url)

        if User.query.filter_by(username=username).first():
            flash("Username already exists.", "danger")
            return redirect(request.url)

        if User.query.filter_by(email=email).first():
            flash("Email already in use.", "danger")
            return redirect(request.url)

        hashed_pw = generate_password_hash(password)
        new_user = User(
            username=username,
            email=email,
            password_hash=hashed_pw,
            admin_level=admin_level,
            team_id=team_id,
        )
        db.session.add(new_user)
        db.session.commit()

        flash("User created successfully.", "success")
        return redirect(url_for("admin.manage_users"))

    return render_template("admin_create_user.html")


@admin_bp.route("/admin/users/delete/<int:user_id>", methods=["POST"])
@login_required
def delete_user(user_id):
    if not current_user.is_superuser():
        flash("Access denied: Superuser only.", "danger")
        return redirect(url_for("dashboard"))

    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash("You cannot delete your own account while logged in.", "warning")
        return redirect(url_for("admin.manage_users"))

    db.session.delete(user)
    db.session.commit()
    flash("User deleted successfully.", "success")
    return redirect(url_for("admin.manage_users"))


@admin_bp.route("/admin/backup")
@login_required
def backup_database():
    if not current_user.is_superuser():
        flash("Access denied: Superuser only.", "danger")
        return redirect(url_for("main.home"))

    db_path = os.path.join(os.getcwd(), "pip_crm.db")
    if os.path.exists(db_path):
        return send_file(db_path, as_attachment=True)

    flash("Database file not found.", "danger")
    return redirect(url_for("admin.admin_dashboard"))
