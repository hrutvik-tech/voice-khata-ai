"""
backend/app/services/validation.py

Business validation and decision rules for Bolta Khata AI.
Implements amount limits, outlier detection, and matching thresholds.
"""

from datetime import datetime, timezone
from typing import Any
from rapidfuzz import fuzz
from app.services.ledger import credit_stats, normalize_name

MAX_AMOUNT_PAISE = 100000000  # ₹10,00,000
AMEND_WINDOW_SECONDS = 60
DUPLICATE_WINDOW_SECONDS = 120
MIN_CONFIDENCE = 0.6


def check_outlier(customer_id: int, amount_paise: int) -> bool:
    """
    Outlier rule:
    At least 3 earlier active credits, AND
    amount > 5 * median of the last 10 credits, AND
    amount > 200000 paise (₹2,000).
    """
    if amount_paise <= 200000:
        return False

    stats = credit_stats(customer_id)
    if stats["earlier_count"] < 3:
        return False

    median = stats["median_last_10"]
    if median <= 0:
        return False

    return amount_paise > (5 * median)


def match_customer_candidates(name: str, customers: list[dict]) -> list[dict]:
    """
    Matches spoken/provided name against a list of customer references.
    Returns candidates with score >= 75 sorted highest score first.
    """
    norm_query = normalize_name(name)
    candidates = []

    for c in customers:
        c_norm = normalize_name(c.get("name") or "")
        # Compare token sort ratio
        score = fuzz.token_sort_ratio(norm_query, c_norm)
        if score >= 75:
            candidates.append({
                "customer_id": c["id"],
                "name": c["name"],
                "area": c.get("area"),
                "score": float(score),
            })

    candidates.sort(key=lambda x: x["score"], reverse=True)
    return candidates
