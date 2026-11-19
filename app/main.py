from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import Base, engine, SessionLocal
from app.models import Device
from app.routers import devices, sensors
from app.routers import auth
from app.models import User
from app.routers import control

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


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    seed_devices()

    yield


app = FastAPI(
    title="SmartHome-PQC API",
    description="Backend API for a Raspberry Pi 5 Smart Home System",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(control.router)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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