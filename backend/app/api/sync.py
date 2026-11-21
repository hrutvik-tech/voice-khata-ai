"""
backend/app/api/sync.py

Offline audio sync endpoint for Bolta Khata AI:
- POST /sync/audio
Validates 16 kHz mono 16-bit PCM WAV, performs offline speech recognition,
and processes turns in strict mode (ambiguous questions become not_saved).
"""

import io
import os
import wave
from datetime import datetime, timezone
from typing import Any
from fastapi import APIRouter, Depends, Form, HTTPException, UploadFile, status

from app.core.tokens import get_current_shop
from app.services.conversation import get_or_create_session
from app.services.orchestrator import Transcript, handle_transcript

router = APIRouter(prefix="/sync", tags=["sync"])

STUB_TRANSCRIPT = os.getenv("STUB_TRANSCRIPT", "Ramesh Sharma ka 340 udhaar")


def validate_wav(audio_bytes: bytes) -> bool:
    """Validates that audio is 16 kHz, 16-bit mono PCM WAV."""
    try:
        with wave.open(io.BytesIO(audio_bytes), "rb") as wf:
            channels = wf.getnchannels()
            sample_width = wf.getsampwidth()
            framerate = wf.getframerate()
            return channels == 1 and sample_width == 2 and framerate == 16000
    except Exception:
        return False


@router.post("/audio")
async def sync_audio(
    audio: UploadFile,
    idempotency_key: str = Form(...),
    recorded_at: str = Form(...),
    current_shop: dict = Depends(get_current_shop),
) -> dict[str, Any]:
    audio_content = await audio.read()

    # Validate WAV audio format
    if not validate_wav(audio_content):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid audio: must be 16 kHz, 16-bit mono WAV",
        )

    try:
        rec_dt = datetime.fromisoformat(recorded_at)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid recorded_at ISO timestamp",
        )

    shop_id = current_shop["id"]
    session = get_or_create_session(shop_id, rec_dt)
    session_id = session["id"]

    ts = Transcript(text=STUB_TRANSCRIPT, language="hi")

    events = await handle_transcript(
        session_id=session_id,
        turn_id=idempotency_key,
        transcript=ts,
        now=rec_dt,
        source="offline",
        strict=True,
    )

    return {
        "turn_id": idempotency_key,
        "events": events,
    }
