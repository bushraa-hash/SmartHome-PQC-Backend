import re
from datetime import datetime, timezone
from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    field_serializer,
    field_validator,
)


def _format_utc_z(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)
    return dt.isoformat().replace("+00:00", "Z")


def _check_password_strength(value: str) -> str:
    if len(value) < 8:
        raise ValueError("Password must be at least 8 characters long")
    if not re.search(r"[A-Z]", value):
        raise ValueError("Password must contain at least one uppercase letter")
    if not re.search(r"[a-z]", value):
        raise ValueError("Password must contain at least one lowercase letter")
    if not re.search(r"\d", value):
        raise ValueError("Password must contain at least one number")
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", value):
        raise ValueError("Password must contain at least one special character (!@#$%^&*)")
    return value


class DeviceResponse(BaseModel):
    id: int
    component_name: str
    component_type: str
    gpio_pin: int | None
    status: str
    created_at: datetime

    @field_serializer("created_at")
    def serialize_created_at(self, value: datetime) -> str:
        return _format_utc_z(value)

    model_config = ConfigDict(from_attributes=True)


class SensorReadingCreate(BaseModel):
    temperature: float | None = None
    humidity: float | None = None
    motion: bool = False


class SensorReadingResponse(BaseModel):
    id: int
    temperature: float | None
    humidity: float | None
    motion: bool
    timestamp: datetime

    @field_serializer("timestamp")
    def serialize_timestamp(self, value: datetime) -> str:
        return _format_utc_z(value)

    model_config = ConfigDict(from_attributes=True)


class UserRegister(BaseModel):
    full_name: str = Field(min_length=2, max_length=150)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, value):
        return _check_password_strength(value)


class AdminCreateUser(BaseModel):
    full_name: str = Field(min_length=2, max_length=150)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    role: str = "normal_user"

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, value):
        return _check_password_strength(value)

    @field_validator("role")
    @classmethod
    def validate_role(cls, value):
        allowed_roles = {"admin", "normal_user"}
        if value not in allowed_roles:
            raise ValueError("Role must be 'admin' or 'normal_user'")
        return value


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: int
    full_name: str
    email: EmailStr
    role: str
    status: str
    is_active: bool
    created_at: datetime

    @field_serializer("created_at")
    def serialize_created_at(self, value: datetime) -> str:
        return _format_utc_z(value)

    model_config = ConfigDict(from_attributes=True)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class RoleUpdate(BaseModel):
    role: str

    @field_validator("role")
    @classmethod
    def validate_role(cls, value):
        allowed_roles = {"admin", "normal_user"}
        if value not in allowed_roles:
            raise ValueError("Role must be 'admin' or 'normal_user'")
        return value


class ApproveUser(BaseModel):
    role: str = "normal_user"

    @field_validator("role")
    @classmethod
    def validate_role(cls, value):
        allowed_roles = {"admin", "normal_user"}
        if value not in allowed_roles:
            raise ValueError("Role must be 'admin' or 'normal_user'")
        return value


class StatusUpdate(BaseModel):
    is_active: bool


class PasswordChange(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8, max_length=128)

    @field_validator("new_password")
    @classmethod
    def validate_new_password_strength(cls, value):
        return _check_password_strength(value)