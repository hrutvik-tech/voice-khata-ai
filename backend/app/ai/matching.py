"""Fuzzy customer name matching for Voice Khata AI.

This module matches spoken customer names against registered customers using
rapidfuzz token ratios.
"""

from __future__ import annotations

import re
from typing import Any
from rapidfuzz import fuzz

# Matching score thresholds (from docs/contracts.md)
MATCH_SAME: int = 90  # score >= 90 means "same person"
MATCH_SIMILAR: int = 75  # score 75-89 means "maybe, ask user"

# Titles and honorifics commonly spoken in Indian retail contexts
_TITLES_RE = re.compile(
    r"\b(bhai|bhaiya|ji|seth|sahab|saheb|didi|madam|sir)\b",
    re.IGNORECASE,
)


def normalize_name(name: str) -> str:
    """Normalize a customer name by lowercasing, stripping titles, and cleaning whitespace.

    Args:
        name: Raw customer name or spoken name string.

    Returns:
        Cleaned, normalized name string.
    """
    if not name:
        return ""

    cleaned = name.lower()
    # Remove common honorific titles
    cleaned = _TITLES_RE.sub(" ", cleaned)
    # Collapse multiple whitespace
    cleaned = " ".join(cleaned.split())
    return cleaned.strip()


def match_customers(spoken_name: str, customers: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Match a spoken name against a list of known customers.

    Args:
        spoken_name: The customer name as heard from speech.
        customers: List of customer dicts containing at least 'id' (or 'customer_id'),
                   'name', and optionally 'name_key'.

    Returns:
        List of matches sorted by score (highest first), each containing:
        - customer_id: int
        - name: str
        - score: int
        - confidence: "same" | "similar" | "no_match"
        Only matches with score >= MATCH_SIMILAR (75) are returned.
    """
    if not spoken_name or not customers:
        return []

    norm_spoken = normalize_name(spoken_name)
    if not norm_spoken:
        return []

    results: list[dict[str, Any]] = []

    for c in customers:
        customer_id = c.get("id") if "id" in c else c.get("customer_id")
        customer_name = c.get("name", "")
        name_key = c.get("name_key") or normalize_name(customer_name)

        if not name_key:
            continue

        # Score against both full name and tokens to handle spoken first names
        score_val = max(
            fuzz.token_sort_ratio(norm_spoken, name_key),
            fuzz.partial_ratio(norm_spoken, name_key),
        )
        score = int(round(score_val))

        if score >= MATCH_SAME:
            confidence = "same"
        elif score >= MATCH_SIMILAR:
            confidence = "similar"
        else:
            continue

        results.append({
            "customer_id": int(customer_id) if customer_id is not None else 0,
            "name": customer_name,
            "score": score,
            "confidence": confidence,
        })

    # Sort candidates by score descending
    results.sort(key=lambda x: x["score"], reverse=True)
    return results


def best_match(spoken_name: str, customers: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Find the single unambiguous best customer match.

    Calls match_customers internally. If exactly ONE candidate has
    confidence 'same' (score >= MATCH_SAME), returns that candidate.
    Otherwise returns None to let the caller handle ambiguity.

    Args:
        spoken_name: The customer name heard.
        customers: List of known customer records.

    Returns:
        The matched customer dict or None.
    """
    matches = match_customers(spoken_name, customers)
    same_matches = [m for m in matches if m["confidence"] == "same"]

    if len(same_matches) == 1:
        return same_matches[0]

    return None
