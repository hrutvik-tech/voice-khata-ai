import asyncio
import json
import os
from pathlib import Path
import wave
import pytest
import websockets

from app.speech.stt import SttSession, SttError, Transcript


@pytest.fixture
def anyio_backend():
    return "asyncio"


class FakeGnaniServer:
    """Fake Gnani realtime WebSocket server for unit testing."""

    def __init__(self, behavior_fn=None):
        self.behavior_fn = behavior_fn
        self.received_headers = {}
        self.received_messages = []
        self.server = None
        self.port = 0

    async def _handler(self, ws):
        # Capture connection upgrade headers
        if hasattr(ws, "request") and hasattr(ws.request, "headers"):
            self.received_headers = dict(ws.request.headers)
        elif hasattr(ws, "request_headers"):
            self.received_headers = dict(ws.request_headers)

        if self.behavior_fn:
            await self.behavior_fn(ws, self)
        else:
            # Default behavior: send connected, wait for frames & commit, then send transcript
            await ws.send(json.dumps({"type": "connected", "message": "ready"}))
            while True:
                try:
                    msg = await ws.recv()
                    self.received_messages.append(msg)
                    if isinstance(msg, str):
                        data = json.loads(msg)
                        if data.get("type") == "commit":
                            await ws.send(json.dumps({
                                "type": "transcript",
                                "text": "नमस्ते",
                                "segment_index": 1,
                                "is_final": True,
                                "detected_language_code": "hi-IN",
                                "latency": 250,
                            }))
                            break
                except websockets.ConnectionClosed:
                    break

    async def __aenter__(self):
        self.server = await websockets.serve(self._handler, "localhost", 0)
        self.port = self.server.sockets[0].getsockname()[1]
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.server:
            self.server.close()
            await self.server.wait_closed()


@pytest.mark.asyncio
async def test_headers_sent(monkeypatch):
    """Test that SttSession sends all documented connection headers with correct names and values."""
    monkeypatch.setenv("GNANI_API_KEY", "test-api-key-123")
    monkeypatch.setenv("STT_MODEL", "prisma-v3.0")
    monkeypatch.setenv("STT_FORMAT", "codemix")
    monkeypatch.setenv("STT_MIN_SILENCE_MS", "350")
    monkeypatch.setenv("STT_VAD_THRESHOLD", "0.7")

    async with FakeGnaniServer() as fake:
        monkeypatch.setenv("GNANI_STT_WS_URL", f"ws://localhost:{fake.port}")

        session = SttSession(lang_hints=["hi-IN", "en-IN"], keyterms=["Ramesh", "udhaar", "Ramesh"])
        await session.open()
        await session.close()

        headers = fake.received_headers
        assert headers.get("x-api-key-id") == "test-api-key-123"
        assert headers.get("model") == "prisma-v3.0"
        assert headers.get("language_code") == "hi-IN,en-IN"
        assert headers.get("format") == "codemix"
        assert headers.get("x-sample-rate") == "16000"
        assert headers.get("x-min-silence-ms") == "350"
        assert headers.get("x-vad-threshold") == "0.7"
        # Keyterms should be deduplicated JSON array
        assert json.loads(headers.get("keyterms")) == ["Ramesh", "udhaar"]


@pytest.mark.asyncio
async def test_frame_size_enforcement(monkeypatch):
    """Test that send() enforces 1,024-byte frames."""
    monkeypatch.setenv("GNANI_API_KEY", "test-api-key")

    async with FakeGnaniServer() as fake:
        monkeypatch.setenv("GNANI_STT_WS_URL", f"ws://localhost:{fake.port}")

        session = SttSession(lang_hints=["hi-IN"], keyterms=[])
        await session.open()

        # Under 1024 bytes -> ValueError
        with pytest.raises(ValueError, match="1024 bytes"):
            await session.send(b"\x00" * 512)

        # Over 1024 bytes -> ValueError
        with pytest.raises(ValueError, match="1024 bytes"):
            await session.send(b"\x00" * 2048)

        # Exactly 1024 bytes -> Success
        await session.send(b"\x00" * 1024)
        await session.close()


@pytest.mark.asyncio
async def test_commit_frame(monkeypatch):
    """Test that commit() sends the documented commit control frame."""
    monkeypatch.setenv("GNANI_API_KEY", "test-api-key")

    async with FakeGnaniServer() as fake:
        monkeypatch.setenv("GNANI_STT_WS_URL", f"ws://localhost:{fake.port}")

        session = SttSession(lang_hints=["hi-IN"], keyterms=[])
        await session.open()
        await session.send(b"\x00" * 1024)
        await session.commit()
        await session.result(timeout=2.0)
        await session.close()

        # Check commit frame was received by server
        json_frames = [json.loads(m) for m in fake.received_messages if isinstance(m, str)]
        assert any(frame.get("type") == "commit" for frame in json_frames)


@pytest.mark.asyncio
async def test_joining_two_segments(monkeypatch):
    """Test that multiple transcript segments are joined in segment_index order."""
    monkeypatch.setenv("GNANI_API_KEY", "test-api-key")

    async def behavior(ws, fake):
        await ws.send(json.dumps({"type": "connected", "message": "ready"}))
        while True:
            msg = await ws.recv()
            if isinstance(msg, str) and json.loads(msg).get("type") == "commit":
                # Send segments in reverse order to ensure sorting by segment_index works
                await ws.send(json.dumps({
                    "type": "transcript",
                    "text": "340 udhaar",
                    "segment_index": 2,
                    "is_final": True,
                    "detected_language_code": "hi-IN",
                    "latency": 320,
                }))
                await ws.send(json.dumps({
                    "type": "transcript",
                    "text": "Ramesh ka",
                    "segment_index": 1,
                    "is_final": False,
                }))
                break

    async with FakeGnaniServer(behavior_fn=behavior) as fake:
        monkeypatch.setenv("GNANI_STT_WS_URL", f"ws://localhost:{fake.port}")

        session = SttSession(lang_hints=["hi-IN"], keyterms=[])
        await session.open()
        await session.commit()
        res = await session.result(timeout=2.0)
        await session.close()

        assert res.text == "Ramesh ka 340 udhaar"
        assert res.language == "hi"
        assert res.latency_ms == 320


@pytest.mark.asyncio
async def test_language_mapping(monkeypatch):
    """Test mapping detected language codes to 'hi', 'kn', 'en', or None."""
    monkeypatch.setenv("GNANI_API_KEY", "test-api-key")

    for raw_code, expected_mapped in [
        ("hi-IN", "hi"),
        ("kn-IN", "kn"),
        ("en-IN", "en"),
        ("te-IN", None),
        (None, None),
    ]:
        async def behavior(ws, fake, code=raw_code):
            await ws.send(json.dumps({"type": "connected", "message": "ready"}))
            while True:
                msg = await ws.recv()
                if isinstance(msg, str) and json.loads(msg).get("type") == "commit":
                    payload = {
                        "type": "transcript",
                        "text": "sample text",
                        "segment_index": 1,
                        "is_final": True,
                    }
                    if code:
                        payload["detected_language_code"] = code
                    await ws.send(json.dumps(payload))
                    break

        async with FakeGnaniServer(behavior_fn=behavior) as fake:
            monkeypatch.setenv("GNANI_STT_WS_URL", f"ws://localhost:{fake.port}")

            session = SttSession(lang_hints=["hi-IN"], keyterms=[])
            await session.open()
            await session.commit()
            res = await session.result(timeout=2.0)
            await session.close()

            assert res.language == expected_mapped


@pytest.mark.asyncio
async def test_empty_transcript(monkeypatch):
    """Test that an empty transcript is allowed and does not raise an error."""
    monkeypatch.setenv("GNANI_API_KEY", "test-api-key")

    async def behavior(ws, fake):
        await ws.send(json.dumps({"type": "connected", "message": "ready"}))
        while True:
            msg = await ws.recv()
            if isinstance(msg, str) and json.loads(msg).get("type") == "commit":
                await ws.send(json.dumps({
                    "type": "transcript",
                    "text": "",
                    "segment_index": 1,
                    "is_final": True,
                }))
                break

    async with FakeGnaniServer(behavior_fn=behavior) as fake:
        monkeypatch.setenv("GNANI_STT_WS_URL", f"ws://localhost:{fake.port}")

        session = SttSession(lang_hints=["hi-IN"], keyterms=[])
        await session.open()
        await session.commit()
        res = await session.result(timeout=2.0)
        await session.close()

        assert res.text == ""


@pytest.mark.asyncio
async def test_error_message_raises_stt_error(monkeypatch):
    """Test that receiving an error message raises SttError."""
    monkeypatch.setenv("GNANI_API_KEY", "test-api-key")

    async def behavior(ws, fake):
        await ws.send(json.dumps({"type": "connected", "message": "ready"}))
        while True:
            msg = await ws.recv()
            if isinstance(msg, str) and json.loads(msg).get("type") == "commit":
                await ws.send(json.dumps({
                    "type": "error",
                    "message": "Engine failed to recognize audio",
                }))
                break

    async with FakeGnaniServer(behavior_fn=behavior) as fake:
        monkeypatch.setenv("GNANI_STT_WS_URL", f"ws://localhost:{fake.port}")

        session = SttSession(lang_hints=["hi-IN"], keyterms=[])
        await session.open()
        await session.commit()
        with pytest.raises(SttError, match="Engine failed to recognize audio"):
            await session.result(timeout=2.0)
        await session.close()


@pytest.mark.asyncio
async def test_timeout_raises_stt_error(monkeypatch):
    """Test that timing out waiting for transcript raises SttError."""
    monkeypatch.setenv("GNANI_API_KEY", "test-api-key")

    async def behavior(ws, fake):
        await ws.send(json.dumps({"type": "connected", "message": "ready"}))
        # Never send a transcript
        while True:
            await ws.recv()

    async with FakeGnaniServer(behavior_fn=behavior) as fake:
        monkeypatch.setenv("GNANI_STT_WS_URL", f"ws://localhost:{fake.port}")

        session = SttSession(lang_hints=["hi-IN"], keyterms=[])
        await session.open()
        await session.commit()
        with pytest.raises(SttError, match="timed out"):
            await session.result(timeout=0.2)
        await session.close()


@pytest.mark.live
@pytest.mark.asyncio
async def test_live_streaming(monkeypatch):
    """Live integration test streaming test_data/audio/hi_01.wav to Gnani API."""
    if not os.getenv("GNANI_API_KEY"):
        for env_path in [
            Path.cwd() / ".env",
            Path.cwd() / ".env.txt",
            Path(__file__).resolve().parents[2].parent / ".env",
            Path(__file__).resolve().parents[2].parent / ".env.txt",
        ]:
            if env_path.exists():
                lines = [line.strip() for line in env_path.read_text(encoding="utf-8").splitlines() if line.strip()]
                for line in lines:
                    if line.startswith("GNANI_API_KEY="):
                        monkeypatch.setenv("GNANI_API_KEY", line.split("=", 1)[1].strip())
                        break
                    elif line.startswith("vach_"):
                        monkeypatch.setenv("GNANI_API_KEY", line.strip())
                        break
                if os.getenv("GNANI_API_KEY"):
                    break

    assert os.getenv("GNANI_API_KEY"), "GNANI_API_KEY must be set in environment or .env"

    audio_file = Path(__file__).resolve().parents[2].parent / "test_data" / "audio" / "hi_01.wav"
    assert audio_file.exists(), f"Audio file {audio_file} does not exist"

    with wave.open(str(audio_file), "rb") as wf:
        raw_pcm = wf.readframes(wf.getnframes())

    session = SttSession(lang_hints=["hi-IN"], keyterms=["Ramesh", "udhaar"])
    await session.open()

    chunk_size = 1024
    for i in range(0, len(raw_pcm), chunk_size):
        chunk = raw_pcm[i:i + chunk_size]
        if len(chunk) < chunk_size:
            chunk = chunk + b"\x00" * (chunk_size - len(chunk))
        await session.send(chunk)
        await asyncio.sleep(0.032)

    await session.commit()
    res = await session.result(timeout=6.0)
    await session.close()

    assert res.text, "Expected nonempty transcript from live streaming test"
