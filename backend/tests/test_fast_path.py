"""Tests for app.ai.fast_path."""

import pytest
from app.ai.fast_path import detect_inquiry, try_fast_path


def test_credit_pattern():
    """Test credit pattern: 'Ramesh ne 500 rupaye diye'."""
    res = try_fast_path("Ramesh ne 500 rupaye diye")
    assert res is not None
    assert res["customer_name"] == "Ramesh"
    assert res["intent"] == "add_entry"
    assert res["direction"] == "credit"
    assert res["amount_paise"] == 50000
    assert res["amount"] == 50000
    assert res["confidence"] == 0.95
    assert "business_date" in res


def test_debit_pattern():
    """Test debit pattern: 'Ramesh ko 200 ka saman diya'."""
    res = try_fast_path("Ramesh ko 200 ka saman diya")
    assert res is not None
    assert res["customer_name"] == "Ramesh"
    assert res["intent"] == "add_entry"
    assert res["direction"] == "debit"
    assert res["amount_paise"] == 20000
    assert res["amount"] == 20000
    assert res["confidence"] == 0.95


def test_inquiry_check_balance():
    """Test customer balance inquiry: 'Ramesh ka hisab'."""
    res = detect_inquiry("Ramesh ka hisab")
    assert res is not None
    assert res["intent"] == "check_balance"
    assert res["customer_name"] == "Ramesh"
    assert res["confidence"] == 0.95


def test_inquiry_day_summary():
    """Test day summary inquiry: 'aaj ka hisab'."""
    res = detect_inquiry("aaj ka hisab")
    assert res is not None
    assert res["intent"] == "day_summary"
    assert res["customer_name"] is None
    assert res["confidence"] == 0.95


def test_unclear_input_returns_none():
    """Test unclear/ambiguous sentence returns None so LLM handles it."""
    assert try_fast_path("kuch bhi likh do") is None
    assert try_fast_path("hello munshi ji") is None
    assert try_fast_path("") is None
    assert try_fast_path(None) is None
    assert detect_inquiry("hello munshi ji") is None


def test_amount_parse_failure_returns_none():
    """Test input with invalid amount expression returns None."""
    # Pattern matches structure, but amount is not parseable
    assert try_fast_path("Ramesh ne bohot saare rupaye diye") is None
    assert try_fast_path("Ramesh ko xyz rupaye ka saman diya") is None
