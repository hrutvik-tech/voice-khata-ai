from typing import Literal

Lang = Literal["hi", "kn", "en"]

# Full irregular list of Hindi words for 1 to 99
HINDI_1_TO_99: dict[int, str] = {
    1: "एक",
    2: "दो",
    3: "तीन",
    4: "चार",
    5: "पांच",
    6: "छह",
    7: "सात",
    8: "आठ",
    9: "नौ",
    10: "दस",
    11: "ग्यारह",
    12: "बारह",
    13: "तेरह",
    14: "चौदह",
    15: "पंद्रह",
    16: "सोलह",
    17: "सत्रह",
    18: "अठारह",
    19: "उन्नीस",
    20: "बीस",
    21: "इक्कीस",
    22: "बाइस",
    23: "तेईस",
    24: "चौबीस",
    25: "पच्चीस",
    26: "छब्बीस",
    27: "सत्ताईस",
    28: "अट्ठाईस",
    29: "उनतीस",
    30: "तीस",
    31: "इकतीस",
    32: "बत्तीस",
    33: "तैंतीस",
    34: "चौंतीस",
    35: "पैंतीस",
    36: "छत्तीस",
    37: "सैंतीस",
    38: "अड़तीस",
    39: "उनतालीस",
    40: "चालीस",
    41: "इकतालीस",
    42: "बयालीस",
    43: "तैंतालीस",
    44: "चवालीस",
    45: "पैंतालीस",
    46: "छियालीस",
    47: "सैंतालीस",
    48: "अड़तालीस",
    49: "उनचास",
    50: "पचास",
    51: "इक्यावन",
    52: "बावन",
    53: "तिरपन",
    54: "चौवन",
    55: "पचपन",
    56: "छप्पन",
    57: "सत्तावन",
    58: "अट्ठावन",
    59: "उनसठ",
    60: "साठ",
    61: "इकसठ",
    62: "बासठ",
    63: "तिरसठ",
    64: "चौंसठ",
    65: "पैंसठ",
    66: "छियासठ",
    67: "सरसठ",
    68: "अड़सठ",
    69: "उनहत्तर",
    70: "सत्तर",
    71: "इकहत्तर",
    72: "बहत्तर",
    73: "तिहत्तर",
    74: "चौहत्तर",
    75: "पचहत्तर",
    76: "छिहत्तर",
    77: "सतहत्तर",
    78: "अठहत्तर",
    79: "उन्यासी",
    80: "अस्सी",
    81: "इक्यासी",
    82: "बयासी",
    83: "तिरासी",
    84: "चौरासी",
    85: "पचासी",
    86: "छियासी",
    87: "सत्तासी",
    88: "अट्ठासी",
    89: "नवासी",
    90: "नब्बे",
    91: "इक्यानवे",
    92: "बानवे",
    93: "तिरानवे",
    94: "चौरानवे",
    95: "पचानवे",
    96: "छियानवे",
    97: "सत्तानवे",
    98: "अट्ठानवे",
    99: "निन्यानवे",
}

ENGLISH_1_TO_19: dict[int, str] = {
    1: "one",
    2: "two",
    3: "three",
    4: "four",
    5: "five",
    6: "six",
    7: "seven",
    8: "eight",
    9: "nine",
    10: "ten",
    11: "eleven",
    12: "twelve",
    13: "thirteen",
    14: "fourteen",
    15: "fifteen",
    16: "sixteen",
    17: "seventeen",
    18: "eighteen",
    19: "nineteen",
}

ENGLISH_TENS: dict[int, str] = {
    20: "twenty",
    30: "thirty",
    40: "forty",
    50: "fifty",
    60: "sixty",
    70: "seventy",
    80: "eighty",
    90: "ninety",
}

KANNADA_1_TO_9: dict[int, str] = {
    1: "ಒಂದು",
    2: "ಎರಡು",
    3: "ಮೂರು",
    4: "ನಾಲ್ಕು",
    5: "ಐದು",
    6: "ಆರು",
    7: "ಏಳು",
    8: "ಎಂಟು",
    9: "ಒಂಬತ್ತು",
}

KANNADA_10_TO_19: dict[int, str] = {
    10: "ಹತ್ತು",
    11: "ಹನ್ನೊಂದು",
    12: "ಹನ್ನೆರಡು",
    13: "ಹದಿಮೂರು",
    14: "ಹದಿನಾಲ್ಕು",
    15: "ಹದಿನೈದು",
    16: "ಹದಿನಾರು",
    17: "ಹದಿನೇಳು",
    18: "ಹದಿನೆಂಟು",
    19: "ಹತ್ತೊಂಬತ್ತು",
}

KANNADA_TENS_STANDALONE: dict[int, str] = {
    20: "ಇಪ್ಪತ್ತು",
    30: "ಮೂವತ್ತು",
    40: "ನಲವತ್ತು",
    50: "ಐವತ್ತು",
    60: "ಅರವತ್ತು",
    70: "ಎಪ್ಪತ್ತು",
    80: "ಎಂಬತ್ತು",
    90: "ತೊಂಬತ್ತು",
}

KANNADA_TENS_PREFIX: dict[int, str] = {
    20: "ಇಪ್ಪತ್ತ",
    30: "ಮೂವತ್ತ",
    40: "ನಲವತ್ತ",
    50: "ಐವತ್ತ",
    60: "ಅರವತ್ತ",
    70: "ಎಪ್ಪತ್ತ",
    80: "ಎಂಬತ್ತ",
    90: "ತೊಂಬತ್ತ",
}


def _english_under_100(n: int) -> str:
    if n <= 0:
        return ""
    if n < 20:
        return ENGLISH_1_TO_19[n]
    tens = (n // 10) * 10
    unit = n % 10
    if unit == 0:
        return ENGLISH_TENS[tens]
    return f"{ENGLISH_TENS[tens]} {ENGLISH_1_TO_19[unit]}"


def _kannada_under_100(n: int) -> str:
    if n <= 0:
        return ""
    if n < 10:
        return KANNADA_1_TO_9[n]
    if n < 20:
        return KANNADA_10_TO_19[n]
    tens = (n // 10) * 10
    unit = n % 10
    if unit == 0:
        return KANNADA_TENS_STANDALONE[tens]
    return f"{KANNADA_TENS_PREFIX[tens]}{KANNADA_1_TO_9[unit]}"


def _indian_breakdown(num: int) -> tuple[int, int, int, int, int]:
    """Returns (crore, lakh, thousand, hundred, remainder) in Indian numbering."""
    crore = num // 10_000_000
    rem = num % 10_000_000
    lakh = rem // 100_000
    rem = rem % 100_000
    thousand = rem // 1_000
    rem = rem % 1_000
    hundred = rem // 100
    remainder = rem % 100
    return crore, lakh, thousand, hundred, remainder


def _number_to_hindi(num: int) -> str:
    if num == 0:
        return "शून्य"
    crore, lakh, thousand, hundred, rem = _indian_breakdown(num)
    parts = []
    if crore > 0:
        parts.append(f"{_number_to_hindi(crore)} करोड़")
    if lakh > 0:
        parts.append(f"{HINDI_1_TO_99.get(lakh, _number_to_hindi(lakh))} लाख")
    if thousand > 0:
        parts.append(f"{HINDI_1_TO_99.get(thousand, _number_to_hindi(thousand))} हज़ार")
    if hundred > 0:
        parts.append(f"{HINDI_1_TO_99[hundred]} सौ")
    if rem > 0:
        parts.append(HINDI_1_TO_99[rem])
    return " ".join(parts)


def _number_to_english(num: int) -> str:
    if num == 0:
        return "zero"
    crore, lakh, thousand, hundred, rem = _indian_breakdown(num)
    parts = []
    if crore > 0:
        parts.append(f"{_number_to_english(crore)} crore")
    if lakh > 0:
        parts.append(f"{_english_under_100(lakh)} lakh")
    if thousand > 0:
        parts.append(f"{_english_under_100(thousand)} thousand")
    if hundred > 0:
        parts.append(f"{ENGLISH_1_TO_19[hundred]} hundred")
    if rem > 0:
        parts.append(_english_under_100(rem))
    return " ".join(parts)


def _number_to_kannada(num: int) -> str:
    if num == 0:
        return "ಶೂನ್ಯ"
    crore, lakh, thousand, hundred, rem = _indian_breakdown(num)
    parts = []
    if crore > 0:
        parts.append(f"{_number_to_kannada(crore)} ಕೋಟಿ")
    if lakh > 0:
        parts.append(f"{_kannada_under_100(lakh)} ಲಕ್ಷ")
    if thousand > 0:
        parts.append(f"{_kannada_under_100(thousand)} ಸಾವಿರ")
    if hundred > 0:
        # e.g., "ನಾಲ್ಕು ನೂರ ಮೂವತ್ತು" or "ಮೂರು ನೂರ ನಲವತ್ತು"
        if rem > 0:
            parts.append(f"{KANNADA_1_TO_9[hundred]} ನೂರ")
        else:
            parts.append(f"{KANNADA_1_TO_9[hundred]} ನೂರು")
    if rem > 0:
        parts.append(_kannada_under_100(rem))
    return " ".join(parts)


def rupees_in_words(paise: int, language: Lang) -> str:
    """
    Converts paise into words using the Indian numbering system (hazaar, lakh, crore).
    
    Examples:
      - hi: 43000 -> "चार सौ तीस रुपये"
            100 -> "एक रुपया"
            0 -> "शून्य रुपये"
            12000000 -> "एक लाख बीस हज़ार रुपये"
            34050 -> "तीन सौ चालीस रुपये पचास पैसे"
      - en: 43000 -> "four hundred thirty rupees"
            100 -> "one rupee"
            34050 -> "three hundred forty rupees and fifty paise"
            12000000 -> "one lakh twenty thousand rupees"
      - kn: 100 -> "ಒಂದು ರೂಪಾಯಿ"
            0 -> "ಶೂನ್ಯ ರೂಪಾಯಿಗಳು"
            43000 -> "ನಾಲ್ಕು ನೂರ ಮೂವತ್ತು ರೂಪಾಯಿಗಳು"
            34050 -> "ಮೂರು ನೂರ ನಲವತ್ತು ರೂಪಾಯಿಗಳು ಐವತ್ತು ಪೈಸೆ"
    """
    if paise < 0:
        raise ValueError("Negative paise amount is not allowed")

    rupees = paise // 100
    rem_paise = paise % 100

    if language == "hi":
        if rupees == 0 and rem_paise == 0:
            return "शून्य रुपये"
        parts = []
        if rupees > 0:
            r_words = _number_to_hindi(rupees)
            unit = "रुपया" if rupees == 1 else "रुपये"
            parts.append(f"{r_words} {unit}")
        if rem_paise > 0:
            p_words = HINDI_1_TO_99[rem_paise]
            parts.append(f"{p_words} पैसे")
        return " ".join(parts)

    elif language == "en":
        if rupees == 0 and rem_paise == 0:
            return "zero rupees"
        parts = []
        if rupees > 0:
            r_words = _number_to_english(rupees)
            unit = "one rupee" if rupees == 1 else f"{r_words} rupees"
            parts.append(unit)
        if rem_paise > 0:
            p_words = _english_under_100(rem_paise)
            p_unit = "one paisa" if rem_paise == 1 else f"{p_words} paise"
            if parts:
                parts.append(f"and {p_unit}")
            else:
                parts.append(p_unit)
        return " ".join(parts)

    elif language == "kn":
        if rupees == 0 and rem_paise == 0:
            return "ಶೂನ್ಯ ರೂಪಾಯಿಗಳು"
        parts = []
        if rupees > 0:
            r_words = _number_to_kannada(rupees)
            unit = "ರೂಪಾಯಿ" if rupees == 1 else "ರೂಪಾಯಿಗಳು"
            parts.append(f"{r_words} {unit}")
        if rem_paise > 0:
            p_words = _kannada_under_100(rem_paise)
            parts.append(f"{p_words} ಪೈಸೆ")
        return " ".join(parts)

    else:
        raise ValueError(f"Unsupported language: {language}")
