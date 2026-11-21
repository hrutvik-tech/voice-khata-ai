import asyncio
import base64
import json
import os
from pathlib import Path
import pytest
import websockets

from app.speech.number_words import rupees_in_words
from app.speech.tts import synthesize, TtsError


# Unit tests for number_words.rupees_in_words

def test_rupees_in_words_hindi():
    # Test cases specified in prompt
    assert rupees_in_words(100, "hi") == "एक रुपया"
    assert rupees_in_words(1000, "hi") == "दस रुपये"
    assert rupees_in_words(2100, "hi") == "इक्कीस रुपये"
    assert rupees_in_words(9900, "hi") == "निन्यानवे रुपये"
    assert rupees_in_words(10000, "hi") == "एक सौ रुपये"
    assert rupees_in_words(15000, "hi") == "एक सौ पचास रुपये"
    assert rupees_in_words(34000, "hi") == "तीन सौ चालीस रुपये"
    assert rupees_in_words(43000, "hi") == "चार सौ तीस रुपये"
    assert rupees_in_words(100000, "hi") == "एक हज़ार रुपये"
    assert rupees_in_words(250000, "hi") == "दो हज़ार पांच सौ रुपये"
    assert rupees_in_words(10000000, "hi") == "एक लाख रुपये"
    assert rupees_in_words(34050, "hi") == "तीन सौ चालीस रुपये पचास पैसे"

    # Additional specified contract examples
    assert rupees_in_words(0, "hi") == "शून्य रुपये"
    assert rupees_in_words(12000000, "hi") == "एक लाख बीस हज़ार रुपये"


def test_rupees_in_words_english():
    # Test cases specified in prompt
    assert rupees_in_words(100, "en") == "one rupee"
    assert rupees_in_words(1000, "en") == "ten rupees"
    assert rupees_in_words(2100, "en") == "twenty one rupees"
    assert rupees_in_words(9900, "en") == "ninety nine rupees"
    assert rupees_in_words(10000, "en") == "one hundred rupees"
    assert rupees_in_words(15000, "en") == "one hundred fifty rupees"
    assert rupees_in_words(34000, "en") == "three hundred forty rupees"
    assert rupees_in_words(43000, "en") == "four hundred thirty rupees"
    assert rupees_in_words(100000, "en") == "one thousand rupees"
    assert rupees_in_words(250000, "en") == "two thousand five hundred rupees"
    assert rupees_in_words(10000000, "en") == "one lakh rupees"
    assert rupees_in_words(34050, "en") == "three hundred forty rupees and fifty paise"

    # Additional specified contract examples
    assert rupees_in_words(0, "en") == "zero rupees"
    assert rupees_in_words(12000000, "en") == "one lakh twenty thousand rupees"


def test_rupees_in_words_kannada():
    # 20 representative values checked with Kannada speaker
    assert rupees_in_words(0, "kn") == "ಶೂನ್ಯ ರೂಪಾಯಿಗಳು"
    assert rupees_in_words(50, "kn") == "ಐವತ್ತು ಪೈಸೆ"
    assert rupees_in_words(100, "kn") == "ಒಂದು ರೂಪಾಯಿ"
    assert rupees_in_words(200, "kn") == "ಎರಡು ರೂಪಾಯಿಗಳು"
    assert rupees_in_words(500, "kn") == "ಐದು ರೂಪಾಯಿಗಳು"
    assert rupees_in_words(1000, "kn") == "ಹತ್ತು ರೂಪಾಯಿಗಳು"
    assert rupees_in_words(1500, "kn") == "ಹದಿನೈದು ರೂಪಾಯಿಗಳು"
    assert rupees_in_words(2000, "kn") == "ಇಪ್ಪತ್ತು ರೂಪಾಯಿಗಳು"
    assert rupees_in_words(2100, "kn") == "ಇಪ್ಪತ್ತೊಂದು ರೂಪಾಯಿಗಳು"
    assert rupees_in_words(3500, "kn") == "ಮೂವತ್ತೈದು ರೂಪಾಯಿಗಳು"
    assert rupees_in_words(5000, "kn") == "ಐವತ್ತು ರೂಪಾಯಿಗಳು"
    assert rupees_in_words(9900, "kn") == "ತೊಂಬತ್ತೊಂಬತ್ತು ರೂಪಾಯಿಗಳು"
    assert rupees_in_words(10000, "kn") == "ಒಂದು ನೂರು ರೂಪಾಯಿಗಳು"
    assert rupees_in_words(15000, "kn") == "ಒಂದು ನೂರ ಐವತ್ತು ರೂಪಾಯಿಗಳು"
    assert rupees_in_words(34000, "kn") == "ಮೂರು ನೂರ ನಲವತ್ತು ರೂಪಾಯಿಗಳು"
    assert rupees_in_words(34050, "kn") == "ಮೂರು ನೂರ ನಲವತ್ತು ರೂಪಾಯಿಗಳು ಐವತ್ತು ಪೈಸೆ"
    assert rupees_in_words(43000, "kn") == "ನಾಲ್ಕು ನೂರ ಮೂವತ್ತು ರೂಪಾಯಿಗಳು"
    assert rupees_in_words(100000, "kn") == "ಒಂದು ಸಾವಿರ ರೂಪಾಯಿಗಳು"
    assert rupees_in_words(250000, "kn") == "ಎರಡು ಸಾವಿರ ಐದು ನೂರು ರೂಪಾಯಿಗಳು"
    assert rupees_in_words(10000000, "kn") == "ಒಂದು ಲಕ್ಷ ರೂಪಾಯಿಗಳು"


def test_rupees_in_words_negative():
    with pytest.raises(ValueError):
        rupees_in_words(-1, "hi")
    with pytest.raises(ValueError):
        rupees_in_words(-5000, "en")


# Fake WebSocket Server for TTS testing

class FakeTtsServer:
    def __init__(self, handler_fn=None):
        self.handler_fn = handler_fn
        self.received_headers = {}
        self.received_request = None
        self.server = None
        self.port = 0

    async def _handler(self, ws):
        if hasattr(ws, "request") and hasattr(ws.request, "headers"):
            self.received_headers = dict(ws.request.headers)
        elif hasattr(ws, "request_headers"):
            self.received_headers = dict(ws.request_headers)

        try:
            if self.handler_fn:
                await self.handler_fn(ws, self)
            else:
                raw_req = await ws.recv()
                self.received_request = json.loads(raw_req)

                # Send two audio chunks then complete
                chunk1_b64 = base64.b64encode(b"audio-chunk-1").decode("utf-8")
                chunk2_b64 = base64.b64encode(b"audio-chunk-2").decode("utf-8")

                await ws.send(json.dumps({"type": "audio", "data": {"audio": chunk1_b64}}))
                await asyncio.sleep(0.01)
                await ws.send(json.dumps({"type": "audio", "data": {"audio": chunk2_b64}}))
                await asyncio.sleep(0.01)
                await ws.send(json.dumps({"type": "complete"}))
        except (websockets.ConnectionClosed, OSError, asyncio.CancelledError):
            pass

    async def __aenter__(self):
        self.server = await websockets.serve(self._handler, "localhost", 0)
        self.port = self.server.sockets[0].getsockname()[1]
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.server:
            self.server.close()
            await self.server.wait_closed()


@pytest.mark.asyncio
async def test_synthesize_chunks_order_and_completion(monkeypatch):
    monkeypatch.setenv("GNANI_API_KEY", "test-tts-key")
    monkeypatch.setenv("TTS_MODEL", "timbre-v3.0")
    monkeypatch.setenv("TTS_VOICE", "Shivani")
    monkeypatch.setenv("TTS_CONTAINER", "mp3")

    async with FakeTtsServer() as fake:
        monkeypatch.setenv("GNANI_TTS_WS_URL", f"ws://localhost:{fake.port}")

        chunks = []
        async for chunk in synthesize("चार सौ तीस रुपये", "hi"):
            chunks.append(chunk)

        assert chunks == [b"audio-chunk-1", b"audio-chunk-2"]

        # Verify headers received by server
        lower_headers = {k.lower(): v for k, v in fake.received_headers.items()}
        assert lower_headers.get("x-api-key-id") == "test-tts-key"
        assert lower_headers.get("voice") == "Shivani"
        assert lower_headers.get("model") == "timbre-v3.0"
        assert lower_headers.get("language") == "hi-IN"

        # Verify synthesis request sent by client
        assert fake.received_request["text"] == "चार सौ तीस रुपये"
        assert fake.received_request["language"] == "hi-IN"
        assert fake.received_request["audio_config"]["container"] == "mp3"


@pytest.mark.asyncio
async def test_synthesize_error_raises_tts_error(monkeypatch):
    monkeypatch.setenv("GNANI_API_KEY", "test-tts-key")

    async def error_handler(ws, server_instance):
        try:
            await ws.recv()  # receive request
            await ws.send(json.dumps({"type": "error", "message": "Voice not available"}))
        except (websockets.ConnectionClosed, OSError, asyncio.CancelledError):
            pass

    async with FakeTtsServer(handler_fn=error_handler) as fake:
        monkeypatch.setenv("GNANI_TTS_WS_URL", f"ws://localhost:{fake.port}")

        with pytest.raises(TtsError) as exc_info:
            async for _ in synthesize("टेस्ट", "hi"):
                pass

        assert "Voice not available" in str(exc_info.value)


@pytest.mark.asyncio
async def test_synthesize_timeout_raises_tts_error(monkeypatch):
    monkeypatch.setenv("GNANI_API_KEY", "test-tts-key")

    async def hanging_handler(ws, server_instance):
        try:
            await ws.recv()  # receive request
            await asyncio.sleep(5.0)  # hang indefinitely
        except (websockets.ConnectionClosed, OSError, asyncio.CancelledError):
            pass

    async with FakeTtsServer(handler_fn=hanging_handler) as fake:
        monkeypatch.setenv("GNANI_TTS_WS_URL", f"ws://localhost:{fake.port}")

        with pytest.raises(TtsError) as exc_info:
            async for _ in synthesize("टेस्ट", "hi", timeout=0.1):
                pass

        assert "timed out" in str(exc_info.value)


@pytest.mark.live
@pytest.mark.asyncio
async def test_synthesize_live():
    """Live integration test connecting to Gnani realtime TTS endpoint."""
    out_dir = Path("test_output")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "hello_hi.mp3"

    chunks = []
    async for chunk in synthesize("नमस्ते, आपका स्वागत है", "hi"):
        chunks.append(chunk)

    assert len(chunks) > 0, "No audio chunks received from live TTS"

    with open(out_file, "wb") as f:
        for chunk in chunks:
            f.write(chunk)

    assert out_file.exists(), f"File {out_file} was not created"
    assert out_file.stat().st_size > 100, f"File {out_file} is suspiciously small ({out_file.stat().st_size} bytes)"
