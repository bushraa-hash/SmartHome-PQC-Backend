from app.core.pqc import (
    b64_decode,
    b64_encode,
    generate_dsa_keypair,
    generate_kem_keypair,
    kem_decapsulate,
    sign_data,
)


class PQCManager:
    """
    يدير مفاتيح السيرفر (ML-KEM-768 و ML-DSA-65) وجلسات الأجهزة (Raspberry Pi).
    يتم توليد مفاتيح السيرفر مرة واحدة عند تشغيل الباك إند.
    """

    def __init__(self):
        self.server_kem_ek, self.server_kem_dk = generate_kem_keypair()
        self.server_dsa_pk, self.server_dsa_sk = generate_dsa_keypair()
        # تخزين جلسات الأجهزة: { device_id: {"shared_key": bytes, "device_dsa_pk": bytes} }
        self.sessions: dict[str, dict[str, bytes]] = {}

    def get_server_public_keys(self) -> dict[str, str]:
        return {
            "kem_algorithm": "ML-KEM-768 (NIST FIPS 203)",
            "dsa_algorithm": "ML-DSA-65 (NIST FIPS 204)",
            "server_kem_public_key": b64_encode(self.server_kem_ek),
            "server_dsa_public_key": b64_encode(self.server_dsa_pk),
        }

    def complete_handshake(
        self,
        device_id: str,
        kem_ciphertext_b64: str,
        device_dsa_public_key_b64: str,
    ) -> dict[str, str]:
        ciphertext = b64_decode(kem_ciphertext_b64)
        device_dsa_pk = b64_decode(device_dsa_public_key_b64)

        # استخراج المفتاح المشترك (32 بايت) باستخدام مفتاح Kyber الخاص بالسيرفر
        shared_key = kem_decapsulate(self.server_kem_dk, ciphertext)

        self.sessions[device_id] = {
            "shared_key": shared_key,
            "device_dsa_pk": device_dsa_pk,
        }

        confirmation = {
            "status": "handshake_complete",
            "device_id": device_id,
        }
        server_sig = sign_data(self.server_dsa_sk, confirmation)

        return {
            **confirmation,
            "server_signature": b64_encode(server_sig),
        }

    def get_session(self, device_id: str) -> dict[str, bytes] | None:
        return self.sessions.get(device_id)

    def sign_payload(self, payload: dict) -> str:
        """توقيع أي قاموس بيانات بمفتاح السيرفر الخاص (ML-DSA-65) وإرجاعه بصيغة Base64"""
        sig = sign_data(self.server_dsa_sk, payload)
        return b64_encode(sig)


# نسخة واحدة مشتركة على مستوى التطبيق
pqc_manager = PQCManager()