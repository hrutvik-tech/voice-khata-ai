import os
from pathlib import Path
import pytest

from app.speech.cli import parse_amount_from_transcript


def test_parse_amount_from_transcript_digits():
    assert parse_amount_from_transcript("रमेश का 340 उधार है") == 34000
    assert parse_amount_from_transcript("सुरेश का 700 दिया") == 70000
    assert parse_amount_from_transcript("रमेश का 40 बाकी") == 4000
    assert parse_amount_from_transcript("ramesh 250 credit") == 25000
    assert parse_amount_from_transcript("koi amount nahi hai") is None
    assert parse_amount_from_transcript(None) is None


def test_cli_overrides_env_variables(monkeypatch):
    monkeypatch.setenv("STT_MIN_SILENCE_MS", "350")
    monkeypatch.setenv("STT_VAD_THRESHOLD", "0.7")

    from app.speech.cli import run_stt_stream
    import asyncio

    # Test with non-existent directory just to verify env overrides apply
    with pytest.raises(SystemExit):
        asyncio.run(
            run_stt_stream(
                "non_existent_folder_123",
                min_silence_override=450,
                vad_threshold_override=0.85,
            )
        )

    assert os.getenv("STT_MIN_SILENCE_MS") == "450"
    assert os.getenv("STT_VAD_THRESHOLD") == "0.85"
