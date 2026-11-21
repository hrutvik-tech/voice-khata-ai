"""
backend/tests/m4/test_ws.py

Tests for WebSocket /ws endpoint and debug endpoints (M4-3):
- /ws token authentication and 4401 close
- turn lifecycle: turn_start -> 1024-byte audio -> commit -> events
- ping/pong
- debug routes: /debug/turn, /debug/choose, /debug/reset
"""

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect


def _register_shop(client: TestClient, phone="9300000001") -> tuple[str, dict]:
    res = client.post("/auth/register", json={"owner_name": "Sharma", "phone": phone, "pin": "1234"})
    assert res.status_code == 201
    return res.json()["token"], res.json()["shop"]


def test_ws_unauthorized_token_closes_4401(client: TestClient):
    # Invalid token
    with pytest.raises(WebSocketDisconnect) as exc1:
        with client.websocket_connect("/ws?token=invalid_token"):
            pass
    assert exc1.value.code == 4401

    # Missing token
    with pytest.raises(WebSocketDisconnect) as exc2:
        with client.websocket_connect("/ws"):
            pass
    assert exc2.value.code == 4401


def test_ws_turn_lifecycle(client: TestClient):
    token, shop = _register_shop(client, "9300000002")

    with client.websocket_connect(f"/ws?token={token}") as ws:
        # Initial messages: ready, state: resting
        ready_msg = ws.receive_json()
        assert ready_msg["type"] == "ready"
        assert ready_msg["shop_id"] == shop["id"]
        assert "session_id" in ready_msg

        state_msg = ws.receive_json()
        assert state_msg["type"] == "state"
        assert state_msg["state"] == "resting"

        # Ping / pong
        ws.send_json({"type": "ping"})
        pong_msg = ws.receive_json()
        assert pong_msg["type"] == "pong"

        # Start turn
        turn_id = "test-turn-uuid-1"
        ws.send_json({"type": "turn_start", "turn_id": turn_id})
        st_listening = ws.receive_json()
        assert st_listening["type"] == "state"
        assert st_listening["state"] == "listening"

        # Send bad audio frame (not 1024 bytes)
        ws.send_bytes(b"too_short")
        err_msg = ws.receive_json()
        assert err_msg["type"] == "error"
        assert err_msg["code"] == "bad_message"

        # Send valid 1024-byte audio frame
        valid_frame = b"\x00" * 1024
        ws.send_bytes(valid_frame)

        # Commit turn with transcript text
        ws.send_json({"type": "commit", "turn_id": turn_id, "text": "Ramesh Sharma ka 340 udhaar"})

        # Expect state: understanding
        st_und = ws.receive_json()
        assert st_und["type"] == "state"
        assert st_und["state"] == "understanding"

        # Expect heard
        heard_msg = ws.receive_json()
        assert heard_msg["type"] == "heard"
        assert heard_msg["turn_id"] == turn_id

        # Expect entry
        entry_msg = ws.receive_json()
        assert entry_msg["type"] == "entry"
        assert entry_msg["entry"]["amount_paise"] == 34000
        assert entry_msg["entry"]["direction"] == "credit"

        # Expect answer
        ans_msg = ws.receive_json()
        assert ans_msg["type"] == "answer"
        assert ans_msg["kind"] == "entry_saved"
        # First turn disclosure check
        assert "मुंशी" in ans_msg["say"]

        # Final state: resting
        st_resting = ws.receive_json()
        assert st_resting["type"] == "state"
        assert st_resting["state"] == "resting"


def test_debug_routes(client: TestClient):
    token, _ = _register_shop(client, "9300000003")
    headers = {"Authorization": f"Bearer {token}"}

    # Debug turn
    res_turn = client.post(
        "/debug/turn",
        headers=headers,
        json={"text": "Ramesh Sharma ka 340 udhaar"},
    )
    assert res_turn.status_code == 200
    t_data = res_turn.json()
    assert "events" in t_data
    assert any(e["type"] == "entry" for e in t_data["events"])

    # Debug reset
    res_reset = client.post("/debug/reset", headers=headers)
    assert res_reset.status_code == 204

    # Verify demo customers seeded
    custs = client.get("/customers", headers=headers).json()
    names = [c["name"] for c in custs]
    assert "Ramesh Sharma" in names
    assert "Suresh" in names
