from datetime import datetime
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict, field_serializer
from sqlalchemy.orm import Session

from app.core.security import require_roles
from app.database import get_db
from app.models import SecurityLog, User
from app.schemas import _format_utc_z

router = APIRouter(
    prefix="/api/logs",
    tags=["Security & Audit Logs"],
)


class SecurityLogResponse(BaseModel):
    id: int
    event_type: str
    severity: str
    actor: str | None
    details: str
    timestamp: datetime

    @field_serializer("timestamp")
    def serialize_timestamp(self, value: datetime) -> str:
        return _format_utc_z(value)

    model_config = ConfigDict(from_attributes=True)


@router.get("/", response_model=list[SecurityLogResponse])
def get_security_logs(
    limit: int = Query(default=50, ge=1, le=200),
    severity: str | None = Query(default=None),
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_roles("admin")),
):
    """عرض أحدث سجلات الأمان والتدقيق (للأدمن فقط)"""
    query = db.query(SecurityLog)
    if severity:
        query = query.filter(SecurityLog.severity == severity.upper())
    return query.order_by(SecurityLog.id.desc()).limit(limit).all()