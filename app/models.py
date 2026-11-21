from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    Boolean,
    DateTime,
)

from app.database import Base


class Device(Base):
    __tablename__ = "devices"

    id = Column(Integer, primary_key=True, index=True)

    component_name = Column(String(100), nullable=False)

    component_type = Column(String(50), nullable=False)

    gpio_pin = Column(Integer, nullable=True)

    status = Column(String(20), default="ready", nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow)


class SensorReading(Base):
    __tablename__ = "sensor_readings"

    id = Column(Integer, primary_key=True, index=True)

    temperature = Column(Float, nullable=True)

    humidity = Column(Float, nullable=True)

    motion = Column(Boolean, default=False, nullable=False)

    timestamp = Column(DateTime, default=datetime.utcnow)





class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)

    full_name = Column(String(150), nullable=False)

    email = Column(
        String(255),
        unique=True,
        index=True,
        nullable=False
    )

    hashed_password = Column(String(255), nullable=False)

    role = Column(
        String(30),
        nullable=False,
        default="normal_user"
    )

    is_active = Column(
        Boolean,
        nullable=False,
        default=True
    )

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )

class SecurityLog(Base):
    __tablename__ = "security_logs"

    id = Column(Integer, primary_key=True, index=True)
    event_type = Column(String(50), nullable=False, index=True)
    severity = Column(String(20), nullable=False, default="INFO")  # INFO, WARNING, CRITICAL
    actor = Column(String(150), nullable=True)                     # email or device_id
    details = Column(String(500), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)