from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.pqc import b64_decode, decrypt_json, verify_signature
from app.core.pqc_manager import pqc_manager
from app.core.security import require_roles
from app.database import get_db
from app.models import SensorReading, User
from app.schemas import SensorReadingResponse
from app.services.audit_service import log_security_event

router = APIRouter(
    prefix="/api/pqc",
    tags=["Post-Quantum Cryptography (PQC)"],
)

PI_ONLINE_THRESHOLD_SECONDS = 30


class HandshakeRequest(BaseModel):
    device_id: str
    kem_ciphertext: str
    device_dsa_public_key: str


class EncryptedSensorPayload(BaseModel):
    device_id: str
    nonce: str
    ciphertext: str
    signature: str


@router.get("/status")
def get_pqc_and_device_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "normal_user")),
):
    """إرجاع حالة التشفير الكمي (PQC Active) وحالة اتصال Raspberry Pi (online/offline)"""
    pqc_info = pqc_manager.get_pqc_status()

    latest_reading = (
        db.query(SensorReading)
        .order_by(SensorReading.timestamp.desc(), SensorReading.id.desc())
        .first()
    )

    pi_online = False
    last_seen = None
    seconds_since_last = None

    if latest_reading and latest_reading.timestamp:
        ts = latest_reading.timestamp
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        else:
            ts = ts.astimezone(timezone.utc)

        now = datetime.now(timezone.utc)
        seconds_since_last = round(max(0.0, (now - ts).total_seconds()), 1)
        pi_online = seconds_since_last <= PI_ONLINE_THRESHOLD_SECONDS
        last_seen = ts.isoformat().replace("+00:00", "Z")

    return {
        **pqc_info,
        "raspberry_pi": {
            "status": "online" if pi_online else "offline",
            "online": pi_online,
            "last_seen": last_seen,
            "seconds_since_last_reading": seconds_since_last,
        },
    }


@router.get("/public-keys")
def get_pqc_public_keys():
    """إرجاع مفاتيح السيرفر العامة (ML-KEM-768 و ML-DSA-65) لبدء الـ Handshake"""
    return pqc_manager.get_server_public_keys()


@router.post("/handshake")
def pqc_handshake(req: HandshakeRequest):
    """إتمام تبادل المفاتيح (ML-KEM-768) وتسجيل مفتاح التوقيع العام للرازبيري"""
    try:
        return pqc_manager.complete_handshake(
            device_id=req.device_id,
            kem_ciphertext_b64=req.kem_ciphertext,
            device_dsa_public_key_b64=req.device_dsa_public_key,
        )
    except Exception as err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"PQC Handshake failed: {err}",
        )


@router.post(
    "/sensors/readings",
    response_model=SensorReadingResponse,
    status_code=status.HTTP_201_CREATED,
)
def receive_encrypted_sensor_reading(
    payload: EncryptedSensorPayload,
    db: Session = Depends(get_db),
):
    """استقبال قراءات الحساسات مشفّرة (AES-256-GCM) وموقّعة (ML-DSA-65)"""
    session = pqc_manager.get_session(payload.device_id)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No active PQC session. Perform /api/pqc/handshake first.",
        )

    encrypted_envelope = {
        "nonce": payload.nonce,
        "ciphertext": payload.ciphertext,
    }

    # 1. التحقق من توقيع ML-DSA-65 قبل فك التشفير (Verify-then-Decrypt)
    is_valid = verify_signature(
        public_key=session["device_dsa_pk"],
        data=encrypted_envelope,
        signature=b64_decode(payload.signature),
    )
    if not is_valid:
        log_security_event(
            db=db,
            event_type="PQC_TAMPERING_DETECTED",
            severity="CRITICAL",
            actor=payload.device_id,
            details="Invalid ML-DSA-65 (Dilithium) signature — possible MITM tampering attack blocked!",
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid ML-DSA-65 (Dilithium) signature — possible tampering detected!",
        )

    # 2. فك التشفير باستخدام المفتاح المشترك (AES-256-GCM)
    try:
        data = decrypt_json(
            shared_key=session["shared_key"],
            nonce_b64=payload.nonce,
            ciphertext_b64=payload.ciphertext,
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="AES-256-GCM decryption failed",
        )

    # 3. حفظ القراءة في قاعدة البيانات (Neon)
    reading = SensorReading(
        temperature=data.get("temperature"),
        humidity=data.get("humidity"),
        motion=bool(data.get("motion", False)),
    )
    db.add(reading)
    db.commit()
    db.refresh(reading)

    return reading