"""Spoken money phrase parser for Voice Khata AI.

This module converts spoken Hindi, English, and mixed digit/word phrases into
integer paise (₹1 = 100 paise).
Never use floats for money.
"""

from __future__ import annotations

import re

# Maximum allowed transaction amount: ₹10,00,000 (10 lakh rupees) in paise
MAX_AMOUNT_PAISE: int = 100_000_000

# Multipliers mapping
MULTIPLIERS: dict[str, int] = {
    "sau": 100,
    "hundred": 100,
    "hazaar": 1000,
    "hazar": 1000,
    "thousand": 1000,
    "k": 1000,
    "lakh": 100000,
    "lac": 100000,
}

# Hindi number words mapping
HINDI_UNITS: dict[str, int] = {
    "ek": 1,
    "do": 2,
    "teen": 3,
    "tin": 3,
    "chaar": 4,
    "char": 4,
    "paanch": 5,
    "panch": 5,
    "chhe": 6,
    "che": 6,
    "saat": 7,
    "sat": 7,
    "aath": 8,
    "ath": 8,
    "nau": 9,
    "das": 10,
    "gyarah": 11,
    "gyara": 11,
    "baarah": 12,
    "barah": 12,
    "terah": 13,
    "tera": 13,
    "chaudah": 14,
    "chauda": 14,
    "pandrah": 15,
    "pandra": 15,
    "solah": 16,
    "sola": 16,
    "satrah": 17,
    "satra": 17,
    "aathrah": 18,
    "atharah": 18,
    "athrah": 18,
    "unnees": 19,
    "unnis": 19,
    "bees": 20,
    "bis": 20,
    "ikkees": 21,
    "ikkis": 21,
    "baees": 22,
    "bais": 22,
    "teees": 23,
    "teis": 23,
    "chaubees": 24,
    "chaubis": 24,
    "pachees": 25,
    "pachis": 25,
    "chhabbees": 26,
    "chhabbis": 26,
    "sattaees": 27,
    "sattais": 27,
    "atthaees": 28,
    "atthais": 28,
    "untees": 29,
    "untis": 29,
    "tees": 30,
    "tis": 30,
    "iktees": 31,
    "iktis": 31,
    "battees": 32,
    "battis": 32,
    "taintees": 33,
    "taintis": 33,
    "chauntees": 34,
    "chauntis": 34,
    "paintees": 35,
    "paintis": 35,
    "pantis": 35,
    "chhattees": 36,
    "chhattis": 36,
    "saintees": 37,
    "saintis": 37,
    "adhtees": 38,
    "adhtis": 38,
    "untaalees": 39,
    "untalis": 39,
    "chaalees": 40,
    "chalis": 40,
    "iktaalis": 41,
    "iktalis": 41,
    "bayaalees": 42,
    "bayalis": 42,
    "taintaalis": 43,
    "taintalis": 43,
    "chawalees": 44,
    "chavalis": 44,
    "paintaalis": 45,
    "paintalis": 45,
    "chhiyaalees": 46,
    "chhiyalis": 46,
    "saintaalis": 47,
    "saintalis": 47,
    "adhaalees": 48,
    "adhalis": 48,
    "unchaas": 49,
    "unchas": 49,
    "pachaas": 50,
    "pachas": 50,
    "ikaawan": 51,
    "ikawan": 51,
    "baawan": 52,
    "bawan": 52,
    "tirepan": 53,
    "chauwan": 54,
    "pachpan": 55,
    "chhappan": 56,
    "sattawan": 57,
    "atthaawan": 58,
    "unsath": 59,
    "saath": 60,
    "sath": 60,
    "iksath": 61,
    "baasath": 62,
    "tirasath": 63,
    "chaunsath": 64,
    "painsath": 65,
    "chhiyaasath": 66,
    "sadsath": 67,
    "adsath": 68,
    "unhattar": 69,
    "sattar": 70,
    "ikhattar": 71,
    "bahattar": 72,
    "tihattar": 73,
    "chauhattar": 74,
    "pachhattar": 75,
    "chhihattar": 76,
    "sathattar": 77,
    "athhattar": 78,
    "unassi": 79,
    "assi": 80,
    "ikyaasi": 81,
    "bayaasi": 82,
    "tiraasi": 83,
    "chauraasi": 84,
    "pachaasi": 85,
    "chhiyaasi": 86,
    "sattaasi": 87,
    "atthaasi": 88,
    "nawaasi": 89,
    "nabbe": 90,
    "ikyaanve": 91,
    "baanve": 92,
    "tiraanve": 93,
    "chauraanve": 94,
    "pachaanve": 95,
    "chhiyaanve": 96,
    "sattaanve": 97,
    "atthaanve": 98,
    "ninyaanve": 99,
    # English single/tens units
    "zero": 0,
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "eleven": 11,
    "twelve": 12,
    "thirteen": 13,
    "fourteen": 14,
    "fifteen": 15,
    "sixteen": 16,
    "seventeen": 17,
    "eighteen": 18,
    "nineteen": 19,
    "twenty": 20,
    "thirty": 30,
    "forty": 40,
    "fifty": 50,
    "sixty": 60,
    "seventy": 70,
    "eighty": 80,
    "ninety": 90,
}


def normalize_amount_words(text: str) -> str:
    """Normalize money text by stripping currency labels, lowercasing, and cleaning whitespace.

    Args:
        text: Raw input string containing money words or symbols.

    Returns:
        Cleaned lowercase string without currency labels.
    """
    if not text:
        return ""

    cleaned = text.lower()
    # Strip currency symbols
    cleaned = cleaned.replace("₹", " ")
    # Strip commas in numbers like 1,500
    cleaned = cleaned.replace(",", "")
    # Strip currency words (rupaye, rupees, rs, rs., inr, etc.)
    cleaned = re.sub(r"\brs\.?(?=\s|$)|(?<=\b)(rupees?|rupaye?|rupiye?|rupya|rupee|inr)\b", " ", cleaned)
    # Collapse multiple whitespace
    cleaned = " ".join(cleaned.split())
    return cleaned.strip()


def parse_amount(text: str | None) -> int | None:
    """Parse spoken Hindi, English, and numeric money expressions into integer paise.

    Rules:
    - ₹1 = 100 paise.
    - Money is integer paise everywhere; never uses floats.
    - If amount > MAX_AMOUNT_PAISE (100_000_000 paise = ₹10 lakh) or <= 0, returns None.
    - Returns None for anything unparseable.

    Args:
        text: Raw string like 'pandrah sau rupaye', '250 rupees', 'do hazaar paanch sau'.

    Returns:
        Amount in integer paise, or None if parsing fails.
    """
    if not text:
        return None

    cleaned = normalize_amount_words(text)
    if not cleaned:
        return None

    # Handle direct pure digit string (e.g., "250", "1500")
    if cleaned.isdigit():
        rupees = int(cleaned)
        if rupees <= 0:
            return None
        amount_paise = rupees * 100
        return amount_paise if amount_paise <= MAX_AMOUNT_PAISE else None

    tokens = cleaned.split()
    total_rupees = 0
    current_block = 0

    for token in tokens:
        # Check multiplier words (sau, hazaar, lakh, hundred, thousand, etc.)
        if token in MULTIPLIERS:
            mult = MULTIPLIERS[token]
            if current_block == 0:
                current_block = 1
            total_rupees += current_block * mult
            current_block = 0
        # Check numeric digits (e.g., "15", "250")
        elif token.isdigit():
            val = int(token)
            if val < 0:
                return None
            if current_block == 0:
                current_block = val
            else:
                current_block += val
        # Check Hindi/English unit words
        elif token in HINDI_UNITS:
            val = HINDI_UNITS[token]
            # Handle combinations like "twenty" (20) + "five" (5)
            if current_block in {20, 30, 40, 50, 60, 70, 80, 90} and val < 10:
                current_block += val
            elif current_block == 0:
                current_block = val
            else:
                current_block += val
        else:
            # Unrecognized token - never guess
            return None

    total_rupees += current_block

    if total_rupees <= 0:
        return None

    amount_paise = total_rupees * 100

    if amount_paise > MAX_AMOUNT_PAISE:
        return None

    return amount_paise
