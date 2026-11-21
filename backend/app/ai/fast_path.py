"""Fast-path deterministic parser for Voice Khata AI.

This module detects obvious transaction and inquiry patterns directly from
transcripts using regex to skip LLM calls, reducing latency and cost.
This module only PROPOSES operations; it NEVER writes to the database.
"""

from __future__ import annotations

import re
from typing import Any

try:
    from backend.app.ai.number_parser import parse_amount
    from backend.app.ai.shop_clock import business_date, resolve_date
except ImportError:
    try:
        from app.ai.number_parser import parse_amount
        from app.ai.shop_clock import business_date, resolve_date
    except ImportError:
        from .number_parser import parse_amount  # type: ignore
        from .shop_clock import business_date, resolve_date  # type: ignore

FAST_PATH_CONFIDENCE: float = 0.95

# CREDIT patterns (customer GAVE money):
# "ne ... diye", "ne ... paid", "se ... mila", "ne ... jama", "ne ... diya"
_CREDIT_PATTERNS = [
    re.compile(r"^(?P<name>[A-Za-z\s]+?)\s+ne\s+(?P<amount>.+?)\s+(?:diye|diya|de\s+diye|paid|jama(?:\s*kiye)?)\s*$", re.I),
    re.compile(r"^(?P<name>[A-Za-z\s]+?)\s+se\s+(?P<amount>.+?)\s+(?:mile|mila|jama)\s*$", re.I),
]

# DEBIT patterns (customer TOOK goods or credit):
# "ko ... diya", "ka ... udhar", "ko ... udhaar", "ne ... liya", "ko ... saman"
_DEBIT_PATTERNS = [
    re.compile(r"^(?P<name>[A-Za-z\s]+?)\s+ko\s+(?P<amount>.+?)\s+(?:(?:ka\s+)?saman\s+diya|(?:ka\s+)?maal\s+diya|diya|(?:ka\s+)?udhar|(?:ka\s+)?udhaar)\s*$", re.I),
    re.compile(r"^(?P<name>[A-Za-z\s]+?)\s+ka\s+(?P<amount>.+?)\s+(?:udhar|udhaar)\s*$", re.I),
    re.compile(r"^(?P<name>[A-Za-z\s]+?)\s+ne\s+(?P<amount>.+?)\s+(?:(?:ka\s+)?saman\s+)?(?:liya|le\s+liya)\s*$", re.I),
]

# INQUIRY patterns:
_INQUIRY_DAY_SUMMARY = re.compile(
    r"^(?:aaj\s+ka\s+(?:hisab|hisaab|total|summary)|today'?s\s+total|day\s+summary)\s*$",
    re.I,
)
_INQUIRY_BALANCE_NAMED = re.compile(
    r"^(?P<name>[A-Za-z\s]+?)\s+ka\s+(?:hisab|hisaab|balance|baki|baaki)\s*$",
    re.I,
)
_INQUIRY_BALANCE_UNNAMED = re.compile(
    r"^(?:kitna\s+(?:baki|baaki|balance)\s+hai|balance\s+check)\s*$",
    re.I,
)


def try_fast_path(transcript: str | None) -> dict[str, Any] | None:
    """Attempt deterministic extraction of a transaction from standard Kirana phrases.

    Supported patterns:
    - Credit: "Ramesh ne 500 rupaye diye", "Ramesh se 500 mila"
    - Debit: "Ramesh ko 200 ka saman diya", "Ramesh ka 300 rupaye udhar"

    Args:
        transcript: Spoken text transcript.

    Returns:
        Proposed transaction dict or None if no clear pattern matches.
        Output dictionary:
        {
            "customer_name": str,
            "intent": "add_entry",
            "amount_paise": int,
            "amount": int,  # Alias for amount_paise
            "direction": "credit" | "debit",
            "business_date": str (ISO date),
            "confidence": 0.95
        }
    """
    if not transcript:
        return None

    cleaned = " ".join(transcript.strip().split())
    if not cleaned:
        return None

    customer_name: str | None = None
    amount_str: str | None = None
    direction: str | None = None

    # Check credit patterns
    for pat in _CREDIT_PATTERNS:
        m = pat.match(cleaned)
        if m:
            customer_name = m.group("name").strip()
            amount_str = m.group("amount").strip()
            direction = "credit"
            break

    # Check debit patterns if not matched
    if not direction:
        for pat in _DEBIT_PATTERNS:
            m = pat.match(cleaned)
            if m:
                customer_name = m.group("name").strip()
                amount_str = m.group("amount").strip()
                direction = "debit"
                break

    if not customer_name or not amount_str or not direction:
        return None

    # Disallow known inquiry keywords in customer name
    if customer_name.lower() in {"aaj", "today", "kal", "parso"}:
        return None

    amount_paise = parse_amount(amount_str)
    if amount_paise is None:
        return None

    active_date = business_date()

    return {
        "customer_name": customer_name,
        "intent": "add_entry",
        "amount_paise": amount_paise,
        "amount": amount_paise,
        "direction": direction,
        "business_date": active_date.isoformat(),
        "confidence": FAST_PATH_CONFIDENCE,
    }


def detect_inquiry(transcript: str | None) -> dict[str, Any] | None:
    """Detect non-transaction inquiries such as balance checks or day summaries.

    Args:
        transcript: Spoken text transcript.

    Returns:
        Proposed inquiry dict or None:
        {
            "intent": "check_balance" | "day_summary",
            "customer_name": str | None,
            "confidence": 0.95
        }
    """
    if not transcript:
        return None

    cleaned = " ".join(transcript.strip().split())
    if not cleaned:
        return None

    # Check day summary
    if _INQUIRY_DAY_SUMMARY.match(cleaned):
        return {
            "intent": "day_summary",
            "customer_name": None,
            "confidence": FAST_PATH_CONFIDENCE,
        }

    # Check named balance query
    m = _INQUIRY_BALANCE_NAMED.match(cleaned)
    if m:
        name = m.group("name").strip()
        if name.lower() not in {"aaj", "today"}:
            return {
                "intent": "check_balance",
                "customer_name": name,
                "confidence": FAST_PATH_CONFIDENCE,
            }

    # Check unnamed balance query
    if _INQUIRY_BALANCE_UNNAMED.match(cleaned):
        return {
            "intent": "check_balance",
            "customer_name": None,
            "confidence": FAST_PATH_CONFIDENCE,
        }

    return None
