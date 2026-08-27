"""
Seed script for Heron Technologies Billing Management System.

Creates the database tables (if not present) and a single admin user.
No sample/demo data is inserted.

Usage:
    python seed.py
"""

from app import create_app
from extensions import db
from config import Config
from models import User

app = create_app()


def seed():
    with app.app_context():
        db.create_all()

        admin = User.query.filter_by(username=Config.ADMIN_USERNAME).first()

        if not admin:
            admin = User(
                username=Config.ADMIN_USERNAME,
                full_name="Administrator"
            )
            admin.set_password(Config.ADMIN_PASSWORD)

            db.session.add(admin)
            db.session.commit()

            print(f"Admin user created: {Config.ADMIN_USERNAME}")
        else:
            print("Admin user already exists.")

        print("Database initialized successfully.")


if __name__ == "__main__":
    seed()