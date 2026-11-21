"""
backend/app/api/debug.py

Debug endpoints for Bolta Khata AI:
- POST /debug/turn
- POST /debug/choose
- POST /debug/reset
Guarded by DEBUG=true and JWT authentication.
"""

import os
import uuid
from datetime import datetime, timezone
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel

from app.core.tokens import get_current_shop, hash_pin
from app.database.db import get_connection
from app.services.conversation import get_or_create_session
from app.services.ledger import create_customer, create_entry, delete_shop_data
from app.services.orchestrator import Transcript, handle_choice, handle_transcript

router = APIRouter(prefix="/debug", tags=["debug"])


def _check_debug_enabled():
    debug_val = os.getenv("DEBUG", "true").lower()
    if debug_val not in ("true", "1"):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Debug disabled")


class DebugTurnRequest(BaseModel):
    text: str
    now: str | None = None
    session_id: str | None = None


class DebugChooseRequest(BaseModel):
    session_id: str
    turn_id: str
    choice: dict[str, Any]
    now: str | None = None


class DebugResetRequest(BaseModel):
    now: str | None = None


@router.post("/turn")
async def debug_turn(
    payload: DebugTurnRequest,
    current_shop: dict = Depends(get_current_shop),
) -> dict[str, Any]:
    _check_debug_enabled()
    now_dt = datetime.fromisoformat(payload.now) if payload.now else datetime.now(timezone.utc)
    session = get_or_create_session(current_shop["id"], now_dt, payload.session_id)
    session_id = session["id"]

    turn_id = str(uuid.uuid4())
    ts = Transcript(text=payload.text, language="hi")

    events = await handle_transcript(
        session_id=session_id,
        turn_id=turn_id,
        transcript=ts,
        now=now_dt,
        source="voice",
    )
    return {
        "session_id": session_id,
        "turn_id": turn_id,
        "events": events,
    }


@router.post("/choose")
async def debug_choose(
    payload: DebugChooseRequest,
    current_shop: dict = Depends(get_current_shop),
) -> dict[str, Any]:
    _check_debug_enabled()
    now_dt = datetime.fromisoformat(payload.now) if payload.now else datetime.now(timezone.utc)
    events = await handle_choice(
        session_id=payload.session_id,
        turn_id=payload.turn_id,
        choice=payload.choice,
        now=now_dt,
    )
    return {"events": events}


@router.post("/reset", status_code=status.HTTP_204_NO_CONTENT)
def debug_reset(
    payload: DebugResetRequest = None,
    current_shop: dict = Depends(get_current_shop),
) -> Response:
    _check_debug_enabled()
    shop_id = current_shop["id"]
    delete_shop_data(shop_id)

    # Reseed demo shop
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO shops (
                id, owner_name, shop_name, phone, pin_hash, open_time, close_time, timezone, language_mode, setup_complete
            ) VALUES (?, 'Sharma', 'Sharma Kirana Store', '9000000001', ?, '06:00', '02:00', 'Asia/Kolkata', 'mix', 1)
            """,
            (shop_id, hash_pin("1234")),
        )
        conn.commit()

        # Seed customers
        r_sharma = create_customer(shop_id, "Ramesh Sharma", area="Gandhi Nagar")
        r_gupta = create_customer(shop_id, "Ramesh Gupta", area="Station Road")
        suresh = create_customer(shop_id, "Suresh")
        amit = create_customer(shop_id, "Amit")

        now = datetime.now(timezone.utc)
        # Seed credits
        create_entry(shop_id, r_sharma["id"], 50000, "credit", "2026-11-14", now, source="seed")
        create_entry(shop_id, r_gupta["id"], 80000, "credit", "2026-11-14", now, source="seed")
        create_entry(shop_id, suresh["id"], 25000, "credit", "2026-11-14", now, source="seed")

        return Response(status_code=status.HTTP_204_NO_CONTENT)
    finally:
        conn.close()
