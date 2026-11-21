"""
tests/backend/test_health.py

Tests for GET /api/health.
Uses FastAPI's TestClient (backed by httpx) — no live server needed.
"""

import sys
import os

# Allow importing from backend/app without installing the package
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "backend"))

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health_returns_200():
    """Health endpoint must respond with HTTP 200."""
    response = client.get("/api/health")
    assert response.status_code == 200


def test_health_response_shape():
    """Health endpoint must return the expected JSON keys."""
    response = client.get("/api/health")
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "bolta-khata-ai-backend"
    assert "version" in data


def test_health_content_type():
    """Health endpoint must return JSON content-type."""
    response = client.get("/api/health")
    assert "application/json" in response.headers["content-type"]
