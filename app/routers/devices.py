from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.security import require_roles
from app.database import get_db
from app.models import Device, User
from app.schemas import DeviceResponse


router = APIRouter(
    prefix="/api/devices",
    tags=["Devices"]
)


@router.get("/", response_model=list[DeviceResponse])
def get_devices(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "normal_user")),
):
    """إرجاع قائمة الأجهزة والمكونات (محمي بـ JWT)"""
    devices = db.query(Device).order_by(Device.id).all()
    return devices


@router.get("/{device_id}", response_model=DeviceResponse)
def get_device(
    device_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "normal_user")),
):
    """إرجاع تفاصيل جهاز واحد (محمي بـ JWT)"""
    device = db.query(Device).filter(Device.id == device_id).first()

    if device is None:
        raise HTTPException(
            status_code=404,
            detail="Device not found"
        )

    return device