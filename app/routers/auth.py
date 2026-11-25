from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)
from sqlalchemy.orm import Session

from app.core.security import (
    create_access_token,
    get_current_user,
    hash_password,
    require_roles,
)
from app.database import get_db
from app.models import User
from app.schemas import (
    AdminCreateUser,
    ApproveUser,
    PasswordChange,
    RoleUpdate,
    StatusUpdate,
    TokenResponse,
    UserLogin,
    UserRegister,
    UserResponse,
)
from app.services.audit_service import log_security_event
from app.services.auth_service import (
    authenticate_user,
    get_user_by_email,
)

router = APIRouter(
    prefix="/api/auth",
    tags=["Authentication"],
)


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
def register_request(
    user_data: UserRegister,
    db: Session = Depends(get_db),
):
    normalized_email = user_data.email.strip().lower()
    existing_user = get_user_by_email(db, normalized_email)

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered or pending approval",
        )

    user = User(
        full_name=user_data.full_name.strip(),
        email=normalized_email,
        hashed_password=hash_password(user_data.password),
        role="pending",
        status="pending",
        is_active=False,
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return user


@router.post(
    "/login",
    response_model=TokenResponse,
)
def login(
    login_data: UserLogin,
    db: Session = Depends(get_db),
):
    user = authenticate_user(
        db,
        login_data.email,
        login_data.password,
    )

    if user is None:
        log_security_event(
            db=db,
            event_type="LOGIN_FAILED",
            severity="WARNING",
            actor=login_data.email,
            details="Failed login attempt (incorrect email or password)",
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if user.status == "pending" or user.role == "pending":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account is pending admin approval",
        )

    if user.status == "rejected":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your registration request was rejected by the admin",
        )

    if user.status == "disabled" or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account is deactivated. Contact an admin.",
        )

    token = create_access_token(user.id)

    return {
        "access_token": token,
        "token_type": "bearer",
    }


@router.get(
    "/me",
    response_model=UserResponse,
)
def get_my_profile(
    current_user: User = Depends(get_current_user),
):
    return current_user


@router.post(
    "/change-password",
)
def change_my_password(
    password_data: PasswordChange,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    verified = authenticate_user(
        db,
        current_user.email,
        password_data.current_password,
    )

    if verified is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )

    current_user.hashed_password = hash_password(password_data.new_password)
    db.commit()

    return {"message": "Password updated successfully"}


@router.get(
    "/users",
    response_model=list[UserResponse],
)
def get_all_users(
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_roles("admin")),
):
    return db.query(User).order_by(User.id).all()


@router.post(
    "/users",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
def admin_create_user(
    user_data: AdminCreateUser,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_roles("admin")),
):
    normalized_email = user_data.email.strip().lower()
    existing_user = get_user_by_email(db, normalized_email)

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    user = User(
        full_name=user_data.full_name.strip(),
        email=normalized_email,
        hashed_password=hash_password(user_data.password),
        role=user_data.role,
        status="active",
        is_active=True,
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return user


@router.patch(
    "/users/{user_id}/approve",
    response_model=UserResponse,
)
def approve_pending_user(
    user_id: int,
    approve_data: ApproveUser,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_roles("admin")),
):
    user = db.query(User).filter(User.id == user_id).first()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    if user.status != "pending" and user.role != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only pending requests can be approved",
        )

    user.role = approve_data.role
    user.status = "active"
    user.is_active = True
    db.commit()
    db.refresh(user)

    return user


@router.patch(
    "/users/{user_id}/reject",
    response_model=UserResponse,
)
def reject_pending_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_roles("admin")),
):
    user = db.query(User).filter(User.id == user_id).first()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    if user.status != "pending" and user.role != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only pending requests can be rejected",
        )

    user.role = "normal_user"
    user.status = "rejected"
    user.is_active = False
    db.commit()
    db.refresh(user)

    return user


@router.patch(
    "/users/{user_id}/role",
    response_model=UserResponse,
)
def update_user_role(
    user_id: int,
    role_data: RoleUpdate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_roles("admin")),
):
    if user_id == current_admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot change your own role",
        )

    user = db.query(User).filter(User.id == user_id).first()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    if user.status in {"pending", "rejected"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot change role of a pending or rejected user",
        )

    user.role = role_data.role
    db.commit()
    db.refresh(user)

    return user


@router.patch(
    "/users/{user_id}/status",
    response_model=UserResponse,
)
def update_user_status(
    user_id: int,
    status_data: StatusUpdate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_roles("admin")),
):
    if user_id == current_admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot deactivate your own account",
        )

    user = db.query(User).filter(User.id == user_id).first()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    if user.status in {"pending", "rejected"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot activate/deactivate a pending or rejected user",
        )

    user.is_active = status_data.is_active
    user.status = "active" if status_data.is_active else "disabled"
    db.commit()
    db.refresh(user)

    return user


@router.delete(
    "/users/{user_id}",
)
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_roles("admin")),
):
    if user_id == current_admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot delete your own account",
        )

    user = db.query(User).filter(User.id == user_id).first()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    db.delete(user)
    db.commit()

    return {"message": "User deleted successfully"}