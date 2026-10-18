"""Create (or reset) the production administrator. Run interactively:

    fly ssh console -C "python scripts/create_admin.py"
"""
import os
import sys
import getpass
from datetime import datetime, timezone

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.db.session import SessionLocal
from app.models import User, WorkerProfile, UserRole, UserStatus
from app.core.security import hash_password
from app.core.phone import normalize_phone


def main():
    phone = normalize_phone(input("Admin phone (e.g. 0712345678): ").strip())
    full_name = input("Full name: ").strip() or "TopLine Administrator"
    password = getpass.getpass("Password (min 12 chars): ")
    if len(password) < 12:
        sys.exit("Password too short (minimum 12 characters).")
    if password != getpass.getpass("Repeat password: "):
        sys.exit("Passwords do not match.")

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.phone == phone).first()
        if user:
            user.password_hash = hash_password(password)
            user.role = UserRole.ADMINISTRATOR
            user.status = UserStatus.ACTIVE
            print(f"Updated existing user {phone} -> administrator with new password.")
        else:
            user = User(
                phone=phone,
                password_hash=hash_password(password),
                role=UserRole.ADMINISTRATOR,
                status=UserStatus.ACTIVE,
                phone_verified_at=datetime.now(timezone.utc),
            )
            db.add(user)
            db.flush()
            db.add(WorkerProfile(user_id=user.id, full_name=full_name,
                                 trade="Administration", preferred_country="Kenya"))
            print(f"Created administrator {phone}.")
        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    main()
