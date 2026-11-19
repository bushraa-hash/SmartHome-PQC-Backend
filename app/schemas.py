import re

from datetime import datetime

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    field_validator,
)


class DeviceResponse(BaseModel):
    id: int
    component_name: str
    component_type: str
    gpio_pin: int | None
    status: str
    created_at: datetime

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

    model_config = ConfigDict(from_attributes=True)


class UserRegister(BaseModel):
    full_name: str = Field(min_length=2, max_length=150)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, value):
        if not re.search(r"[A-Z]", value):
            raise ValueError(
                "Password must contain an uppercase letter"
            )

        if not re.search(r"[a-z]", value):
            raise ValueError(
                "Password must contain a lowercase letter"
            )

        if not re.search(r"\d", value):
            raise ValueError(
                "Password must contain a number"
            )

        return value


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: int
    full_name: str
    email: EmailStr
    role: str
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class RoleUpdate(BaseModel):
    role: str

    @field_validator("role")
    @classmethod
    def validate_role(cls, value):
        allowed_roles = {"normal_user", "guest"}

        if value not in allowed_roles:
            raise ValueError("Invalid role")

        return value
