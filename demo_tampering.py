import requests
from app.core.pqc import (
    b64_decode,
    b64_encode,
    encrypt_json,
    generate_dsa_keypair,
    kem_encapsulate,
    sign_data,
)

BACKEND_URL = "https://smarthome-pqc-backend.onrender.com"
DEVICE_ID = "demo-attacker-test"

print("=== SmartHome-PQC Tampering Attack Demo ===\n")

# 1. PQC Handshake
print("[1] Performing ML-KEM-768 Handshake with Render Backend...")
keys = requests.get(f"{BACKEND_URL}/api/pqc/public-keys", timeout=10).json()
server_kem_ek = b64_decode(keys["server_kem_public_key"])

shared_key, kem_ct = kem_encapsulate(server_kem_ek)
dev_pk, dev_sk = generate_dsa_keypair()

hs_resp = requests.post(
    f"{BACKEND_URL}/api/pqc/handshake",
    json={
        "device_id": DEVICE_ID,
        "kem_ciphertext": b64_encode(kem_ct),
        "device_dsa_public_key": b64_encode(dev_pk),
    },
    timeout=10,
)
print(f"    Handshake Status: {hs_resp.status_code} OK\n")

# 2. Send a LEGITIMATE encrypted & signed reading
print("[2] Sending LEGITIMATE encrypted (AES-256-GCM) & signed (ML-DSA-65) reading...")
legit_data = {"temperature": 24.5, "humidity": 50.0, "motion": False}
envelope = encrypt_json(shared_key, legit_data)
signature = sign_data(dev_sk, envelope)

valid_resp = requests.post(
    f"{BACKEND_URL}/api/pqc/sensors/readings",
    json={
        "device_id": DEVICE_ID,
        "nonce": envelope["nonce"],
        "ciphertext": envelope["ciphertext"],
        "signature": b64_encode(signature),
    },
    timeout=10,
)
print(f"    Server Response: {valid_resp.status_code} -> ACCEPTED!\n")

# 3. Simulate TAMPERING ATTACK (modify ciphertext in transit)
print("[3] Simulating MITM TAMPERING ATTACK (altering 1 character of ciphertext)...")
tampered_ct = envelope["ciphertext"][:-2] + ("AA" if not envelope["ciphertext"].endswith("AA") else "BB")

attack_resp = requests.post(
    f"{BACKEND_URL}/api/pqc/sensors/readings",
    json={
        "device_id": DEVICE_ID,
        "nonce": envelope["nonce"],
        "ciphertext": tampered_ct,
        "signature": b64_encode(signature),
    },
    timeout=10,
)
print(f"    Server Response: {attack_resp.status_code} -> REJECTED!")
print(f"    Server Detail  : {attack_resp.json().get('detail')}\n")