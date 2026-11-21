"""Shop clock and business date resolver for Voice Khata AI.

This module determines the business date for a kirana shop. A business day
runs from open_time (default 06:00) to the next day's open_time.
All operations are evaluated in Asia/Kolkata timezone.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone, tzinfo
from typing import Any
from zoneinfo import ZoneInfo

# Default operating hours and timezone (from docs/contracts.md)
DEFAULT_OPEN_HOUR: int = 6  # 06:00 AM
DEFAULT_CLOSE_HOUR: int = 2  # 02:00 AM next day
TIMEZONE: str = "Asia/Kolkata"


def _get_timezone() -> tzinfo:
    """Return Asia/Kolkata timezone object, falling back to UTC+5:30 if needed."""
    try:
        return ZoneInfo(TIMEZONE)
    except Exception:
        # Fallback for platforms without system tzdata (IST is fixed UTC+05:30)
        return timezone(timedelta(hours=5, minutes=30))


def business_date(
    now: datetime | None = None,
    open_hour: int = DEFAULT_OPEN_HOUR,
    *args: Any,
) -> date:
    """Compute the active business date for a shop based on open_hour.

    If the current local time is between midnight (00:00) and open_hour (06:00),
    the business day is considered yesterday.

    Args:
        now: Reference datetime. If None, current Asia/Kolkata time is used.
        open_hour: Shop opening hour in 24h format (default 6).
        *args: Accepts optional shop/ShopInfo object for contract compatibility.

    Returns:
        The business date as a datetime.date object.
    """
    # Contract compatibility: if second arg is ShopInfo or dict with open_time
    if not isinstance(open_hour, int) and hasattr(open_hour, "open_time"):
        try:
            open_hour = int(open_hour.open_time.split(":")[0])
        except (ValueError, AttributeError):
            open_hour = DEFAULT_OPEN_HOUR

    tz = _get_timezone()

    if now is None:
        local_now = datetime.now(tz)
    elif now.tzinfo is None:
        local_now = now.replace(tzinfo=tz)
    else:
        local_now = now.astimezone(tz)

    if local_now.hour < open_hour:
        return (local_now - timedelta(days=1)).date()

    return local_now.date()


def resolve_date(
    text: str | None,
    today: date | None = None,
    *args: Any,
) -> date | None:
    """Resolve relative spoken date expressions into a concrete date.

    Supports:
    - "aaj", "today" -> today's business date
    - "kal", "yesterday" -> today - 1 day
    - "parso", "day before yesterday" -> today - 2 days

    Args:
        text: Spoken date expression (e.g., "kal", "aaj", "parso").
        today: Reference base date. If None, current business_date() is used.
        *args: Optional compatibility arguments (e.g., moment, shop).

    Returns:
        Resolved date, or None if the expression is unrecognized.
    """
    if not text:
        return None

    cleaned = text.strip().lower()

    # If second arg was a datetime (from contracts: resolve_date(expr, moment, shop))
    if isinstance(today, datetime):
        shop_arg = args[0] if args else None
        today = business_date(now=today, open_hour=DEFAULT_OPEN_HOUR if not hasattr(shop_arg, "open_time") else int(shop_arg.open_time.split(":")[0]))

    if today is None:
        today = business_date()

    if cleaned in {"aaj", "today", "aaj ka", "aaj ki"}:
        return today

    if cleaned in {"kal", "yesterday", "kal ka", "kal ki"}:
        return today - timedelta(days=1)

    if cleaned in {"parso", "parson", "day before yesterday"}:
        return today - timedelta(days=2)

    return None


def is_within_business_hours(
    now: datetime | None = None,
    open_hour: int = DEFAULT_OPEN_HOUR,
    close_hour: int = DEFAULT_CLOSE_HOUR,
) -> bool:
    """Check if the given time falls within the shop's operating hours.

    Operating hours span from open_hour to close_hour (spanning past midnight
    if close_hour < open_hour, e.g., 6:00 AM to 01:59 AM next day).

    Args:
        now: Reference datetime. If None, current Asia/Kolkata time is used.
        open_hour: Shop opening hour (default 6).
        close_hour: Shop closing hour (default 2).

    Returns:
        True if current time is within business hours, False otherwise.
    """
    tz = _get_timezone()

    if now is None:
        local_now = datetime.now(tz)
    elif now.tzinfo is None:
        local_now = now.replace(tzinfo=tz)
    else:
        local_now = now.astimezone(tz)

    h = local_now.hour

    if close_hour < open_hour:
        # Operating window crosses midnight (e.g., 06:00 to 02:00)
        return h >= open_hour or h < close_hour

    return open_hour <= h < close_hour
