"""
backend/app/api/ws.py

WebSocket handler for Bolta Khata AI:
- Endpoint: /ws?token=<JWT>
- Manages audio streaming, turn lifecycle, state transitions, and client messaging.
"""

import json
import os
from datetime import datetime, timezone
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.tokens import decode_access_token
from app.services.conversation import get_or_create_session
from app.services.orchestrator import Transcript, handle_choice, handle_transcript

router = APIRouter(tags=["websocket"])

STUB_TRANSCRIPT = os.getenv("STUB_TRANSCRIPT", "Ramesh Sharma ka 340 udhaar")


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: str | None = None):
    # 1. Authenticate query token
    if not token:
        await websocket.close(code=4401)
        return

    try:
        payload = decode_access_token(token)
        shop_id = int(payload["shop_id"])
    except Exception:
        await websocket.close(code=4401)
        return

    await websocket.accept()

    # 2. Session setup
    now = datetime.now(timezone.utc)
    session = get_or_create_session(shop_id, now)
    session_id = session["id"]

    # Send ready and initial state
    await websocket.send_json({"type": "ready", "session_id": session_id, "shop_id": shop_id})
    await websocket.send_json({"type": "state", "state": "resting"})

    active_turn_id: str | None = None
    turn_audio_frames: list[bytes] = []
    seen_turn_ids: set[str] = set()

    try:
        while True:
            message = await websocket.receive()
            m_type = message.get("type")

            if m_type == "websocket.disconnect":
                break

            if m_type == "websocket.receive":
                # Binary frame
                if "bytes" in message and message["bytes"] is not None:
                    raw_bytes = message["bytes"]
                    if len(raw_bytes) != 1024:
                        await websocket.send_json({
                            "type": "error",
                            "turn_id": active_turn_id or "",
                            "code": "bad_message",
                            "say": "Frame size must be exactly 1024 bytes",
                        })
                        continue

                    if active_turn_id:
                        turn_audio_frames.append(raw_bytes)
                    continue

                # Text frame
                if "text" in message and message["text"] is not None:
                    data = json.loads(message["text"])
                    msg_type = data.get("type")

                    if msg_type == "ping":
                        await websocket.send_json({"type": "pong"})
                        continue

                    if msg_type == "turn_start":
                        t_id = data.get("turn_id")
                        if t_id in seen_turn_ids:
                            continue
                        seen_turn_ids.add(t_id)

                        active_turn_id = t_id
                        turn_audio_frames = []
                        await websocket.send_json({"type": "state", "state": "listening"})
                        continue

                    if msg_type == "cancel":
                        active_turn_id = None
                        turn_audio_frames = []
                        await websocket.send_json({"type": "state", "state": "resting"})
                        continue

                    if msg_type == "commit":
                        t_id = data.get("turn_id") or active_turn_id
                        await websocket.send_json({"type": "state", "state": "understanding"})

                        transcript_text = data.get("text") or STUB_TRANSCRIPT
                        ts = Transcript(text=transcript_text, language="hi")

                        now_override_str = data.get("now_override")
                        commit_now = datetime.fromisoformat(now_override_str) if now_override_str else datetime.now(timezone.utc)

                        events = await handle_transcript(
                            session_id=session_id,
                            turn_id=t_id,
                            transcript=ts,
                            now=commit_now,
                            source="voice",
                        )

                        for ev in events:
                            await websocket.send_json(ev)

                        has_question = any(e.get("type") == "question" for e in events)
                        next_state = "asking" if has_question else "resting"
                        await websocket.send_json({"type": "state", "state": next_state})

                        active_turn_id = None
                        turn_audio_frames = []
                        continue

                    if msg_type == "choose":
                        t_id = data.get("turn_id")
                        choice = data.get("choice", {})
                        events = await handle_choice(
                            session_id=session_id,
                            turn_id=t_id,
                            choice=choice,
                            now=datetime.now(timezone.utc),
                        )
                        for ev in events:
                            await websocket.send_json(ev)

                        has_question = any(e.get("type") == "question" for e in events)
                        next_state = "asking" if has_question else "resting"
                        await websocket.send_json({"type": "state", "state": next_state})
                        continue

    except WebSocketDisconnect:
        pass
