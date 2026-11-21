import asyncio
from datetime import datetime, timezone
import json
import logging
import os
from typing import Literal

import httpx
from pydantic import BaseModel
import websockets

logger = logging.getLogger(__name__)

Lang = Literal["hi", "kn", "en"]

try:
    from app.schemas.contracts import Transcript
except ImportError:
    class Transcript(BaseModel):
        text: str
        language: Lang | None = None
        latency_ms: int | None = None


class SttError(Exception):
    """Raised when Speech-to-Text operation fails."""
    pass


class SttSession:
    """Realtime streaming Speech-to-Text session using Gnani WebSocket."""

    def __init__(self, lang_hints: list[str], keyterms: list[str]) -> None:
        self.lang_hints = lang_hints
        self.keyterms = keyterms
        self._ws = None
        self._closed = False

        # Utterance timestamps for logging
        self._open_ts: str | None = None
        self._first_frame_ts: str | None = None
        self._commit_ts: str | None = None
        self._transcript_ts: str | None = None

        # Utterance segment storage
        self._segments: list[dict] = []
        self._detected_lang: str | None = None
        self._latency: int | None = None

    async def open(self) -> None:
        """Connect to Gnani's realtime STT WebSocket and wait for 'connected' message."""
        api_key = os.getenv("GNANI_API_KEY", "").strip()
        if not api_key:
            raise SttError("GNANI_API_KEY environment variable is missing or empty")

        model = os.getenv("STT_MODEL", "prisma-v3.0").strip()
        stt_format = os.getenv("STT_FORMAT", "codemix").strip()
        min_silence_ms = os.getenv("STT_MIN_SILENCE_MS", "350").strip()
        vad_threshold = os.getenv("STT_VAD_THRESHOLD", "0.7").strip()
        sample_rate = "16000"

        headers = {
            "x-api-key-id": api_key,
            "language_code": ",".join(self.lang_hints),
            "model": model,
            "format": stt_format,
            "x-sample-rate": sample_rate,
            "x-min-silence-ms": min_silence_ms,
            "x-vad-threshold": vad_threshold,
        }

        if model == "prisma-v3.0" and self.keyterms:
            cleaned = []
            seen = set()
            for k in self.keyterms:
                k_clean = k.strip()
                if k_clean and k_clean not in seen:
                    seen.add(k_clean)
                    cleaned.append(k_clean)
                    if len(cleaned) == 200:
                        break
            if cleaned:
                headers["keyterms"] = json.dumps(cleaned)

        ws_url = os.getenv("GNANI_STT_WS_URL", "wss://api.vachana.ai/stt/v3/stream").strip()
        self._open_ts = datetime.now(timezone.utc).isoformat()

        try:
            self._ws = await websockets.connect(ws_url, additional_headers=headers)
        except Exception as exc:
            raise SttError(f"Failed to connect to STT WebSocket: {exc}") from exc

        # Wait for the documented 'connected' confirmation message
        try:
            first_msg = await self._ws.recv()
            if isinstance(first_msg, bytes):
                first_msg = first_msg.decode("utf-8")
            data = json.loads(first_msg)
            if data.get("type") == "error":
                raise SttError(data.get("message", "STT connection error"))
            if data.get("type") != "connected":
                raise SttError(f"Expected 'connected' message, got '{data.get('type')}'")
        except websockets.ConnectionClosed as exc:
            raise SttError(f"WebSocket closed during connection handshake: {exc.code} {exc.reason}") from exc
        except SttError:
            raise
        except Exception as exc:
            raise SttError(f"Error waiting for connected message: {exc}") from exc

    async def send(self, frame: bytes) -> None:
        """Send a 1,024-byte PCM audio frame."""
        if len(frame) != 1024:
            raise ValueError(f"Frame length must be exactly 1024 bytes, got {len(frame)}")
        if self._closed or self._ws is None:
            raise SttError("Cannot send frame; SttSession is closed or not open")

        if not self._first_frame_ts:
            self._first_frame_ts = datetime.now(timezone.utc).isoformat()

        try:
            await self._ws.send(frame)
        except websockets.ConnectionClosed as exc:
            raise SttError(f"WebSocket closed while sending frame: {exc.code} {exc.reason}") from exc

    async def commit(self) -> None:
        """Send commit control frame to close the open utterance immediately."""
        if self._closed or self._ws is None:
            raise SttError("Cannot commit; SttSession is closed or not open")

        if not self._commit_ts:
            self._commit_ts = datetime.now(timezone.utc).isoformat()

        try:
            await self._ws.send(json.dumps({"type": "commit"}))
        except websockets.ConnectionClosed as exc:
            raise SttError(f"WebSocket closed while committing: {exc.code} {exc.reason}") from exc

    async def result(self, timeout: float = 6.0) -> Transcript:
        """Collect transcript messages for this utterance and return Transcript."""
        if self._closed or self._ws is None:
            raise SttError("Cannot get result; SttSession is closed or not open")

        loop = asyncio.get_running_loop()
        deadline = loop.time() + timeout

        try:
            while True:
                remaining = deadline - loop.time()
                if remaining <= 0:
                    if self._segments:
                        break
                    raise SttError(f"STT result timed out after {timeout} seconds")

                # If we already have at least one segment, wait only briefly for subsequent segments
                recv_timeout = min(0.2, remaining) if self._segments else remaining

                try:
                    msg = await asyncio.wait_for(self._ws.recv(), timeout=recv_timeout)
                except asyncio.TimeoutError:
                    if self._segments:
                        # Utterance segments fully collected
                        break
                    raise SttError(f"STT result timed out after {timeout} seconds")

                if isinstance(msg, bytes):
                    msg = msg.decode("utf-8")
                data = json.loads(msg)
                msg_type = data.get("type")

                if msg_type == "error":
                    raise SttError(data.get("message", "Gnani STT error"))

                if msg_type == "transcript":
                    self._transcript_ts = datetime.now(timezone.utc).isoformat()
                    self._segments.append(data)
                    if data.get("detected_language_code"):
                        self._detected_lang = data.get("detected_language_code")
                    if data.get("latency") is not None:
                        self._latency = data.get("latency")

        except websockets.ConnectionClosed as exc:
            # Documented close codes e.g. 1008 (policy/bad header), 1001 (timeout/15 min)
            if exc.code in (1008, 1001) or exc.code >= 4000:
                raise SttError(f"STT WebSocket closed: {exc.code} {exc.reason}") from exc
            if not self._segments:
                raise SttError(f"STT WebSocket closed without transcript: {exc.code} {exc.reason}") from exc

        # Join text in segment order
        self._segments.sort(key=lambda s: s.get("segment_index", 0))
        joined_text = " ".join(s.get("text", "").strip() for s in self._segments if s.get("text", "").strip()).strip()

        # Map detected language code to 'hi', 'kn', 'en' (first two letters)
        mapped_lang: Lang | None = None
        if self._detected_lang:
            prefix = self._detected_lang[:2].lower()
            if prefix in ("hi", "kn", "en"):
                mapped_lang = prefix  # type: ignore[assignment]

        # Log one line per utterance (no audio, no keys)
        logger.info(
            "Utterance: open=%s first_frame=%s commit=%s transcript=%s",
            self._open_ts,
            self._first_frame_ts,
            self._commit_ts,
            self._transcript_ts,
        )

        return Transcript(text=joined_text, language=mapped_lang, latency_ms=self._latency)

    async def close(self) -> None:
        """Close WebSocket cleanly; safe to call twice."""
        if self._closed:
            return
        self._closed = True
        if self._ws is not None:
            try:
                await self._ws.close()
            except Exception:
                pass
            finally:
                self._ws = None


async def transcribe_file(wav_bytes: bytes, lang_hints: list[str], keyterms: list[str]) -> Transcript:
    """Transcribe audio clip via Gnani STT REST endpoint for offline sync."""
    api_key = os.getenv("GNANI_API_KEY", "").strip()
    if not api_key:
        raise SttError("GNANI_API_KEY environment variable is missing or empty")

    model = os.getenv("STT_MODEL", "prisma-v3.0").strip()
    stt_format = os.getenv("STT_FORMAT", "codemix").strip()
    rest_url = os.getenv("GNANI_STT_REST_URL", "https://api.vachana.ai/stt/v3").strip()

    headers = {"x-api-key-id": api_key}
    data = {
        "language_code": ",".join(lang_hints),
        "model": model,
        "format": stt_format,
    }

    if model == "prisma-v3.0" and keyterms:
        cleaned = []
        seen = set()
        for k in keyterms:
            k_clean = k.strip()
            if k_clean and k_clean not in seen:
                seen.add(k_clean)
                cleaned.append(k_clean)
                if len(cleaned) == 200:
                    break
        if cleaned:
            data["keyterms"] = json.dumps(cleaned)

    files = {"audio_file": ("audio.wav", wav_bytes, "audio/wav")}

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(rest_url, headers=headers, data=data, files=files)
    except Exception as exc:
        raise SttError(f"HTTP request to STT REST endpoint failed: {exc}") from exc

    if resp.status_code != 200:
        raise SttError(f"STT REST error HTTP {resp.status_code}: {resp.text}")

    try:
        res_json = resp.json()
    except Exception as exc:
        raise SttError(f"Failed to parse STT REST response as JSON: {exc}") from exc

    if not res_json.get("success", True):
        raise SttError(res_json.get("message", "STT REST transcription reported failure"))

    text = res_json.get("transcript", "").strip()
    detected = res_json.get("detected_language_code")
    mapped_lang: Lang | None = None
    if detected:
        prefix = detected[:2].lower()
        if prefix in ("hi", "kn", "en"):
            mapped_lang = prefix  # type: ignore[assignment]

    latency_sec = res_json.get("end_to_end_latency")
    if latency_sec is None:
        latency_sec = res_json.get("processing_time")
    latency_ms = int(round(latency_sec * 1000)) if latency_sec is not None else None

    return Transcript(text=text, language=mapped_lang, latency_ms=latency_ms)
