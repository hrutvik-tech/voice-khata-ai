"""
backend/tests/m4/conftest.py

Test fixtures for Member 4 authentication, shop, customer, ledger, ws, debug, sync, and me API tests.
Configures an isolated SQLite test database and test JWT environment.
"""

import os
import pytest
from pathlib import Path
from fastapi.testclient import TestClient

from app.main import app
from app.api.auth import router as auth_router
from app.api.shop import router as shop_router
from app.api.customers import router as customers_router
from app.api.summary import router as summary_router
from app.api.ws import router as ws_router
from app.api.debug import router as debug_router
from app.api.sync import router as sync_router
from app.api.me import router as me_router

# Ensure routers are registered on the FastAPI app
if not any(r.path.startswith("/auth") for r in app.routes):
    app.include_router(auth_router)
if not any(r.path.startswith("/shop") for r in app.routes):
    app.include_router(shop_router)
if not any(r.path.startswith("/customers") for r in app.routes):
    app.include_router(customers_router)
if not any(r.path.startswith("/summary") for r in app.routes):
    app.include_router(summary_router)
if not any(getattr(r, "path", "").startswith("/ws") for r in app.routes):
    app.include_router(ws_router)
if not any(r.path.startswith("/debug") for r in app.routes):
    app.include_router(debug_router)
if not any(r.path.startswith("/sync") for r in app.routes):
    app.include_router(sync_router)
if not any(r.path == "/me" for r in app.routes):
    app.include_router(me_router)


@pytest.fixture(autouse=True)
def setup_test_environment(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """
    Ensures an isolated test database is configured before any database access.
    Sets test environment variables so development database is never touched.
    """
    test_db = tmp_path / "test_khata.db"
    monkeypatch.setenv("DATABASE_PATH", str(test_db))
    monkeypatch.setenv("JWT_SECRET", "test-secret-key-32-chars-long-bolta-khata-m4")
    monkeypatch.setenv("JWT_EXPIRE_DAYS", "30")
    monkeypatch.setenv("DEBUG", "true")

    from app.database.db import get_connection
    from app.core.tokens import ensure_db_tables

    conn = get_connection()
    ensure_db_tables(conn)
    conn.close()

    yield


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)
