"""
backend/tests/m4/test_sync_and_me.py

Tests for M4-5:
- POST /sync/audio (offline audio sync, WAV validation, idempotency)
- DELETE /me (account deletion, cascade, token invalidation)
- WebSocket reconnect and session preservation
- Kannada fallback behavior
"""

import io
import wave
from datetime import datetime, timezone
import pytest
from fastapi.testclient import TestClient

from app.services.replies import render_reply


def _create_valid_wav_bytes(duration_sec: float = 0.1) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)  # mono
        wf.setsampwidth(2)  # 16-bit
        wf.setframerate(16000)  # 16 kHz
        frames = int(16000 * duration_sec)
        wf.writeframes(b"\x00\x00" * frames)
    return buf.getvalue()


def _register_shop(client: TestClient, phone="9500000001") -> tuple[str, dict]:
    res = client.post("/auth/register", json={"owner_name": "Sharma", "phone": phone, "pin": "1234"})
    assert res.status_code == 201
    return res.json()["token"], res.json()["shop"]


def test_sync_audio_requires_auth(client: TestClient):
    wav = _create_valid_wav_bytes()
    res = client.post(
        "/sync/audio",
        files={"audio": ("test.wav", wav, "audio/wav")},
        data={"idempotency_key": "k1", "recorded_at": datetime.now(timezone.utc).isoformat()},
    )
    assert res.status_code == 401


def test_sync_audio_invalid_wav_returns_422(client: TestClient):
    token, _ = _register_shop(client, "9500000002")
    headers = {"Authorization": f"Bearer {token}"}

    # Non-WAV data
    res = client.post(
        "/sync/audio",
        headers=headers,
        files={"audio": ("bad.wav", b"not a wav file", "audio/wav")},
        data={"idempotency_key": "k2", "recorded_at": datetime.now(timezone.utc).isoformat()},
    )
    assert res.status_code == 422


def test_sync_audio_success_and_idempotency(client: TestClient):
    token, _ = _register_shop(client, "9500000003")
    headers = {"Authorization": f"Bearer {token}"}
    wav = _create_valid_wav_bytes()
    now_iso = datetime.now(timezone.utc).isoformat()
    key = "offline-turn-uuid-1"

    # First upload
    res1 = client.post(
        "/sync/audio",
        headers=headers,
        files={"audio": ("sample.wav", wav, "audio/wav")},
        data={"idempotency_key": key, "recorded_at": now_iso},
    )
    assert res1.status_code == 200
    data1 = res1.json()
    assert data1["turn_id"] == key
    assert len(data1["events"]) >= 2
    # Heard must be first
    assert data1["events"][0]["type"] == "heard"
    assert any(e["type"] == "entry" for e in data1["events"])

    # Duplicate upload with same idempotency key
    res2 = client.post(
        "/sync/audio",
        headers=headers,
        files={"audio": ("sample.wav", wav, "audio/wav")},
        data={"idempotency_key": key, "recorded_at": now_iso},
    )
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["turn_id"] == key


def test_delete_account_and_token_invalidation(client: TestClient):
    token, _ = _register_shop(client, "9500000004")
    headers = {"Authorization": f"Bearer {token}"}

    # Shop profile works
    assert client.get("/shop", headers=headers).status_code == 200

    # Delete account
    del_res = client.delete("/me", headers=headers)
    assert del_res.status_code == 204

    # Subsequent request with old token returns 401
    assert client.get("/shop", headers=headers).status_code == 401
    assert client.get("/customers", headers=headers).status_code == 401


def test_ws_reconnect_session_reuse(client: TestClient):
    token, _ = _register_shop(client, "9500000005")

    # Connect first time
    with client.websocket_connect(f"/ws?token={token}") as ws1:
        ready1 = ws1.receive_json()
        assert ready1["type"] == "ready"
        sess_id_1 = ready1["session_id"]
        state1 = ws1.receive_json()
        assert state1["type"] == "state"

    # Reconnect second time within 30 mins
    with client.websocket_connect(f"/ws?token={token}") as ws2:
        ready2 = ws2.receive_json()
        assert ready2["type"] == "ready"
        sess_id_2 = ready2["session_id"]
        state2 = ws2.receive_json()
        assert state2["type"] == "state"
        # Reused session
        assert sess_id_1 == sess_id_2


def test_kannada_fallback_to_hindi():
    """Contracts state Kannada falls back to Hindi until official voice translations."""
    reply_kn = render_reply("disclosure", "kn")
    reply_hi = render_reply("disclosure", "hi")
    assert reply_kn == reply_hi
    assert "मुंशी" in reply_kn
