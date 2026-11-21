"""
backend/tests/m4/test_shop.py

Tests for shop endpoints:
- GET /shop
- PUT /shop
"""

import pytest
from fastapi.testclient import TestClient


def test_get_shop_success(client: TestClient):
    """GET /shop returns the shop object matching docs/contracts.md."""
    reg = client.post(
        "/auth/register",
        json={"owner_name": "Sharma", "phone": "9000000001", "pin": "1234"},
    )
    token = reg.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    response = client.get("/shop", headers=headers)
    assert response.status_code == 200

    shop = response.json()
    assert shop["id"] == reg.json()["shop"]["id"]
    assert shop["owner_name"] == "Sharma"
    assert shop["shop_name"] == ""
    assert shop["phone"] == "9000000001"
    assert shop["open_time"] == "06:00"
    assert shop["close_time"] == "02:00"
    assert shop["timezone"] == "Asia/Kolkata"
    assert shop["language_mode"] == "mix"
    assert shop["setup_complete"] is False

    # Ensure no credentials or hash leak
    assert "pin_hash" not in shop
    assert "pin" not in shop


def test_get_shop_without_token(client: TestClient):
    """GET /shop without token returns 401."""
    response = client.get("/shop")
    assert response.status_code == 401


def test_put_shop_success(client: TestClient):
    """PUT /shop updates fields, sets setup_complete=True, and returns updated shop."""
    reg = client.post(
        "/auth/register",
        json={"owner_name": "Sharma", "phone": "9000000001", "pin": "1234"},
    )
    token = reg.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    update_payload = {
        "shop_name": "Sharma Kirana Store",
        "open_time": "07:30",
        "close_time": "22:45",
        "language_mode": "hi",
    }
    response = client.put("/shop", headers=headers, json=update_payload)
    assert response.status_code == 200

    updated = response.json()
    assert updated["shop_name"] == "Sharma Kirana Store"
    assert updated["open_time"] == "07:30"
    assert updated["close_time"] == "22:45"
    assert updated["language_mode"] == "hi"
    assert updated["setup_complete"] is True
    assert updated["phone"] == "9000000001"
    assert "pin_hash" not in updated

    # Re-fetch via GET to verify persistence
    get_res = client.get("/shop", headers=headers)
    assert get_res.status_code == 200
    assert get_res.json() == updated


def test_put_shop_without_token(client: TestClient):
    """PUT /shop without token returns 401."""
    response = client.put(
        "/shop",
        json={
            "shop_name": "Sharma Kirana Store",
            "open_time": "06:00",
            "close_time": "22:00",
            "language_mode": "hi",
        },
    )
    assert response.status_code == 401


@pytest.mark.parametrize(
    "invalid_payload",
    [
        # empty shop_name
        {"shop_name": "", "open_time": "06:00", "close_time": "22:00", "language_mode": "hi"},
        # whitespace only shop_name
        {"shop_name": "   ", "open_time": "06:00", "close_time": "22:00", "language_mode": "hi"},
        # shop_name > 80 chars
        {"shop_name": "S" * 81, "open_time": "06:00", "close_time": "22:00", "language_mode": "hi"},
        # invalid open_time hour
        {"shop_name": "Valid", "open_time": "25:00", "close_time": "22:00", "language_mode": "hi"},
        # invalid open_time minute
        {"shop_name": "Valid", "open_time": "06:60", "close_time": "22:00", "language_mode": "hi"},
        # open_time not HH:MM
        {"shop_name": "Valid", "open_time": "6:00", "close_time": "22:00", "language_mode": "hi"},
        # invalid close_time
        {"shop_name": "Valid", "open_time": "06:00", "close_time": "midnight", "language_mode": "hi"},
        # open_time equals close_time
        {"shop_name": "Valid", "open_time": "06:00", "close_time": "06:00", "language_mode": "hi"},
        # invalid language_mode
        {"shop_name": "Valid", "open_time": "06:00", "close_time": "22:00", "language_mode": "bengali"},
    ],
)
def test_put_shop_validation_errors(client: TestClient, invalid_payload: dict):
    """Invalid PUT /shop payloads return 422 Unprocessable Entity."""
    reg = client.post(
        "/auth/register",
        json={"owner_name": "Sharma", "phone": "9000000001", "pin": "1234"},
    )
    token = reg.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    response = client.put("/shop", headers=headers, json=invalid_payload)
    assert response.status_code == 422


def test_protected_routes_without_token(client: TestClient):
    """
    Explicitly tests all 3 protected routes without a token:
    GET /shop, PUT /shop, and PUT /auth/pin.
    All must return 401.
    """
    # 1. GET /shop
    res_get_shop = client.get("/shop")
    assert res_get_shop.status_code == 401

    # 2. PUT /shop
    res_put_shop = client.put(
        "/shop",
        json={
            "shop_name": "Store",
            "open_time": "08:00",
            "close_time": "20:00",
            "language_mode": "en",
        },
    )
    assert res_put_shop.status_code == 401

    # 3. PUT /auth/pin
    res_put_pin = client.put(
        "/auth/pin",
        json={"old_pin": "1234", "new_pin": "5678"},
    )
    assert res_put_pin.status_code == 401
