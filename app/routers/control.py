from datetime import datetime, timezone
from typing import Literal, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.pqc_manager import pqc_manager
from app.core.security import require_roles
from app.database import get_db
from app.models import User
from app.services.audit_service import log_security_event


router = APIRouter(
    prefix="/api/control",
    tags=["Control"]
)

# الحالة الحالية للنظام (محفوظة بالذاكرة للسرعة والوصول الفوري من الرازبيري)
device_state = {
    "mode": "AUTO",          # AUTO أو MANUAL
    "light_state": False,    # True = ON, False = OFF
    "updated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
}


class ControlCommand(BaseModel):
    mode: Optional[Literal["AUTO", "MANUAL"]] = None
    light_state: Optional[bool] = None


@router.get("/state")
def get_control_state():
    """الرازبيري والواجهة بيطلبوا هذا الرابط لمعرفة الوضع الحالي وحالة الضوء (موقّع بـ ML-DSA-65)"""
    payload = {
        "mode": device_state["mode"],
        "light_state": device_state["light_state"],
    }
    signature = pqc_manager.sign_payload(payload)
    return {
        **device_state,
        "signature": signature,
    }


@router.post("/command")
def update_control_state(
    command: ControlCommand,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "normal_user")),
):
    """إرسال أمر لتغيير الوضع (AUTO/MANUAL) أو تشغيل/إطفاء الضوء (محمي بـ JWT)"""
    if command.mode is None and command.light_state is None:
        raise HTTPException(
            status_code=400,
            detail="You must provide at least 'mode' or 'light_state'."
        )

    if command.mode is not None:
        device_state["mode"] = command.mode
        # لما نرجع لوضع AUTO بنصفر حالة الضوء اليدوية
        if command.mode == "AUTO":
            device_state["light_state"] = False

    if command.light_state is not None:
        if device_state["mode"] != "MANUAL":
            raise HTTPException(
                status_code=400,
                detail="Cannot manually control light while in AUTO mode. Switch to MANUAL first."
            )
        device_state["light_state"] = command.light_state

    device_state["updated_at"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    actor_name = getattr(current_user, "email", None) or getattr(current_user, "username", "dashboard")

    log_security_event(
        db=db,
        event_type="CONTROL_COMMAND",
        severity="INFO",
        actor=actor_name,
        details=f"Mode={device_state['mode']}, Light={'ON' if device_state['light_state'] else 'OFF'}",
    )
    return {
        "message": "Command applied successfully",
        "state": device_state
    }