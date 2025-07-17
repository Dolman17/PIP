from app import app, db
from models import Employee
from datetime import datetime

with app.app_context():
    new_employee = Employee(
        first_name="John",
        last_name="Doe",
        job_title="Support Worker",
        line_manager="Jane Smith",
        service="Lichfield",
        start_date=datetime.strptime("2024-01-01", "%Y-%m-%d"),
        team_id=1  # adjust based on valid team_id values in your app
    )
    db.session.add(new_employee)
    db.session.commit()
    print(f"Added employee: {new_employee.first_name} {new_employee.last_name} (ID: {new_employee.id})")
