# seed_data.py

import os
import random
from datetime import date, timedelta

from app import app, db
from models import Employee, PIPRecord, PIPActionItem

# ---- Sample pools ----
first_names = ["Alice", "Bob", "Carol", "Dave", "Eve", "Frank", "Grace", "Hank", "Ivy", "Jack"]
last_names  = ["Anderson", "Brown", "Clark", "Davis", "Evans", "Foster", "Green", "Hill", "Irwin", "Jones"]
services    = ["IT Support", "HR", "Finance", "Sales", "Marketing"]
job_titles  = ["Analyst", "Coordinator", "Manager", "Specialist", "Technician"]

concerns_list = [
    "Missed multiple key project deadlines",
    "Lack of clear communication with team",
    "Quality of deliverables below standard",
    "Low participation in team meetings",
    "Incomplete documentation of work",
    "Difficulty adapting to new tools",
    "Insufficient follow-through on tasks",
    "Poor time management skills",
    "Frequent unplanned absences",
    "Low customer satisfaction scores"
]

action_items_pool = [
    "Provide weekly status updates to manager",
    "Attend a time-management workshop",
    "Pair-program with a peer for knowledge sharing",
    "Draft clear process documentation",
    "Shadow senior team member on project tasks",
    "Set daily to-do list and track completion",
    "Schedule bi-weekly one-on-one meetings",
    "Complete communication skills training",
    "Use task-tracking software consistently",
    "Review quality checklist before submission"
]

def seed():
    with app.app_context():
        # optional: clear existing data
        # Employee.query.delete()
        # PIPRecord.query.delete()
        # PIPActionItem.query.delete()
        # db.session.commit()

        for i in range(10):
            # Create employee
            emp = Employee(
                first_name = first_names[i],
                last_name  = last_names[i],
                job_title  = job_titles[i % len(job_titles)],
                line_manager = f"{first_names[(i+1)%10]} {last_names[(i+1)%10]}",
                service    = services[i % len(services)],
                start_date = date.today() - timedelta(days=30 + i*5),
                team_id    = (i % 3) + 1
            )
            db.session.add(emp)
            db.session.flush()  # get emp.id

            # Create PIP with random concern
            concern = random.choice(concerns_list)
            pip = PIPRecord(
                employee_id   = emp.id,
                concerns      = concern,
                start_date    = date.today() - timedelta(days=random.randint(1,7)),
                review_date   = date.today() + timedelta(days=random.randint(14,45)),
                meeting_notes = "",
                status        = "Open",
                created_by    = "system_seed"
            )
            db.session.add(pip)
            db.session.flush()  # get pip.id

            # Add 2–4 random action items
            num_actions = random.randint(2, 4)
            for desc in random.sample(action_items_pool, num_actions):
                item = PIPActionItem(
                    pip_record_id = pip.id,
                    description   = desc,
                    status        = random.choice(["Outstanding", "Completed"])
                )
                db.session.add(item)

        db.session.commit()
        print("✅ Seeded 10 employees, each with a live PIP and random actions.")

if __name__ == "__main__":
    # Ensure DB exists
    if not os.path.exists("pip_crm.db"):
        print("Database not found—creating.")
        with app.app_context():
            db.create_all()
    seed()
