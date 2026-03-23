from __future__ import annotations

import os
import tempfile

from flask import Blueprint, abort, flash, jsonify, redirect, render_template, request, session, url_for
from flask_login import current_user, login_required
from sqlalchemy.orm import joinedload
from werkzeug.utils import secure_filename

from forms import EmployeeForm
from models import Employee, SicknessCase, TimelineEvent, db
from pip_app.services.auth_utils import superuser_required
from pip_app.services.import_utils import (
    ALLOWED_EXTS,
    EMPLOYEE_FIELDS,
    REQUIRED_FIELDS,
    XLSX_ENABLED,
    normalize_header,
    read_csv_bytes,
    read_xlsx_bytes,
    try_parse_date,
)
from pip_app.services.sickness_metrics import compute_sickness_trigger_metrics
from pip_app.services.time_utils import today_local

employees_bp = Blueprint("employees", __name__)


def _suggest_mapping(headers, normalize_func, target_fields):
    mapping = {}
    for h in headers or []:
        n = normalize_func(h)
        if n in target_fields:
            mapping[h] = n
        elif n in ("firstname", "first"):
            mapping[h] = "first_name"
        elif n in ("lastname", "last", "surname"):
            mapping[h] = "last_name"
        elif n in ("mail", "email_address"):
            mapping[h] = "email"
        elif n in ("role", "position", "title", "job", "jobrole", "job_role", "jobtitle"):
            mapping[h] = "job_title"
        elif n in ("manager", "line_manager", "linemanager", "manager_name"):
            mapping[h] = "line_manager"
        elif n in ("team", "teamid", "team_id", "dept", "department"):
            mapping[h] = "team_id"
        else:
            mapping[h] = ""
    return mapping


@employees_bp.route('/employee/<int:employee_id>')
@login_required
def employee_detail(employee_id):
    employee = (
        Employee.query.options(
            joinedload(Employee.pips),
            joinedload(Employee.probation_records),
            joinedload(Employee.sickness_cases).joinedload(SicknessCase.meetings),
        )
        .get_or_404(employee_id)
    )

    if current_user.admin_level == 0 and employee.team_id != current_user.team_id:
        flash('Access denied')
        return redirect(url_for('dashboard'))

    today = today_local()
    q_cases = SicknessCase.query.join(Employee).filter(SicknessCase.employee_id == employee.id)

    triggers = compute_sickness_trigger_metrics(
        q_cases,
        today=today,
        window_days=365,
        bradford_medium=200,
        bradford_high=400,
        episodes_threshold=3,
        total_days_threshold=14,
        long_term_days=28,
    )

    sickness_trigger = triggers[0] if triggers else None

    return render_template(
        'employee_detail.html',
        employee=employee,
        sickness_trigger=sickness_trigger,
    )


@employees_bp.route('/employee/edit/<int:employee_id>', methods=['GET', 'POST'])
@login_required
def edit_employee(employee_id):
    employee = Employee.query.get_or_404(employee_id)
    if current_user.admin_level == 0 and employee.team_id != current_user.team_id:
        flash('Access denied.')
        return redirect(url_for('dashboard'))

    form = EmployeeForm(obj=employee)
    if form.validate_on_submit():
        employee.first_name = form.first_name.data
        employee.last_name = form.last_name.data
        employee.job_title = form.job_title.data
        employee.line_manager = form.line_manager.data
        employee.service = form.service.data
        employee.start_date = form.start_date.data
        employee.team_id = form.team_id.data
        employee.email = form.email.data
        db.session.commit()
        flash('Employee details updated.', 'success')
        return redirect(url_for('employees.employee_detail', employee_id=employee.id))
    return render_template('edit_employee.html', form=form, employee=employee)


@employees_bp.route('/employee/add', methods=['GET', 'POST'])
@login_required
def add_employee():
    if current_user.admin_level < 1:
        flash('Access denied.')
        return redirect(url_for('main.home'))

    form = EmployeeForm()
    if form.validate_on_submit():
        emp = Employee(
            first_name=form.first_name.data,
            last_name=form.last_name.data,
            job_title=form.job_title.data,
            line_manager=form.line_manager.data,
            service=form.service.data,
            start_date=form.start_date.data,
            team_id=form.team_id.data,
            email=form.email.data,
        )
        db.session.add(emp)
        db.session.commit()
        flash('New employee added.')
        return redirect(url_for('employees.employee_list'))

    return render_template('add_employee.html', form=form)


@employees_bp.route('/employee/quick-add', methods=['POST'])
@login_required
def quick_add_employee():
    data = request.get_json(force=True, silent=True) or {}
    first = (data.get("first_name") or "").strip()
    last = (data.get("last_name") or "").strip()
    job_title = (data.get("job_title") or data.get("role") or "").strip()
    service = (data.get("service") or "").strip()
    line_manager = (data.get("line_manager") or current_user.username or "").strip()

    if not first or not last:
        return jsonify({"success": False, "error": "First and last name are required"}), 400

    emp = Employee(
        first_name=first,
        last_name=last,
        job_title=job_title or None,
        line_manager=line_manager or None,
        service=service or None,
        team_id=current_user.team_id if getattr(current_user, "admin_level", 0) == 0 else None,
    )
    db.session.add(emp)
    db.session.commit()

    try:
        evt = TimelineEvent(
            event_type="Employee Created",
            notes="Employee created via Quick-Add in wizard",
            updated_by=current_user.username
        )
        db.session.add(evt)
        db.session.commit()
    except Exception:
        pass

    return jsonify({"success": True, "id": emp.id, "display_name": f"{emp.first_name} {emp.last_name}"})


@employees_bp.route('/employee/list')
@login_required
def employee_list():
    template = 'probation_employee_list.html' if session.get('active_module') == 'Probation' else 'employee_list.html'
    q = Employee.query
    if current_user.admin_level == 0:
        if current_user.team_id:
            q = q.filter(Employee.team_id == current_user.team_id)
        else:
            q = q.filter(False)
    employees = q.order_by(Employee.last_name.asc(), Employee.first_name.asc()).all()
    return render_template(template, employees=employees)


@employees_bp.route("/employee/import", methods=["GET", "POST"])
@login_required
def employee_import():
    guard = superuser_required(lambda: None)
    result = guard()
    if result is not None:
        return result

    if request.method == "GET":
        return render_template("employee_import.html")

    file = request.files.get("file")
    if not file or file.filename == "":
        abort(400, "No file uploaded")

    filename = secure_filename(file.filename)
    ext = filename.rsplit(".", 1)[-1].lower()
    if ext not in ALLOWED_EXTS:
        abort(400, f"Unsupported file type: .{ext}")

    file_bytes = file.read()

    if ext == "csv":
        headers, rows = read_csv_bytes(file_bytes)
    else:
        headers, rows = read_xlsx_bytes(file_bytes)

    normalised_headers = [{"raw": h, "norm": normalize_header(h)} for h in (headers or [])]

    tmp = tempfile.NamedTemporaryFile(prefix="emp_import_", suffix=f".{ext}", delete=False)
    tmp.write(file_bytes)
    tmp.flush()
    temp_id = tmp.name
    tmp.close()

    preview = rows[:10] if rows else []

    return jsonify({
        "temp_id": temp_id,
        "headers": headers,
        "headers_norm": normalised_headers,
        "suggested_mapping": _suggest_mapping(headers, normalize_header, [
            "first_name", "last_name", "email", "job_title", "line_manager",
            "service", "team_id", "start_date",
        ]),
        "preview_rows": preview,
        "xlsx_enabled": XLSX_ENABLED
    }), 200


@employees_bp.route("/employee/import/validate", methods=["POST"])
@login_required
def employee_import_validate():
    guard = superuser_required(lambda: None)
    result = guard()
    if result is not None:
        return result

    data = request.get_json(force=True, silent=True) or {}
    temp_id = data.get("temp_id")
    mapping = data.get("mapping") or {}
    unique_key = (data.get("unique_key") or "email").strip()

    if not temp_id:
        abort(400, "Missing temp_id")
    try:
        with open(temp_id, "rb") as f:
            file_bytes = f.read()
    except Exception:
        abort(400, "Invalid temp_id or temporary file expired")

    ext = temp_id.rsplit(".", 1)[-1].lower()
    headers, rows = (read_csv_bytes(file_bytes) if ext == "csv" else read_xlsx_bytes(file_bytes))

    mapped_rows = []
    unmapped_headers = []
    for h in headers or []:
        if not mapping.get(h):
            unmapped_headers.append(h)

    for r in rows:
        out = {}
        for h, v in r.items():
            field = mapping.get(h)
            if not field:
                continue
            if field == "start_date":
                out[field] = try_parse_date(v)
            else:
                out[field] = (str(v).strip() if v is not None else None)
        mapped_rows.append(out)

    missing_required = []
    for idx, r in enumerate(mapped_rows, start=1):
        missing = [f for f in REQUIRED_FIELDS if not r.get(f)]
        if missing:
            missing_required.append({"row": idx, "missing": missing})

    duplicates_in_file = []
    if unique_key:
        keys = unique_key.split(",")
        seen = set()
        for idx, r in enumerate(mapped_rows, start=1):
            key_tuple = tuple((r.get(k.strip()) or "").lower() for k in keys)
            if all(key_tuple):
                if key_tuple in seen:
                    duplicates_in_file.append({"row": idx, "key": key_tuple})
                else:
                    seen.add(key_tuple)

    duplicates_in_db = []
    try:
        if unique_key == "email" and any(r.get("email") for r in mapped_rows):
            emails = list({r.get("email") for r in mapped_rows if r.get("email")})
            existing = set(
                e[0].lower()
                for e in db.session.query(Employee.email).filter(Employee.email.in_(emails)).all()
            )
            for idx, r in enumerate(mapped_rows, start=1):
                em = (r.get("email") or "").lower()
                if em and em in existing:
                    duplicates_in_db.append({"row": idx, "email": r.get("email")})
        elif unique_key == "first_name,last_name":
            pairs = {
                ((r.get("first_name") or "").lower(), (r.get("last_name") or "").lower())
                for r in mapped_rows if r.get("first_name") and r.get("last_name")
            }
            if pairs:
                q = db.session.query(Employee.first_name, Employee.last_name).all()
                existing_pairs = {(fn.lower(), ln.lower()) for fn, ln in q}
                for idx, r in enumerate(mapped_rows, start=1):
                    t = ((r.get("first_name") or "").lower(), (r.get("last_name") or "").lower())
                    if all(t) and t in existing_pairs:
                        duplicates_in_db.append({
                            "row": idx,
                            "name": f"{r.get('first_name')} {r.get('last_name')}"
                        })
    except Exception as e:
        duplicates_in_db = [{"error": f"DB duplicate check skipped: {e}"}]

    report = {
        "unmapped_headers": unmapped_headers,
        "missing_required": missing_required,
        "duplicates_in_file": duplicates_in_file,
        "duplicates_in_db": duplicates_in_db,
        "rows_ready": len(mapped_rows) - len(missing_required) - len(duplicates_in_file) - len(duplicates_in_db),
        "total_rows": len(mapped_rows)
    }
    return jsonify({"temp_id": temp_id, "report": report}), 200


@employees_bp.route("/employee/import/commit", methods=["POST"])
@login_required
def employee_import_commit():
    guard = superuser_required(lambda: None)
    result = guard()
    if result is not None:
        return result

    data = request.get_json(force=True, silent=True) or {}
    temp_id = data.get("temp_id")
    mapping = data.get("mapping") or {}
    confirm = bool(data.get("confirm"))
    unique_key = (data.get("unique_key") or "email").strip()

    if not (temp_id and confirm and mapping):
        abort(400, "Missing temp_id, mapping, or confirm flag")

    try:
        with open(temp_id, "rb") as f:
            file_bytes = f.read()
    except Exception:
        abort(400, "Invalid temp_id or temporary file expired")

    ext = temp_id.rsplit(".", 1)[-1].lower()
    headers, rows = (read_csv_bytes(file_bytes) if ext == "csv" else read_xlsx_bytes(file_bytes))

    created, skipped, errors = 0, 0, []

    for idx, src in enumerate(rows, start=1):
        payload = {}
        for h, v in src.items():
            field = mapping.get(h)
            if not field:
                continue
            if field == "start_date":
                payload[field] = try_parse_date(v)
            else:
                payload[field] = (str(v).strip() if v is not None else None)

        if any(not payload.get(f) for f in REQUIRED_FIELDS):
            skipped += 1
            continue

        try:
            exists = False
            if unique_key == "email" and payload.get("email"):
                exists = db.session.query(Employee.id).filter_by(email=payload["email"]).first() is not None
            elif unique_key == "first_name,last_name" and payload.get("first_name") and payload.get("last_name"):
                exists = db.session.query(Employee.id).filter_by(
                    first_name=payload["first_name"],
                    last_name=payload["last_name"]
                ).first() is not None
            if exists:
                skipped += 1
                continue
        except Exception as e:
            errors.append({"row": idx, "error": f"Duplicate check failed: {e}"})
            skipped += 1
            continue

        try:
            emp = Employee(**{k: v for k, v in payload.items() if k in EMPLOYEE_FIELDS})
            db.session.add(emp)
            created += 1
        except Exception as e:
            errors.append({"row": idx, "error": str(e)})
            skipped += 1

    db.session.commit()

    try:
        username = getattr(current_user, "username", "system")
        notes = f"Employee Import: created={created}, skipped={skipped}, errors={len(errors)}"
        evt = TimelineEvent(event_type="Import", notes=notes, updated_by=username)
        db.session.add(evt)
        db.session.commit()
    except Exception:
        pass

    try:
        if temp_id and os.path.exists(temp_id):
            os.remove(temp_id)
    except Exception:
        pass

    return jsonify({"created": created, "skipped": skipped, "errors": errors}), 200