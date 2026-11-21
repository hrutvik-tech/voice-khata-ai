"""Tests for app.ai.shop_clock."""

from datetime import date, datetime
from zoneinfo import ZoneInfo
import pytest

from app.ai.shop_clock import (
    DEFAULT_OPEN_HOUR,
    TIMEZONE,
    business_date,
    is_within_business_hours,
    resolve_date,
)

IST = ZoneInfo(TIMEZONE)


def test_business_date_same_day():
    """Test business_date at 10:00 AM on Nov 22 is Nov 22."""
    dt = datetime(2026, 11, 22, 10, 0, tzinfo=IST)
    assert business_date(dt) == date(2026, 11, 22)


def test_business_date_previous_day():
    """Test business_date at 1:00 AM on Nov 22 is Nov 21 (before open_hour=6)."""
    dt = datetime(2026, 11, 22, 1, 0, tzinfo=IST)
    assert business_date(dt) == date(2026, 11, 21)


def test_business_date_exactly_open_hour():
    """Test business_date exactly at open_hour (06:00 AM) is that day."""
    dt = datetime(2026, 11, 22, 6, 0, tzinfo=IST)
    assert business_date(dt) == date(2026, 11, 22)


def test_resolve_date_aaj():
    """Test resolve_date for 'aaj' / 'today'."""
    today = date(2026, 11, 22)
    assert resolve_date("aaj", today=today) == today
    assert resolve_date("today", today=today) == today


def test_resolve_date_kal():
    """Test resolve_date for 'kal' / 'yesterday'."""
    today = date(2026, 11, 22)
    assert resolve_date("kal", today=today) == date(2026, 11, 21)
    assert resolve_date("yesterday", today=today) == date(2026, 11, 21)


def test_resolve_date_parso():
    """Test resolve_date for 'parso' / 'day before yesterday'."""
    today = date(2026, 11, 22)
    assert resolve_date("parso", today=today) == date(2026, 11, 20)
    assert resolve_date("day before yesterday", today=today) == date(2026, 11, 20)


def test_resolve_date_unknown():
    """Test resolve_date for unknown or invalid words returns None."""
    today = date(2026, 11, 22)
    assert resolve_date("somwar", today=today) == None
    assert resolve_date("next week", today=today) == None
    assert resolve_date("", today=today) == None
    assert resolve_date(None, today=today) == None


def test_is_within_business_hours_noon():
    """Test is_within_business_hours at noon (12:00 PM) returns True."""
    dt = datetime(2026, 11, 22, 12, 0, tzinfo=IST)
    assert is_within_business_hours(dt) is True


def test_is_within_business_hours_4am():
    """Test is_within_business_hours at 4:00 AM returns False."""
    dt = datetime(2026, 11, 22, 4, 0, tzinfo=IST)
    assert is_within_business_hours(dt) is False
