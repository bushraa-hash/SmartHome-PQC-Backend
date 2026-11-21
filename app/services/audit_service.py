from sqlalchemy.orm import Session
from app.models import SecurityLog


def log_security_event(
    db: Session,
    event_type: str,
    details: str,
    severity: str = "INFO",
    actor: str | None = None,
) -> None:
    """حفظ حدث أمني أو تشغيلي في جدول security_logs"""
    entry = SecurityLog(
        event_type=event_type,
        severity=severity,
        actor=actor,
        details=details,
    )
    db.add(entry)
    db.commit()