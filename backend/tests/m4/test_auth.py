"""
backend/tests/m4/test_auth.py

Tests for authentication endpoints:
- POST /auth/register
- POST /auth/login
- PUT /auth/pin
"""

import pytest
from fastapi.testclient import TestClient


def test_register_success(client: TestClient):
    """Register creates shop with contract defaults and returns 201 {"token", "shop"}."""
    payload = {
        "owner_name": "Sharma",
        "phone": "9000000001",
        "pin": "1234",
    }
    response = client.post("/auth/register", json=payload)
    assert response.status_code == 201

    data = response.json()
    assert "token" in data and isinstance(data["token"], str)
    assert "shop" in data

    shop = data["shop"]
    assert shop["owner_name"] == "Sharma"
    assert shop["shop_name"] == ""
    assert shop["phone"] == "9000000001"
    assert shop["open_time"] == "06:00"
    assert shop["close_time"] == "02:00"
    assert shop["timezone"] == "Asia/Kolkata"
    assert shop["language_mode"] == "mix"
    assert shop["setup_complete"] is False
    assert "id" in shop
    # Ensure PIN hash or internal credentials are never exposed
    assert "pin_hash" not in shop
    assert "pin" not in shop


def test_register_duplicate_phone(client: TestClient):
    """Registering with an already registered phone returns 409 {"detail": "phone_exists"}."""
    payload = {
        "owner_name": "Sharma",
        "phone": "9000000001",
        "pin": "1234",
    }
    first_res = client.post("/auth/register", json=payload)
    assert first_res.status_code == 201

    second_res = client.post("/auth/register", json=payload)
    assert second_res.status_code == 409
    assert second_res.json() == {"detail": "phone_exists"}


@pytest.mark.parametrize(
    "invalid_payload",
    [
        {"owner_name": "", "phone": "9000000001", "pin": "1234"},  # empty name
        {"owner_name": " " * 10, "phone": "9000000001", "pin": "1234"},  # whitespace only
        {"owner_name": "A" * 61, "phone": "9000000001", "pin": "1234"},  # > 60 chars
        {"owner_name": "Valid", "phone": "12345", "pin": "1234"},  # phone not 10 digits
        {"owner_name": "Valid", "phone": "90000000001", "pin": "1234"},  # phone 11 digits
        {"owner_name": "Valid", "phone": "900000000a", "pin": "1234"},  # non-digit phone
        {"owner_name": "Valid", "phone": "9000000001", "pin": "12"},  # pin < 4 digits
        {"owner_name": "Valid", "phone": "9000000001", "pin": "1234567"},  # pin > 6 digits
        {"owner_name": "Valid", "phone": "9000000001", "pin": "abcd"},  # non-digit pin
    ],
)
def test_register_validation_errors(client: TestClient, invalid_payload: dict):
    """Invalid register payloads return 422 Unprocessable Entity."""
    response = client.post("/auth/register", json=invalid_payload)
    assert response.status_code == 422


def test_login_success(client: TestClient):
    """Login with registered phone and correct PIN returns 200 {"token", "shop"}."""
    reg = client.post(
        "/auth/register",
        json={"owner_name": "Sharma", "phone": "9000000001", "pin": "1234"},
    )
    assert reg.status_code == 201

    response = client.post("/auth/login", json={"phone": "9000000001", "pin": "1234"})
    assert response.status_code == 200
    data = response.json()
    assert "token" in data and isinstance(data["token"], str)
    assert data["shop"]["phone"] == "9000000001"
    assert "pin_hash" not in data["shop"]


def test_login_unknown_phone(client: TestClient):
    """Login with unknown phone returns 401 {"detail": "wrong_pin"}."""
    response = client.post("/auth/login", json={"phone": "9999999999", "pin": "1234"})
    assert response.status_code == 401
    assert response.json() == {"detail": "wrong_pin"}


def test_login_wrong_pin(client: TestClient):
    """Login with wrong PIN returns 401 {"detail": "wrong_pin"} (same as unknown phone)."""
    client.post(
        "/auth/register",
        json={"owner_name": "Sharma", "phone": "9000000001", "pin": "1234"},
    )
    response = client.post("/auth/login", json={"phone": "9000000001", "pin": "9999"})
    assert response.status_code == 401
    assert response.json() == {"detail": "wrong_pin"}


def test_change_pin_success(client: TestClient):
    """PUT /auth/pin changes the PIN, returns 204, and allows login with new PIN."""
    reg = client.post(
        "/auth/register",
        json={"owner_name": "Sharma", "phone": "9000000001", "pin": "1234"},
    )
    token = reg.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Change PIN
    response = client.put(
        "/auth/pin",
        headers=headers,
        json={"old_pin": "1234", "new_pin": "56789"},
    )
    assert response.status_code == 204

    # Old PIN should fail
    old_login = client.post("/auth/login", json={"phone": "9000000001", "pin": "1234"})
    assert old_login.status_code == 401
    assert old_login.json() == {"detail": "wrong_pin"}

    # New PIN should succeed
    new_login = client.post("/auth/login", json={"phone": "9000000001", "pin": "56789"})
    assert new_login.status_code == 200


def test_change_pin_wrong_old_pin(client: TestClient):
    """PUT /auth/pin with wrong old_pin returns 401 {"detail": "wrong_pin"}."""
    reg = client.post(
        "/auth/register",
        json={"owner_name": "Sharma", "phone": "9000000001", "pin": "1234"},
    )
    token = reg.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    response = client.put(
        "/auth/pin",
        headers=headers,
        json={"old_pin": "0000", "new_pin": "5678"},
    )
    assert response.status_code == 401
    assert response.json() == {"detail": "wrong_pin"}


@pytest.mark.parametrize(
    "invalid_payload",
    [
        {"old_pin": "1234", "new_pin": "12"},  # new_pin < 4 digits
        {"old_pin": "1234", "new_pin": "1234567"},  # new_pin > 6 digits
        {"old_pin": "1234", "new_pin": "abcd"},  # new_pin non-numeric
    ],
)
def test_change_pin_validation_error(client: TestClient, invalid_payload: dict):
    """PUT /auth/pin with invalid new_pin returns 422."""
    reg = client.post(
        "/auth/register",
        json={"owner_name": "Sharma", "phone": "9000000001", "pin": "1234"},
    )
    token = reg.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    response = client.put("/auth/pin", headers=headers, json=invalid_payload)
    assert response.status_code == 422


def test_change_pin_without_token(client: TestClient):
    """PUT /auth/pin without Authorization header returns 401."""
    response = client.put(
        "/auth/pin",
        json={"old_pin": "1234", "new_pin": "5678"},
    )
    assert response.status_code == 401
