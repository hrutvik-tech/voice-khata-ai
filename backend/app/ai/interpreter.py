"""Interpreter engine for Voice Khata AI (Member 3).

This module coordinates spoken language understanding for shop transactions:
1. Deterministic fast-path regex execution (try_fast_path)
2. Direct inquiry detection (detect_inquiry)
3. Structured-output extraction via Google Gemini Flash-Lite / Flash
THE LLM ONLY PROPOSES — it never writes to the database.
"""

from __future__ import annotations

import asyncio
import os
from typing import Any
from google import genai
from pydantic import BaseModel

try:
    from backend.app.ai.fast_path import detect_inquiry, try_fast_path
    from backend.app.ai.matching import normalize_name
    from backend.app.ai.number_parser import parse_amount
    from backend.app.ai.shop_clock import business_date, resolve_date
except ImportError:
    try:
        from app.ai.fast_path import detect_inquiry, try_fast_path
        from app.ai.matching import normalize_name
        from app.ai.number_parser import parse_amount
        from app.ai.shop_clock import business_date, resolve_date
    except ImportError:
        from .fast_path import detect_inquiry, try_fast_path  # type: ignore
        from .matching import normalize_name  # type: ignore
        from .number_parser import parse_amount  # type: ignore
        from .shop_clock import business_date, resolve_date  # type: ignore

# Execution constants
LLM_TIMEOUT: float = 4.0  # seconds
LLM_RETRIES: int = 1  # retry once on failure
MIN_CONFIDENCE: float = 0.6  # below this threshold, mark intent as unclear
MODEL_ID: str = "gemini-3.5-flash-lite"
FALLBACK_MODEL_ID: str = "gemini-3.6-flash"


class LlmInterpretation(BaseModel):
    """Structured Pydantic schema requested from Gemini."""

    intent: str  # "add_entry", "check_balance", "day_summary", "correction", "unknown"
    customer_name: str | None = None
    amount_rupees: float | None = None  # Raw spoken amount in rupees; converted to paise by backend
    direction: str | None = None  # "credit" or "debit"
    date_reference: str | None = None  # "aaj", "kal", "parso", or None
    confidence: float = 1.0  # Model confidence 0.0 to 1.0
    original_text: str = ""  # Echo of transcript


def _call_gemini_sync(client: Any, model: str, prompt: str) -> Any:
    """Helper to execute synchronous generate_content in a background thread."""
    return client.models.generate_content(
        model=model,
        contents=prompt,
        config={
            "response_mime_type": "application/json",
            "response_schema": LlmInterpretation.model_json_schema(),
            "thinking_level": "low",
        },
    )


async def interpret(transcript: Any, shop_context: dict[str, Any] | None = None) -> dict[str, Any]:
    """Interpret a spoken sentence into a proposed ledger operation.

    Order of resolution:
    1. Fast-path regex parser (bypasses LLM for simple patterns)
    2. Inquiry detector (balance checks, daily totals)
    3. Gemini structured JSON call with automatic 1-retry fallback
    Post-processing enforces integer paise and validated business dates.

    Args:
        transcript: Raw transcript string or Transcript object with .text.
        shop_context: Optional context dictionary or Context model.

    Returns:
        Standard proposed operation dictionary.
    """
    raw_text = transcript.text if hasattr(transcript, "text") else str(transcript or "")
    cleaned = raw_text.strip()

    if not cleaned:
        return {
            "intent": "unknown",
            "customer_name": None,
            "amount_paise": None,
            "direction": None,
            "business_date": None,
            "confidence": 0.0,
            "source": "fast_path",
            "raw_transcript": raw_text,
        }

    # Step a: Try fast-path first
    fast_res = try_fast_path(cleaned)
    if fast_res is not None:
        return {
            "intent": fast_res.get("intent", "add_entry"),
            "customer_name": fast_res.get("customer_name"),
            "amount_paise": fast_res.get("amount_paise"),
            "amount": fast_res.get("amount_paise"),
            "direction": fast_res.get("direction"),
            "business_date": fast_res.get("business_date"),
            "confidence": fast_res.get("confidence", 0.95),
            "source": "fast_path",
            "raw_transcript": raw_text,
        }

    # Step b: Try inquiry detection
    inquiry_res = detect_inquiry(cleaned)
    if inquiry_res is not None:
        today_date = business_date()
        return {
            "intent": inquiry_res.get("intent", "check_balance"),
            "customer_name": inquiry_res.get("customer_name"),
            "amount_paise": None,
            "amount": None,
            "direction": None,
            "business_date": today_date.isoformat(),
            "confidence": inquiry_res.get("confidence", 0.95),
            "source": "inquiry",
            "raw_transcript": raw_text,
        }

    # Step c: Call Gemini with structured output
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return {
            "intent": "error",
            "customer_name": None,
            "amount_paise": None,
            "amount": None,
            "direction": None,
            "business_date": None,
            "confidence": 0.0,
            "source": "llm",
            "error": "LLM unavailable",
            "raw_transcript": raw_text,
        }

    prompt = (
        "You are a bookkeeping assistant for an Indian kirana shop.\n"
        "Interpret this spoken Hindi/English sentence and extract the intent.\n"
        "DO NOT calculate amount_paise or business_date — just extract what was said.\n"
        f"The sentence is: {cleaned}"
    )

    client = genai.Client(api_key=api_key)
    parsed_model: LlmInterpretation | None = None

    models_to_try = [MODEL_ID]
    if LLM_RETRIES > 0:
        models_to_try.append(FALLBACK_MODEL_ID)

    for m_id in models_to_try:
        try:
            # Enforce strict LLM_TIMEOUT seconds
            response = await asyncio.wait_for(
                asyncio.to_thread(_call_gemini_sync, client, m_id, prompt),
                timeout=LLM_TIMEOUT,
            )
            resp_text = response.text if hasattr(response, "text") else str(response)
            parsed_model = LlmInterpretation.model_validate_json(resp_text)
            break
        except Exception:
            # Retry next model or fall through to error
            continue

    if parsed_model is None:
        return {
            "intent": "error",
            "customer_name": None,
            "amount_paise": None,
            "amount": None,
            "direction": None,
            "business_date": None,
            "confidence": 0.0,
            "source": "llm",
            "error": "LLM unavailable",
            "raw_transcript": raw_text,
        }

    # Step d: Post-process LLM response
    # 1. Convert amount to integer paise
    amount_paise: int | None = None
    if parsed_model.amount_rupees is not None:
        amount_paise = int(round(parsed_model.amount_rupees * 100))
    else:
        # Fallback to number_parser on transcript
        amount_paise = parse_amount(cleaned)

    # 2. Resolve business date
    res_date = resolve_date(parsed_model.date_reference) if parsed_model.date_reference else None
    active_date = res_date if res_date is not None else business_date()
    business_date_str = active_date.isoformat()

    # 3. Normalize customer name
    cust_name: str | None = None
    if parsed_model.customer_name:
        cust_name = normalize_name(parsed_model.customer_name)

    # 4. Check confidence threshold
    confidence = float(parsed_model.confidence)
    intent = "unclear" if confidence < MIN_CONFIDENCE else parsed_model.intent

    return {
        "intent": intent,
        "customer_name": cust_name,
        "amount_paise": amount_paise,
        "amount": amount_paise,
        "direction": parsed_model.direction,
        "business_date": business_date_str,
        "confidence": confidence,
        "source": "llm",
        "raw_transcript": raw_text,
    }
