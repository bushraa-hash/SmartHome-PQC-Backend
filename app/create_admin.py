
from getpass import getpass

from app.database import SessionLocal
from app.models import User
from app.core.security import hash_password


def main():
    db = SessionLocal()

    try:
        email = input("Admin email: ").strip().lower()

        existing = db.query(User).filter(
            User.email == email
        ).first()

        if existing:
            print("This email already exists.")
            return

        full_name = input("Admin full name: ").strip()

        password = getpass("Admin password: ")
        confirm_password = getpass("Confirm password: ")

        if password != confirm_password:
            print("Passwords do not match.")
            return

        if len(password) < 8:
            print("Password must be at least 8 characters.")
            return

        user = User(
            full_name=full_name,
            email=email,
            hashed_password=hash_password(password),
            role="admin",
            is_active=True,
        )

        db.add(user)
        db.commit()

        print("Admin account created successfully.")

    finally:
        db.close()


if __name__ == "__main__":
    main()
