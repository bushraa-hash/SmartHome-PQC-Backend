# SmartHome-PQC Backend

## 1. Project Overview

SmartHome-PQC is a secure IoT Smart Home System designed to monitor and control smart home devices using a Raspberry Pi 5.

The backend is developed using Python and FastAPI. It provides REST API endpoints for managing smart home devices and storing sensor readings.

The project aims to integrate Post-Quantum Cryptography (PQC) to improve the security of communication and commands between the system components.

## 2. Technologies Used

- Python
- FastAPI
- Uvicorn
- SQLAlchemy
- SQLite
- Pydantic
- Pytest
- HTTPX

## 3. Hardware Components

The system is designed to work with the following hardware:

- Raspberry Pi 5
- DHT22 Temperature and Humidity Sensor
- PIR Motion Sensor
- Relay Module
- LED

**Note:** The hardware components are prepared for integration. The current backend version uses manually submitted test readings and does not yet collect readings directly from the physical sensors.

## 4. Project Structure

```text
SmartHome-PQC-Backend/
│
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── database.py
│   ├── models.py
│   ├── schemas.py
│   └── routers/
│       ├── __init__.py
│       ├── devices.py
│       └── sensors.py
│
├── tests/
│   └── test_api.py
│
├── requirements.txt
├── README.md
└── smarthome.db
```

## 5. Database

The project currently uses SQLite with SQLAlchemy.

The database contains the following tables:

### Devices
Stores information about the connected or planned smart home devices.

### Sensor Readings
Stores temperature, humidity, motion status, and reading timestamps.

## 6. API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/` | Check that the backend is running |
| GET | `/health` | Check application health |
| GET | `/api/devices/` | Retrieve all devices |
| GET | `/api/devices/{device_id}` | Retrieve a specific device |
| GET | `/api/sensors/latest` | Retrieve the latest sensor reading |
| GET | `/api/sensors/history` | Retrieve sensor reading history |
| POST | `/api/sensors/readings` | Add a new sensor reading |

## 7. Installation and Setup

### Requirements

- Python 3.11 or later
- pip
- Windows, Linux, or Raspberry Pi OS

### Step 1: Clone or open the project

Open the project folder in Visual Studio Code.

### Step 2: Create a virtual environment

```bash
python -m venv .venv
```

### Step 3: Activate the virtual environment

On Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

### Step 4: Install dependencies

```bash
pip install -r requirements.txt
```

## 8. Running the Backend

Run the following command from the project root directory:

```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

The backend will be available at:

`http://127.0.0.1:8000`

## 9. API Documentation

FastAPI automatically generates interactive API documentation.

Swagger UI:

`http://127.0.0.1:8000/docs`

ReDoc:

`http://127.0.0.1:8000/redoc`

## 10. Running Tests

The project uses Pytest and HTTPX for API testing.

Install the testing dependencies:

```bash
pip install pytest httpx
```

Run the tests:

```bash
pytest -v
```

The tests cover:

- Root endpoint
- Health check
- Retrieving all devices
- Retrieving an existing device
- Handling a nonexistent device
- Creating sensor readings
- Retrieving the latest reading
- Retrieving sensor history
- Rejecting empty sensor readings

Tests use a separate temporary SQLite database to avoid modifying the development database.

## 11. Current Implementation Status

### Implemented

- FastAPI application setup
- SQLite database integration
- SQLAlchemy database models
- Device API endpoints
- Sensor API endpoints
- Manual sensor reading submission
- Sensor reading history
- Initial device records
- API testing setup

### Planned

- User registration and authentication
- JWT-based authentication
- Password hashing
- Role-based access control
- Raspberry Pi GPIO integration
- Real-time sensor data collection
- MQTT communication
- Device control through physical hardware
- ML-KEM post-quantum key establishment
- ML-DSA digital signatures
- AES-GCM data encryption
- Security logs and command history

## 12. Project Goal

The main goal is to develop a smart home system that combines IoT hardware, backend development, and Post-Quantum Cryptography to provide secure monitoring and control of smart home devices.

---

**Project:** SmartHome-PQC  
**Backend Framework:** FastAPI  
**Database:** SQLite  
**Programming Language:** Python
## Authentication and Authorization

The system supports secure user authentication using JWT.

### Supported Roles

- Admin
- Normal User
- Guest

### Security Features

- Password hashing using Argon2.
- JWT access tokens.
- Token expiration.
- Protected API endpoints.
- Role-based access control.
- Admin-only user management.

### Authentication Endpoints

- POST /api/auth/register
- POST /api/auth/login
- GET /api/auth/me
- GET /api/auth/users
- PATCH /api/auth/users/{user_id}/role