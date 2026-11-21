import asyncio
import base64
import json
import logging
import os
from pathlib import Path
import time
from typing import AsyncIterator, Literal

import websockets

logger = logging.getLogger(__name__)

Lang = Literal["hi", "kn", "en"]


class TtsError(Exception):
    """Raised when Text-to-Speech operation fails."""
    pass


def _get_api_key() -> str:
    key = os.getenv("GNANI_API_KEY", "").strip()
    if key:
        return key
    for env_path in [
        Path.cwd() / ".env",
        Path.cwd() / ".env.txt",
        Path(__file__).resolve().parents[2].parent / ".env",
        Path(__file__).resolve().parents[2].parent / ".env.txt",
    ]:
        if env_path.exists():
            for line in env_path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line.startswith("GNANI_API_KEY="):
                    key = line.split("=", 1)[1].strip()
                    break
                elif line.startswith("vach_"):
                    key = line
                    break
            if key:
                os.environ["GNANI_API_KEY"] = key
                return key
    return ""


async def synthesize(text: str, language: Lang, timeout: float = 10.0) -> AsyncIterator[bytes]:
    """
    Connect to Gnani's realtime TTS WebSocket, send one synthesis request,
    and yield decoded audio chunks in order as they arrive.
    
    Raises:
        TtsError: On error message, connection failure, or timeout.
    """
    api_key = _get_api_key()
    if not api_key:
        raise TtsError("GNANI_API_KEY environment variable is missing or empty")

    model = os.getenv("TTS_MODEL", "timbre-v3.0").strip()
    voice = os.getenv("TTS_VOICE", "Shivani").strip()
    if not voice:
        voice = "Shivani"
    container = os.getenv("TTS_CONTAINER", "mp3").strip()
    sample_rate = int(os.getenv("TTS_SAMPLE_RATE", "16000").strip())

    lang_map: dict[str, str] = {
        "hi": "hi-IN",
        "kn": "kn-IN",
        "en": "en-IN",
    }
    lang_code = lang_map.get(language, language)

    headers = {
        "X-API-Key-ID": api_key,
        "voice": voice,
        "model": model,
        "language": lang_code,
        "speed": "1.0",
        "audio_config.sample_rate": str(sample_rate),
        "audio_config.num_channels": "1",
        "audio_config.sample_width": "2",
        "audio_config.encoding": "linear_pcm",
        "audio_config.container": container,
    }

    ws_url = os.getenv("GNANI_TTS_WS_URL", "wss://api.vachana.ai/api/v1/tts").strip()

    request_payload = {
        "text": text,
        "voice": voice,
        "model": model,
        "language": lang_code,
        "speed": 1.0,
        "audio_config": {
            "sample_rate": sample_rate,
            "num_channels": 1,
            "sample_width": 2,
            "encoding": "linear_pcm",
            "container": container,
        },
    }

    try:
        ws = await websockets.connect(ws_url, additional_headers=headers)
    except Exception as exc:
        raise TtsError(f"Failed to connect to TTS WebSocket: {exc}") from exc

    start_time = time.monotonic()
    first_chunk_logged = False

    try:
        await ws.send(json.dumps(request_payload))

        while True:
            try:
                raw_msg = await asyncio.wait_for(ws.recv(), timeout=timeout)
            except asyncio.TimeoutError as exc:
                raise TtsError(f"TTS synthesis timed out after {timeout} seconds") from exc
            except websockets.exceptions.ConnectionClosed as exc:
                if first_chunk_logged:
                    break
                raise TtsError(f"TTS connection closed prematurely: {exc}") from exc
            except Exception as exc:
                raise TtsError(f"TTS receive error: {exc}") from exc

            if isinstance(raw_msg, bytes):
                raw_msg = raw_msg.decode("utf-8")

            try:
                msg = json.loads(raw_msg)
            except json.JSONDecodeError as exc:
                raise TtsError(f"Invalid JSON received from TTS server: {raw_msg}") from exc

            msg_type = msg.get("type")

            # Check for error first
            if msg_type == "error" or "error" in msg:
                err_msg = msg.get("message") or msg.get("error") or "Unknown TTS error"
                raise TtsError(f"TTS server error: {err_msg}")

            if msg_type == "complete":
                break

            # Process audio chunk
            audio_b64 = None
            if isinstance(msg.get("data"), dict) and "audio" in msg["data"]:
                audio_b64 = msg["data"]["audio"]
            elif "audio" in msg:
                audio_b64 = msg["audio"]

            if audio_b64:
                try:
                    audio_chunk = base64.b64decode(audio_b64)
                except Exception as exc:
                    raise TtsError(f"Failed to decode base64 audio chunk: {exc}") from exc

                if not first_chunk_logged:
                    latency_ms = int((time.monotonic() - start_time) * 1000)
                    logger.info("TTS first chunk received in %d ms", latency_ms)
                    first_chunk_logged = True

                yield audio_chunk

    finally:
        try:
            await ws.close()
        except (OSError, Exception):
            pass
