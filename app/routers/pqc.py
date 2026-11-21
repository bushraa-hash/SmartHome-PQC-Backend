from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.pqc import b64_decode, decrypt_json, verify_signature
from app.core.pqc_manager import pqc_manager
from app.database import get_db
from app.models import SensorReading
from app.schemas import SensorReadingResponse

router = APIRouter(
    prefix="/api/pqc",
    tags=["Post-Quantum Cryptography (PQC)"],
)


class HandshakeRequest(BaseModel):
    device_id: str
    kem_ciphertext: str
    device_dsa_public_key: str


class EncryptedSensorPayload(BaseModel):
    device_id: str
    nonce: str
    ciphertext: str
    signature: str


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

    # 1. التحقق من توقيع Dilithium قبل فك التشفير (Verify-then-Decrypt)
    is_valid = verify_signature(
        public_key=session["device_dsa_pk"],
        data=encrypted_envelope,
        signature=b64_decode(payload.signature),
    )
    if not is_valid:
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