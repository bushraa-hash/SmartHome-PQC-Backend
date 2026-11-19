
from sqlalchemy.orm import Session

from app.models import User
from app.core.security import hash_password, verify_password


def get_user_by_email(db: Session, email: str):
    return db.query(User).filter(
        User.email == email.lower()
    ).first()


def get_user_by_id(db: Session, user_id: int):
    return db.query(User).filter(
        User.id == user_id
    ).first()


def create_user(
    db: Session,
    full_name: str,
    email: str,
    password: str,
):
    user = User(
        full_name=full_name,
        email=email.lower(),
        hashed_password=hash_password(password),
        role="normal_user",
        is_active=True,
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return user


def authenticate_user(
    db: Session,
    email: str,
    password: str,
):
    user = get_user_by_email(db, email)

    if user is None:
        return None

    if not verify_password(
        password,
        user.hashed_password
    ):
        return None

    if not user.is_active:
        return None

    return user
