import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import Base, engine, SessionLocal
from app.models import Device, User
from app.core.security import hash_password
from app.routers import devices, sensors, auth, control


def seed_devices():
    db = SessionLocal()
    try:
        existing_device = db.query(Device).first()
        if existing_device is not None:
            return

        initial_devices = [
            Device(
                component_name="DHT22 Temperature and Humidity Sensor",
                component_type="sensor",
                gpio_pin=4,
                status="ready"
            ),
            Device(
                component_name="PIR Motion Sensor",
                component_type="sensor",
                gpio_pin=27,
                status="ready"
            ),
            Device(
                component_name="1-Channel Relay",
                component_type="actuator",
                gpio_pin=17,
                status="ready"
            ),
            Device(
                component_name="Smart Light LED",
                component_type="actuator",
                gpio_pin=22,
                status="ready"
            )
        ]

        db.add_all(initial_devices)
        db.commit()
    finally:
        db.close()


def seed_admin():
    admin_email = os.getenv("ADMIN_EMAIL", "").strip().lower()
    admin_password = os.getenv("ADMIN_PASSWORD", "").strip()
    admin_name = os.getenv("ADMIN_FULL_NAME", "Admin").strip()

    if not admin_email or not admin_password:
        return

    db = SessionLocal()
    try:
        existing = db.query(User).filter(User.email == admin_email).first()
        if existing is not None:
            return

        admin_user = User(
            full_name=admin_name,
            email=admin_email,
            hashed_password=hash_password(admin_password),
            role="admin",
            is_active=True,
        )
        db.add(admin_user)
        db.commit()
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    seed_devices()
    seed_admin()
    yield


app = FastAPI(
    title="SmartHome-PQC API",
    description="Backend API for a Raspberry Pi 5 Smart Home System",
    version="1.0.0",
    lifespan=lifespan
)

# إعداد CORS موحّد يسمح بالاتصال من localhost ومن أي دومين أونلاين للفرونت إند
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=".*",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(control.router)
app.include_router(devices.router)
app.include_router(sensors.router)
app.include_router(auth.router)


@app.get("/")
def root():
    return {
        "message": "SmartHome-PQC Backend is running"
    }


@app.get("/health")
def health_check():
    return {
        "status": "healthy"
    }