"""Tests for app.ai.matching."""

import pytest
from app.ai.matching import (
    MATCH_SAME,
    MATCH_SIMILAR,
    best_match,
    match_customers,
    normalize_name,
)


def test_normalize_name():
    """Test lowercasing, stripping honorifics/titles, and extra whitespace."""
    assert normalize_name("Ramesh Bhai Ji") == "ramesh"
    assert normalize_name("  Sunita   Didi  ") == "sunita"
    assert normalize_name("Gupta Seth Ji") == "gupta"
    assert normalize_name("Sharma Sahab") == "sharma"
    assert normalize_name("Doctor Madam") == "doctor"
    assert normalize_name("") == ""


def test_exact_match():
    """Test exact match yields score >= 90 and confidence 'same'."""
    customers = [{"id": 1, "name": "Ramesh Kumar", "name_key": "ramesh kumar"}]
    matches = match_customers("Ramesh", customers)

    assert len(matches) == 1
    assert matches[0]["customer_id"] == 1
    assert matches[0]["name"] == "Ramesh Kumar"
    assert matches[0]["score"] >= MATCH_SAME
    assert matches[0]["confidence"] == "same"


def test_similar_match():
    """Test typo / partial match yields score 75-89 and confidence 'similar'."""
    customers = [{"id": 1, "name": "Ramesh Kumar", "name_key": "ramesh kumar"}]
    matches = match_customers("Ramsh", customers)

    assert len(matches) == 1
    assert matches[0]["customer_id"] == 1
    assert MATCH_SIMILAR <= matches[0]["score"] < MATCH_SAME
    assert matches[0]["confidence"] == "similar"


def test_no_match():
    """Test completely unrelated name returns an empty list."""
    customers = [{"id": 1, "name": "Ramesh Kumar", "name_key": "ramesh kumar"}]
    assert match_customers("Xyz", customers) == []
    assert match_customers("", customers) == []


def test_best_match_clear_winner():
    """Test best_match returns the customer when exactly one has 'same' confidence."""
    customers = [
        {"id": 1, "name": "Ramesh Kumar", "name_key": "ramesh kumar"},
        {"id": 2, "name": "Suresh Verma", "name_key": "suresh verma"},
    ]
    winner = best_match("Ramesh Bhai", customers)
    assert winner is not None
    assert winner["customer_id"] == 1
    assert winner["confidence"] == "same"


def test_best_match_ambiguous():
    """Test best_match returns None when there are multiple same-confidence matches or only similar."""
    # Two candidates both matching "Ramesh" with score >= 90
    ambiguous_customers = [
        {"id": 1, "name": "Ramesh Kumar", "name_key": "ramesh kumar"},
        {"id": 2, "name": "Ramesh Sharma", "name_key": "ramesh sharma"},
    ]
    assert best_match("Ramesh", ambiguous_customers) is None

    # Only similar candidates (score 75-89), none with 'same'
    single_similar = [{"id": 1, "name": "Ramesh Kumar", "name_key": "ramesh kumar"}]
    assert best_match("Ramsh", single_similar) is None
