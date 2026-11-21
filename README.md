# SmartHome-PQC Backend

## 1. Project Overview

**SmartHome-PQC** is a cloud-connected, Post-Quantum Cryptography (PQC) secured IoT Smart Home system built with a **Raspberry Pi 5** gateway, a **FastAPI** backend hosted on **Render**, and a **Neon Serverless PostgreSQL** database.

The system provides real-time environmental monitoring (temperature, humidity, motion), automated and manual actuator control (Relay/LED), strict Role-Based Access Control (RBAC) with admin approval workflows, and end-to-end quantum-resistant communication using **NIST-standardized PQC algorithms**.

- **Production Base URL:** `https://smarthome-pqc-backend.onrender.com`
- **Interactive Swagger Docs:** `https://smarthome-pqc-backend.onrender.com/docs`

---

## 2. Architecture & Technologies Used

- **Backend Framework:** Python 3.14, FastAPI, Uvicorn, Pydantic
- **Database:** Neon Serverless PostgreSQL (SQLAlchemy + `psycopg`)
- **Cloud & Uptime:** Render (CI/CD Auto-Deploy) + UptimeRobot (`/health` `GET`/`HEAD` monitoring)
- **Authentication & Security:** JWT (`PyJWT`), Argon2 password hashing (`argon2-cffi` / `pwdlib`), RBAC
- **Post-Quantum Cryptography (Hybrid Architecture):**
  - **Key Encapsulation:** `ML-KEM-768` (Kyber-768 / NIST FIPS 203) via `kyber-py`
  - **Digital Signatures:** `ML-DSA-65` (Dilithium3 / NIST FIPS 204) via `dilithium-py`
  - **Symmetric Encryption:** `AES-256-GCM` via `cryptography`
- **Hardware Gateway:** Raspberry Pi 5, DHT22 (GPIO4), PIR HC-SR501 (GPIO27), 1-Channel Relay & LED (GPIO17)

---

## 3. Project Structure

```text
SmartHome-PQC-Backend/
├── app/
│   ├── core/
│   │   ├── pqc.py           # ML-KEM-768, ML-DSA-65, AES-256-GCM primitives
│   │   ├── pqc_manager.py   # Server PQC keypairs & device session management
│   │   └── security.py      # Argon2 hashing, JWT tokens, RBAC dependencies
│   ├── routers/
│   │   ├── auth.py          # Login, Pending Registration, Admin User Management
│   │   ├── control.py       # AUTO/MANUAL lighting control endpoints
│   │   ├── devices.py       # Hardware device registry
│   │   ├── pqc.py           # PQC public keys, handshake, encrypted sensor ingestion
│   │   └── sensors.py       # Sensor readings retrieval
│   ├── services/
│   │   └── auth_service.py  # User lookup & authentication logic
│   ├── database.py          # PostgreSQL / SQLite SQLAlchemy engine
│   ├── main.py              # FastAPI app, CORS, /health, router registration
│   ├── models.py            # SQLAlchemy ORM models
│   └── schemas.py           # Pydantic validation & password strength rules
├── demo_tampering.py        # Live MITM tampering attack demonstration script
├── requirements.txt
├── .env.example
└── README.md
```

---

## 4. Security & Authentication (JWT + RBAC)

The system enforces a **Closed-System Security Model**:

- **Pending Approval Workflow:** New users submit a registration request (`POST /api/auth/register`), which creates an inactive `pending` account. An admin must explicitly approve the request (assigning `admin` or `normal_user`) or reject it.
- **Strict Password Policy:** Minimum 8 characters, at least one uppercase letter, one lowercase letter, one number, and one special character.
- **Self-Lockout Protection:** Admins cannot deactivate their own account or downgrade their own role.

### Authentication & User Management Endpoints

| Method | Endpoint | Access | Description |
| :--- | :--- | :--- | :--- |
| `POST` | `/api/auth/register` | Public | Submit a new account request (`role="pending"`) |
| `POST` | `/api/auth/login` | Public | Authenticate and receive a JWT access token |
| `GET` | `/api/auth/me` | Authenticated | Retrieve current user profile |
| `POST` | `/api/auth/change-password` | Authenticated | Update own password |
| `GET` | `/api/auth/users` | Admin Only | List all registered and pending users |
| `POST` | `/api/auth/users` | Admin Only | Directly create an active user |
| `PATCH` | `/api/auth/users/{user_id}/approve` | Admin Only | Approve a pending user and assign role |
| `DELETE` | `/api/auth/users/{user_id}/reject` | Admin Only | Reject and delete a pending request |
| `PATCH` | `/api/auth/users/{user_id}/role` | Admin Only | Switch role (`admin` / `normal_user`) |
| `PATCH` | `/api/auth/users/{user_id}/status` | Admin Only | Activate or deactivate a user account |

---

## 5. Post-Quantum Cryptography (PQC) Protocol

Communication between the **Raspberry Pi 5** and the **Render Backend** uses a **Verify-then-Decrypt** Hybrid PQC pipeline (NIST Security Level 3):

1. **Key Exchange (`GET /api/pqc/public-keys` & `POST /api/pqc/handshake`):**
   The Raspberry Pi encapsulates a 256-bit shared secret using the server's `ML-KEM-768` public key, registers its own `ML-DSA-65` public key, and verifies the server's `ML-DSA-65` handshake signature.
2. **Encrypted Ingestion (`POST /api/pqc/sensors/readings`):**
   Sensor payloads are encrypted with `AES-256-GCM` (unique 96-bit random nonce per packet) and signed with `ML-DSA-65` over Canonical JSON. The server verifies the signature before decrypting; any tampered packet is immediately rejected with `403 Forbidden`.
3. **Observed Performance on Raspberry Pi 5:**
   - Full PQC Handshake (including cloud round-trip): ~1.1s (once at startup)
   - Per-reading Encryption + Dilithium Signing: ~31ms – 77ms

---

## 6. Local Setup & Running

1. Create and activate a virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

2. Install dependencies:

```powershell
pip install -r requirements.txt
```

3. Configure `.env` (see `.env.example` for `SECRET_KEY` and `DATABASE_URL`).

4. Run the server:

```powershell
uvicorn app.main:app --reload
```

5. Run the PQC tampering demonstration:

```powershell
python demo_tampering.py
```