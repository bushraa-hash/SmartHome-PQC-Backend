from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import SensorReading
from app.schemas import (
    SensorReadingCreate,
    SensorReadingResponse,
)

router = APIRouter(
    prefix="/api/sensors",
    tags=["Sensors"]
)


@router.get("/latest", response_model=SensorReadingResponse | None)
def get_latest_reading(db: Session = Depends(get_db)):
    reading = (
        db.query(SensorReading)
        .order_by(SensorReading.timestamp.desc(), SensorReading.id.desc())
        .first()
    )

    return reading


@router.get("/history", response_model=list[SensorReadingResponse])
def get_sensor_history(
    limit: int = Query(default=50, ge=1, le=500),
    db: Session = Depends(get_db)):
    readings = (
        db.query(SensorReading)
        .order_by(SensorReading.timestamp.desc(), SensorReading.id.desc())
        .limit(limit)
        .all()
    )

    return readings


@router.post(
    "/readings",
    response_model=SensorReadingResponse,
    status_code=201
)
def create_sensor_reading(
    reading_data: SensorReadingCreate,
    db: Session = Depends(get_db)
):
    if (
        reading_data.temperature is None
        and reading_data.humidity is None
        and reading_data.motion is False
    ):
        raise HTTPException(
            status_code=400,
            detail="At least one sensor value must be provided"
        )

    new_reading = SensorReading(
        temperature=reading_data.temperature,
        humidity=reading_data.humidity,
        motion=reading_data.motion
    )

    db.add(new_reading)
    db.commit()
    db.refresh(new_reading)

    return new_reading