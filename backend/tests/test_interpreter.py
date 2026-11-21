"""Tests for app.ai.interpreter."""

import json
from unittest.mock import MagicMock, patch
import pytest

from app.ai.interpreter import MIN_CONFIDENCE, interpret


@pytest.mark.asyncio
async def test_fast_path_tried_first():
    """Test that clear phrases match fast_path and skip LLM completely."""
    with patch("app.ai.interpreter._call_gemini_sync") as mock_gemini:
        res = await interpret("Ramesh ne 500 rupaye diye")

        assert res["source"] == "fast_path"
        assert res["customer_name"] == "Ramesh"
        assert res["direction"] == "credit"
        assert res["amount_paise"] == 50000
        # Gemini should not have been called
        mock_gemini.assert_not_called()


@pytest.mark.asyncio
async def test_inquiry_detection_works():
    """Test that balance and summary inquiries are handled without LLM."""
    with patch("app.ai.interpreter._call_gemini_sync") as mock_gemini:
        res = await interpret("Ramesh ka hisab")

        assert res["source"] == "inquiry"
        assert res["intent"] == "check_balance"
        assert res["customer_name"] == "Ramesh"
        mock_gemini.assert_not_called()


@pytest.mark.asyncio
async def test_llm_post_processing():
    """Test LLM response post-processing: amount conversion, date resolution, name normalization."""
    mock_payload = {
        "intent": "add_entry",
        "customer_name": "Ramesh Kumar Ji",
        "amount_rupees": 250.0,
        "direction": "credit",
        "date_reference": "kal",
        "confidence": 0.95,
        "original_text": "ramesh ji ka kal ka 250 jama kar dena",
    }
    mock_resp = MagicMock()
    mock_resp.text = json.dumps(mock_payload)

    with patch.dict("os.environ", {"GEMINI_API_KEY": "fake_test_key"}), \
         patch("app.ai.interpreter._call_gemini_sync", return_value=mock_resp):

        res = await interpret("ramesh ji ka kal ka 250 jama kar dena")

        assert res["source"] == "llm"
        assert res["intent"] == "add_entry"
        # Customer name stripped of honorific 'Ji' and normalized
        assert res["customer_name"] == "ramesh kumar"
        # 250 rupees converted to 25000 paise (integer)
        assert res["amount_paise"] == 25000
        assert isinstance(res["amount_paise"], int)
        assert res["direction"] == "credit"
        assert res["confidence"] == 0.95
        assert "business_date" in res


@pytest.mark.asyncio
async def test_confidence_below_threshold_sets_unclear():
    """Test that low confidence (< MIN_CONFIDENCE) marks intent as unclear."""
    mock_payload = {
        "intent": "add_entry",
        "customer_name": "Unknown",
        "amount_rupees": 100.0,
        "direction": "debit",
        "date_reference": None,
        "confidence": 0.45,  # Below 0.6
        "original_text": "shayad kuch tha",
    }
    mock_resp = MagicMock()
    mock_resp.text = json.dumps(mock_payload)

    with patch.dict("os.environ", {"GEMINI_API_KEY": "fake_test_key"}), \
         patch("app.ai.interpreter._call_gemini_sync", return_value=mock_resp):

        res = await interpret("shayad kuch tha")

        assert res["source"] == "llm"
        assert res["intent"] == "unclear"
        assert res["confidence"] == 0.45


@pytest.mark.asyncio
async def test_error_handling_when_llm_fails():
    """Test graceful error response when Gemini throws or times out."""
    with patch.dict("os.environ", {"GEMINI_API_KEY": "fake_test_key"}), \
         patch("app.ai.interpreter._call_gemini_sync", side_effect=RuntimeError("API Network Error")):

        res = await interpret("sentence requiring llm interpretation")

        assert res["source"] == "llm"
        assert res["intent"] == "error"
        assert res["confidence"] == 0.0
        assert res["error"] == "LLM unavailable"
