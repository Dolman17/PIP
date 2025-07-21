from app import app, db
from models import User
from werkzeug.security import generate_password_hash

# === CONFIGURE YOUR SUPERUSER DETAILS HERE ===
USERNAME = "admin"
EMAIL = "admin@example.com"
PASSWORD = "superpassword"  # Replace this with a secure password
ADMIN_LEVEL = 2  # 2 = superuser

# === SCRIPT LOGIC ===
with app.app_context():
    existing_user = User.query.filter_by(username=USERNAME).first()
    if existing_user:
        print(f"❌ User '{USERNAME}' already exists.")
    else:
        user = User(
            username=USERNAME,
            email=EMAIL,
            password_hash=generate_password_hash(PASSWORD),
            admin_level=ADMIN_LEVEL
        )
        db.session.add(user)
        db.session.commit()
        print(f"✅ Superuser '{USERNAME}' created successfully.")
