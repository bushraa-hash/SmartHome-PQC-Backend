import base64
import json
import os
from typing import Any

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from dilithium_py.ml_dsa import ML_DSA_65
from kyber_py.ml_kem import ML_KEM_768


# ==========================================
# Base64 Helpers (for JSON transport)
# ==========================================
def b64_encode(data: bytes) -> str:
    return base64.b64encode(data).decode("utf-8")


def b64_decode(data_str: str) -> bytes:
    return base64.b64decode(data_str.encode("utf-8"))


# ==========================================
# 1. ML-KEM-768 (Kyber) - Key Encapsulation
# ==========================================
def generate_kem_keypair() -> tuple[bytes, bytes]:
    """يولّد زوج مفاتيح Kyber: (encapsulation_key / public, decapsulation_key / private)"""
    ek, dk = ML_KEM_768.keygen()
    return ek, dk


def kem_encapsulate(public_key: bytes) -> tuple[bytes, bytes]:
    """
    يستخدمها الطرف المرسل (الرازبيري) مع المفتاح العام للسيرفر
    لإنتاج: (shared_secret_32_bytes, ciphertext)
    """
    shared_key, ciphertext = ML_KEM_768.encaps(public_key)
    return shared_key, ciphertext


def kem_decapsulate(private_key: bytes, ciphertext: bytes) -> bytes:
    """
    يستخدمها السيرفر مع مفتاحه الخاص لاستخراج نفس الـ shared_secret (32 bytes)
    """
    return ML_KEM_768.decaps(private_key, ciphertext)


# ==========================================
# 2. ML-DSA-65 (Dilithium) - Digital Signatures
# ==========================================
def generate_dsa_keypair() -> tuple[bytes, bytes]:
    """يولّد زوج مفاتيح Dilithium: (public_key, private_key)"""
    pk, sk = ML_DSA_65.keygen()
    return pk, sk


def _canonical_bytes(data: dict[str, Any] | bytes) -> bytes:
    """تحويل البيانات لبايتات ثابتة ومرتبة قبل التوقيع أو التحقق"""
    if isinstance(data, bytes):
        return data
    return json.dumps(data, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sign_data(private_key: bytes, data: dict[str, Any] | bytes) -> bytes:
    """توقيع البيانات بمفتاح Dilithium الخاص"""
    message = _canonical_bytes(data)
    return ML_DSA_65.sign(private_key, message)


def verify_signature(
    public_key: bytes,
    data: dict[str, Any] | bytes,
    signature: bytes,
) -> bool:
    """التحقق من صحة التوقيع بمفتاح Dilithium العام"""
    message = _canonical_bytes(data)
    try:
        return bool(ML_DSA_65.verify(public_key, message, signature))
    except Exception:
        return False


# ==========================================
# 3. AES-256-GCM - Hybrid Symmetric Encryption
# ==========================================
def encrypt_json(shared_key: bytes, payload: dict[str, Any]) -> dict[str, str]:
    """
    تشفير قاموس JSON باستخدام مفتاح Kyber المشترك (32 bytes)
    ويرجع nonce و ciphertext بصيغة Base64
    """
    aesgcm = AESGCM(shared_key)
    nonce = os.urandom(12)  # 96-bit nonce (معيار GCM)
    plaintext = json.dumps(payload, sort_keys=True).encode("utf-8")
    ciphertext = aesgcm.encrypt(nonce, plaintext, None)
    return {
        "nonce": b64_encode(nonce),
        "ciphertext": b64_encode(ciphertext),
    }


def decrypt_json(shared_key: bytes, nonce_b64: str, ciphertext_b64: str) -> dict[str, Any]:
    """فك تشفير البيانات واسترجاع قاموس JSON الأصلي"""
    aesgcm = AESGCM(shared_key)
    nonce = b64_decode(nonce_b64)
    ciphertext = b64_decode(ciphertext_b64)
    plaintext = aesgcm.decrypt(nonce, ciphertext, None)
    return json.loads(plaintext.decode("utf-8"))