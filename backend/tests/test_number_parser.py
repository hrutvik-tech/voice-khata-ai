"""Tests for app.ai.number_parser."""

import pytest
from app.ai.number_parser import (
    MAX_AMOUNT_PAISE,
    normalize_amount_words,
    parse_amount,
)


def test_hindi_words():
    """Test standard Hindi words parsing to integer paise."""
    assert parse_amount("pandrah sau rupaye") == 150000
    assert parse_amount("do hazaar paanch sau") == 250000
    assert parse_amount("ek hazar tees") == 103000
    assert parse_amount("paanch sau") == 50000
    assert parse_amount("pachaas rupaye") == 5000


def test_english_words():
    """Test English words and labels."""
    assert parse_amount("250 rupees") == 25000
    assert parse_amount("one thousand rupees") == 100000
    assert parse_amount("two hundred fifty") == 25000


def test_mixed_digits_and_words():
    """Test digits mixed with currency labels and words."""
    assert parse_amount("1500 rupaye") == 150000
    assert parse_amount("₹ 500") == 50000
    assert parse_amount("Rs. 250") == 25000
    assert parse_amount("2 hazaar") == 200000
    assert parse_amount("15 sau") == 150000


def test_multipliers():
    """Test multipliers sau, hazaar, lakh alone and combined."""
    assert parse_amount("do hazaar") == 200000
    assert parse_amount("sau rupaye") == 10000
    assert parse_amount("ek lakh") == 10000000
    assert parse_amount("hazaar rupaye") == 100000


def test_edge_cases():
    """Test empty, None, and unparseable input."""
    assert parse_amount("") is None
    assert parse_amount("   ") is None
    assert parse_amount(None) is None
    assert parse_amount("hello") is None
    assert parse_amount("ramesh ka udhaar") is None
    assert parse_amount("0 rupaye") is None


def test_max_exceeded():
    """Test boundary of MAX_AMOUNT_PAISE (₹10,00,000 = 100_000_000 paise)."""
    # Exact max boundary (10 lakh rupees)
    assert parse_amount("10 lakh rupaye") == MAX_AMOUNT_PAISE
    assert parse_amount("1000000 rupees") == MAX_AMOUNT_PAISE

    # Exceeding max boundary
    assert parse_amount("11 lakh rupaye") is None
    assert parse_amount("1000001 rupees") is None


def test_normalize_amount_words():
    """Test stripping currency words and symbols."""
    assert normalize_amount_words("₹ 1,500 rupaye") == "1500"
    assert normalize_amount_words("Rs. 250 rupees") == "250"
    assert normalize_amount_words("  pandrah sau rupaye  ") == "pandrah sau"
