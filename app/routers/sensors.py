from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.security import require_roles
from app.database import get_db
from app.models import SensorReading, User
from app.schemas import SensorReadingResponse

router = APIRouter(
    prefix="/api/sensors",
    tags=["Sensors"]
)


@router.get("/latest", response_model=SensorReadingResponse | None)
def get_latest_reading(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "normal_user")),
):
    """إرجاع أحدث قراءة حساسات (محمي بـ JWT)"""
    reading = (
        db.query(SensorReading)
        .order_by(SensorReading.timestamp.desc(), SensorReading.id.desc())
        .first()
    )
    return reading


@router.get("/history", response_model=list[SensorReadingResponse])
def get_sensor_history(
    limit: int = Query(default=50, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "normal_user")),
):
    """إرجاع سجل القراءات السابقة (محمي بـ JWT)"""
    readings = (
        db.query(SensorReading)
        .order_by(SensorReading.timestamp.desc(), SensorReading.id.desc())
        .limit(limit)
        .all()
    )
    return readings