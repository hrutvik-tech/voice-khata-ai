"""
backend/app/services/replies.py

Spoken reply templates for Bolta Khata AI matching docs/contracts.md.
Supports Hindi and English. Kannada cleanly falls back to Hindi as documented.
"""

from typing import Any

# Kannada fallback: per contracts.md line 112 & 392, Kannada falls back to Hindi.
TEMPLATES = {
    "disclosure": {
        "hi": "नमस्ते, मैं मुंशी हूँ, एक AI सहायक।",
        "en": "Hello, I'm Munshi, an AI assistant.",
    },
    "entry_credit": {
        "hi": "{name} के खाते में {amount} उधार लिख दिया। कुल बाकी {balance}।",
        "en": "Added {amount} credit for {name}. Balance {balance}.",
    },
    "entry_payment": {
        "hi": "{name} से {amount} जमा लिया। कुल बाकी {balance}।",
        "en": "Received {amount} from {name}. Balance {balance}.",
    },
    "entry_amended": {
        "hi": "ठीक है, {name} की एंट्री बदलकर {amount} कर दी। कुल बाकी {balance}।",
        "en": "Changed {name}'s entry to {amount}. Balance {balance}.",
    },
    "entry_undone": {
        "hi": "{name} की {amount} वाली एंट्री हटा दी। कुल बाकी {balance}।",
        "en": "Removed {name}'s {amount} entry. Balance {balance}.",
    },
    "entries_many": {
        "hi": "{count} एंट्री लिख दीं।",
        "en": "Saved {count} entries.",
    },
    "new_customer_prefix": {
        "hi": "नया ग्राहक {name} जोड़ा।",
        "en": "Added new customer {name}.",
    },
    "balance": {
        "hi": "{name} का कुल बाकी {balance} है।",
        "en": "{name} owes {balance}.",
    },
    "balance_zero": {
        "hi": "{name} का कोई बाकी नहीं है।",
        "en": "{name} owes nothing.",
    },
    "balance_advance": {
        "hi": "{name} का {balance} एडवांस जमा है।",
        "en": "{name} has {balance} paid in advance.",
    },
    "daily_total": {
        "hi": "आज कुल {amount} उधार गया।",
        "en": "Total credit today is {amount}.",
    },
    "day_summary": {
        "hi": "आज {credit} उधार गया और {payment} जमा आया। सबसे ज़्यादा बाकी: {top}।",
        "en": "Today {credit} went on credit and {payment} came in. Highest balances: {top}.",
    },
    "choose_customer": {
        "hi": "कौन से? {options}?",
        "en": "Which one: {options}?",
    },
    "confirm_similar": {
        "hi": "क्या आपका मतलब {name} है?",
        "en": "Do you mean {name}?",
    },
    "confirm_amount": {
        "hi": "{amount}, सही है? हाँ या ना बोलिए।",
        "en": "Is {amount} right? Say yes or no.",
    },
    "confirm_direction": {
        "hi": "{name} का {amount} उधार है या जमा?",
        "en": "Is {name}'s {amount} credit or payment?",
    },
    "confirm_duplicate": {
        "hi": "{name} का {amount} अभी लिखा था। दोबारा लिखूँ?",
        "en": "I just saved {amount} for {name}. Save it again?",
    },
    "confirm_amend": {
        "hi": "{name} की पिछली एंट्री बदलकर {amount} कर दूँ?",
        "en": "Change {name}'s last entry to {amount}?",
    },
    "confirm_undo": {
        "hi": "{name} की {amount} वाली एंट्री हटा दूँ?",
        "en": "Remove {name}'s {amount} entry?",
    },
    "cancelled": {
        "hi": "ठीक है, कुछ नहीं लिखा।",
        "en": "Okay, nothing saved.",
    },
    "not_understood": {
        "hi": "समझ नहीं आया, दोबारा बोलिए।",
        "en": "I didn't catch that, please say it again.",
    },
    "nothing_to_undo": {
        "hi": "हटाने के लिए कोई एंट्री नहीं है।",
        "en": "There's no entry to remove.",
    },
    "customer_not_found": {
        "hi": "{name} नाम का कोई ग्राहक नहीं मिला।",
        "en": "No customer named {name}.",
    },
    "not_saved": {
        "hi": "ऑफलाइन एंट्री सेव नहीं हुई, दोबारा बोलिए।",
        "en": "An offline entry wasn't saved. Please say it again.",
    },
    "stt_failed": {
        "hi": "आवाज़ नहीं पहुँची, दोबारा बोलिए।",
        "en": "The voice didn't come through. Please say it again.",
    },
}


def rupees_in_words(paise: int, language: str = "hi") -> str:
    """
    Converts integer paise into spoken currency text.
    Negative paise is converted as absolute value for speech formatting.
    """
    rupees = abs(paise) // 100
    remainder_paise = abs(paise) % 100

    lang = "en" if language == "en" else "hi"

    if lang == "hi":
        if remainder_paise == 0:
            return f"{rupees} रुपये"
        return f"{rupees} रुपये {remainder_paise} पैसे"
    else:
        if remainder_paise == 0:
            return f"₹{rupees}"
        return f"₹{rupees}.{remainder_paise:02d}"


def render_reply(key: str, language: str = "hi", **kwargs: Any) -> str:
    """Renders a reply string from template keys."""
    lang = "en" if language == "en" else "hi"
    template_dict = TEMPLATES.get(key, TEMPLATES["not_understood"])
    template = template_dict.get(lang) or template_dict.get("hi", "")
    return template.format(**kwargs)
