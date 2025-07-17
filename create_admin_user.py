from app import app, db, User
from werkzeug.security import generate_password_hash

with app.app_context():
    user = User.query.filter_by(username="admin").first()
    if user:
        print("Admin user already exists.")
    else:
        user = User(
            username="admin",
            email="admin@example.com",
            password_hash=generate_password_hash("admin123"),
            admin_level=2,
            team_id=1
        )
        db.session.add(user)
        db.session.commit()
        print("Admin user created.")
