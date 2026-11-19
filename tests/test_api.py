

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.database import Base, get_db
from app.models import Device, User
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
)


# ==========================================
# 1. Test Database Configuration
# ==========================================

TEST_DATABASE_URL = "sqlite://"

test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestingSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=test_engine,
)


# ==========================================
# 2. Test Client Fixture
# ==========================================

@pytest.fixture
def client():

    Base.metadata.drop_all(bind=test_engine)
    Base.metadata.create_all(bind=test_engine)

    db = TestingSessionLocal()

    try:
        devices = [
            Device(
                component_name="DHT22 Temperature and Humidity Sensor",
                component_type="sensor",
                gpio_pin=4,
                status="ready",
            ),
            Device(
                component_name="PIR Motion Sensor",
                component_type="sensor",
                gpio_pin=27,
                status="ready",
            ),
            Device(
                component_name="1-Channel Relay",
                component_type="actuator",
                gpio_pin=17,
                status="ready",
            ),
            Device(
                component_name="Smart Light LED",
                component_type="actuator",
                gpio_pin=22,
                status="ready",
            ),
        ]

        db.add_all(devices)
        db.commit()

    finally:
        db.close()

    def override_get_db():
        test_db = TestingSessionLocal()

        try:
            yield test_db
        finally:
            test_db.close()

    app.dependency_overrides[get_db] = override_get_db

    test_client = TestClient(app)

    try:
        yield test_client

    finally:
        test_client.close()
        app.dependency_overrides.clear()
        Base.metadata.drop_all(bind=test_engine)


# ==========================================
# 3. Test Users Fixture
# ==========================================

@pytest.fixture
def auth_users(client):

    db = TestingSessionLocal()

    admin = User(
        full_name="Test Admin",
        email="admin@test.com",
        hashed_password=hash_password("AdminPass123!"),
        role="admin",
        is_active=True,
    )

    normal_user = User(
        full_name="Test User",
        email="user@test.com",
        hashed_password=hash_password("UserPass123!"),
        role="normal_user",
        is_active=True,
    )

    guest = User(
        full_name="Test Guest",
        email="guest@test.com",
        hashed_password=hash_password("GuestPass123!"),
        role="guest",
        is_active=True,
    )

    inactive_user = User(
        full_name="Inactive User",
        email="inactive@test.com",
        hashed_password=hash_password("InactivePass123!"),
        role="normal_user",
        is_active=False,
    )

    db.add_all([
        admin,
        normal_user,
        guest,
        inactive_user,
    ])

    db.commit()

    db.refresh(admin)
    db.refresh(normal_user)
    db.refresh(guest)
    db.refresh(inactive_user)

    admin_token = create_access_token(admin.id)
    user_token = create_access_token(normal_user.id)
    guest_token = create_access_token(guest.id)
    inactive_token = create_access_token(inactive_user.id)

    result = {
        "admin": admin,
        "user": normal_user,
        "guest": guest,
        "inactive": inactive_user,

        "admin_headers": {
            "Authorization": f"Bearer {admin_token}"
        },

        "user_headers": {
            "Authorization": f"Bearer {user_token}"
        },

        "guest_headers": {
            "Authorization": f"Bearer {guest_token}"
        },

        "inactive_headers": {
            "Authorization": f"Bearer {inactive_token}"
        },
    }

    db.close()

    return result


# ==========================================
# 4. Root and Health Tests
# ==========================================

def test_root_endpoint(client):

    response = client.get("/")

    assert response.status_code == 200
    assert response.json()["message"] == (
        "SmartHome-PQC Backend is running"
    )


def test_health_endpoint(client):

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


# ==========================================
# 5. Device Tests
# ==========================================

def test_get_all_devices(client, auth_users):

    response = client.get(
        "/api/devices/",
        headers=auth_users["user_headers"],
    )

    assert response.status_code == 200
    assert len(response.json()) == 4


def test_get_existing_device(client, auth_users):

    response = client.get(
        "/api/devices/1",
        headers=auth_users["user_headers"],
    )

    assert response.status_code == 200
    assert response.json()["id"] == 1


def test_get_nonexistent_device(client, auth_users):

    response = client.get(
        "/api/devices/999",
        headers=auth_users["user_headers"],
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Device not found"


def test_devices_reject_missing_token(client):

    response = client.get("/api/devices/")

    assert response.status_code == 401


# ==========================================
# 6. Sensor Tests
# ==========================================

def test_create_sensor_reading(client):

    reading = {
        "temperature": 24.5,
        "humidity": 55.0,
        "motion": True,
    }

    response = client.post(
        "/api/sensors/readings",
        json=reading,
    )

    assert response.status_code == 201
    assert response.json()["temperature"] == 24.5
    assert response.json()["humidity"] == 55.0
    assert response.json()["motion"] is True


def test_get_latest_sensor_reading(client, auth_users):

    reading = {
        "temperature": 27.2,
        "humidity": 61.5,
        "motion": False,
    }

    client.post(
        "/api/sensors/readings",
        json=reading,
    )

    response = client.get(
        "/api/sensors/latest",
        headers=auth_users["user_headers"],
    )

    assert response.status_code == 200
    assert response.json()["temperature"] == 27.2
    assert response.json()["humidity"] == 61.5


def test_get_sensor_history(client, auth_users):

    first_reading = {
        "temperature": 24.5,
        "humidity": 55.0,
        "motion": True,
    }

    second_reading = {
        "temperature": 27.2,
        "humidity": 61.5,
        "motion": False,
    }

    client.post("/api/sensors/readings", json=first_reading)
    client.post("/api/sensors/readings", json=second_reading)

    response = client.get(
        "/api/sensors/history",
        headers=auth_users["user_headers"],
    )

    assert response.status_code == 200
    assert len(response.json()) == 2


def test_reject_empty_sensor_reading(client):

    reading = {
        "temperature": None,
        "humidity": None,
        "motion": False,
    }

    response = client.post(
        "/api/sensors/readings",
        json=reading,
    )

    assert response.status_code == 400


def test_sensor_latest_rejects_missing_token(client):

    response = client.get("/api/sensors/latest")

    assert response.status_code == 401


def test_sensor_history_rejects_missing_token(client):

    response = client.get("/api/sensors/history")

    assert response.status_code == 401


# ==========================================
# 7. User Registration Tests
# ==========================================

def test_user_registration(client):

    user_data = {
        "full_name": "New Test User",
        "email": "newuser@test.com",
        "password": "NewPassword123!",
    }

    response = client.post(
        "/api/auth/register",
        json=user_data,
    )

    assert response.status_code == 201

    result = response.json()

    assert result["full_name"] == "New Test User"
    assert result["email"] == "newuser@test.com"
    assert result["role"] == "normal_user"

    assert "password" not in result
    assert "hashed_password" not in result


def test_user_registration_duplicate_email(client):

    user_data = {
        "full_name": "First User",
        "email": "duplicate@test.com",
        "password": "Password123!",
    }

    first_response = client.post(
        "/api/auth/register",
        json=user_data,
    )

    second_response = client.post(
        "/api/auth/register",
        json=user_data,
    )

    assert first_response.status_code == 201
    assert second_response.status_code == 409


def test_registered_password_is_hashed(client):

    user_data = {
        "full_name": "Password Test",
        "email": "password@test.com",
        "password": "MySecret123!",
    }

    response = client.post(
        "/api/auth/register",
        json=user_data,
    )

    assert response.status_code == 201

    db = TestingSessionLocal()

    try:
        user = db.query(User).filter(
            User.email == "password@test.com"
        ).first()

        assert user is not None
        assert user.hashed_password != "MySecret123!"
        assert verify_password(
            "MySecret123!",
            user.hashed_password,
        ) is True

    finally:
        db.close()


# ==========================================
# 8. Login Tests
# ==========================================

def test_login_success(client):

    client.post(
        "/api/auth/register",
        json={
            "full_name": "Login User",
            "email": "login@test.com",
            "password": "LoginPass123!",
        },
    )

    response = client.post(
        "/api/auth/login",
        json={
            "email": "login@test.com",
            "password": "LoginPass123!",
        },
    )

    assert response.status_code == 200
    assert "access_token" in response.json()
    assert response.json()["token_type"] == "bearer"


def test_login_wrong_password(client):

    client.post(
        "/api/auth/register",
        json={
            "full_name": "Login User",
            "email": "wrongpass@test.com",
            "password": "CorrectPass123!",
        },
    )

    response = client.post(
        "/api/auth/login",
        json={
            "email": "wrongpass@test.com",
            "password": "WrongPass123!",
        },
    )

    assert response.status_code == 401


def test_login_unknown_email(client):

    response = client.post(
        "/api/auth/login",
        json={
            "email": "unknown@test.com",
            "password": "Password123!",
        },
    )

    assert response.status_code == 401


# ==========================================
# 9. Current User Tests
# ==========================================

def test_get_current_user_profile(client, auth_users):

    response = client.get(
        "/api/auth/me",
        headers=auth_users["user_headers"],
    )

    assert response.status_code == 200
    assert response.json()["email"] == "user@test.com"


def test_profile_rejects_missing_token(client):

    response = client.get("/api/auth/me")

    assert response.status_code == 401


def test_profile_rejects_invalid_token(client):

    response = client.get(
        "/api/auth/me",
        headers={
            "Authorization": "Bearer invalid.token.value"
        },
    )

    assert response.status_code == 401


def test_inactive_user_cannot_access_profile(client, auth_users):

    response = client.get(
        "/api/auth/me",
        headers=auth_users["inactive_headers"],
    )

    assert response.status_code == 401


# ==========================================
# 10. Role-Based Authorization Tests
# ==========================================

def test_admin_can_get_all_users(client, auth_users):

    response = client.get(
        "/api/auth/users",
        headers=auth_users["admin_headers"],
    )

    assert response.status_code == 200
    assert len(response.json()) == 4


def test_normal_user_cannot_get_all_users(client, auth_users):

    response = client.get(
        "/api/auth/users",
        headers=auth_users["user_headers"],
    )

    assert response.status_code == 403


def test_guest_cannot_get_all_users(client, auth_users):

    response = client.get(
        "/api/auth/users",
        headers=auth_users["guest_headers"],
    )

    assert response.status_code == 403


def test_users_endpoint_rejects_missing_token(client):

    response = client.get("/api/auth/users")

    assert response.status_code == 401
