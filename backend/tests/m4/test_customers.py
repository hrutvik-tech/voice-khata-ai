"""
backend/tests/m4/test_customers.py

Tests for customer and summary API endpoints:
- GET /customers
- POST /customers
- GET /customers/{id}
- GET /summary/today
- Shop isolation and authorization
"""

from fastapi.testclient import TestClient


def _register_shop(client: TestClient, phone="9000000001") -> tuple[str, dict]:
    res = client.post(
        "/auth/register",
        json={"owner_name": "Sharma", "phone": phone, "pin": "1234"},
    )
    assert res.status_code == 201
    return res.json()["token"], res.json()["shop"]


def test_customers_endpoints_require_auth(client: TestClient):
    """Protected customer endpoints return 401 without Bearer token."""
    assert client.get("/customers").status_code == 401
    assert client.post("/customers", json={"name": "Ramesh"}).status_code == 401
    assert client.get("/customers/1").status_code == 401
    assert client.get("/summary/today").status_code == 401


def test_customer_creation_and_listing(client: TestClient):
    token, _ = _register_shop(client, "9200000001")
    headers = {"Authorization": f"Bearer {token}"}

    # Add 2 customers
    c1 = client.post(
        "/customers",
        headers=headers,
        json={"name": "Ramesh Sharma", "phone": "9888888881", "area": "Gandhi Nagar"},
    )
    assert c1.status_code == 201
    assert c1.json()["customer"]["name"] == "Ramesh Sharma"

    c2 = client.post(
        "/customers",
        headers=headers,
        json={"name": "Suresh Gupta", "phone": "9888888882", "area": "Station Road"},
    )
    assert c2.status_code == 201

    # List all
    res = client.get("/customers", headers=headers)
    assert res.status_code == 200
    custs = res.json()
    assert len(custs) == 2
    # Alphabetical sorting when no activity
    assert custs[0]["name"] == "Ramesh Sharma"
    assert custs[1]["name"] == "Suresh Gupta"


def test_customer_search(client: TestClient):
    token, _ = _register_shop(client, "9200000002")
    headers = {"Authorization": f"Bearer {token}"}

    client.post("/customers", headers=headers, json={"name": "Ramesh Sharma", "area": "Gandhi Nagar"})
    client.post("/customers", headers=headers, json={"name": "Suresh Gupta", "area": "Station Road"})

    # Search by name
    res_name = client.get("/customers?search=ramesh", headers=headers)
    assert len(res_name.json()) == 1
    assert res_name.json()[0]["name"] == "Ramesh Sharma"

    # Search by area
    res_area = client.get("/customers?search=station", headers=headers)
    assert len(res_area.json()) == 1
    assert res_area.json()[0]["name"] == "Suresh Gupta"


def test_similar_customer_409_and_confirmation(client: TestClient):
    token, _ = _register_shop(client, "9200000003")
    headers = {"Authorization": f"Bearer {token}"}

    client.post("/customers", headers=headers, json={"name": "Ramesh Sharma", "area": "Market"})

    # Attempt to add similar name "Ramesh Sharm" without confirm -> 409
    res_similar = client.post(
        "/customers",
        headers=headers,
        json={"name": "Ramesh Sharm", "area": "Market", "confirm": False},
    )
    assert res_similar.status_code == 409
    detail = res_similar.json()["detail"]
    assert detail["detail"] == "similar_exists"
    assert len(detail["similar"]) >= 1
    assert detail["similar"][0]["name"] == "Ramesh Sharma"

    # With confirm=True -> succeeds with 201
    res_ok = client.post(
        "/customers",
        headers=headers,
        json={"name": "Ramesh Sharm", "area": "Market", "confirm": True},
    )
    assert res_ok.status_code == 201
    assert res_ok.json()["customer"]["name"] == "Ramesh Sharm"


def test_customer_profile_and_summary_today(client: TestClient):
    token, _ = _register_shop(client, "9200000004")
    headers = {"Authorization": f"Bearer {token}"}

    c_res = client.post("/customers", headers=headers, json={"name": "Amit Kumar"})
    cid = c_res.json()["customer"]["id"]

    # Check profile
    profile = client.get(f"/customers/{cid}", headers=headers)
    assert profile.status_code == 200
    pdata = profile.json()
    assert pdata["customer"]["name"] == "Amit Kumar"
    assert pdata["balance_paise"] == 0
    assert pdata["entries"] == []

    # Check summary today
    summary = client.get("/summary/today", headers=headers)
    assert summary.status_code == 200
    sdata = summary.json()
    assert "business_date" in sdata
    assert sdata["credit_paise"] == 0
    assert sdata["payment_paise"] == 0
    assert sdata["top"] == []


def test_customers_shop_isolation(client: TestClient):
    t1, _ = _register_shop(client, "9200000005")
    t2, _ = _register_shop(client, "9200000006")

    h1 = {"Authorization": f"Bearer {t1}"}
    h2 = {"Authorization": f"Bearer {t2}"}

    c1 = client.post("/customers", headers=h1, json={"name": "Shop 1 Customer"}).json()["customer"]["id"]

    # Shop 2 cannot view Shop 1's customer
    assert client.get(f"/customers/{c1}", headers=h2).status_code == 404

    # Shop 2 listing does not include Shop 1's customer
    s2_list = client.get("/customers", headers=h2).json()
    assert len(s2_list) == 0
