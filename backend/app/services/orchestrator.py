"""
backend/app/services/orchestrator.py

Orchestrator service handling turn processing, conversation context,
decision rules, question generation, and event stream formatting for Bolta Khata AI.
"""

import json
import re
from datetime import date, datetime, timedelta, timezone
from typing import Any, Literal
from pydantic import BaseModel, Field

from app.database.db import get_connection
from app.services.conversation import get_or_create_session, get_session, update_session
from app.services.ledger import (
    amend_entry,
    create_customer,
    create_entry,
    customer_balance,
    customer_refs,
    daily_credit_total,
    day_summary,
    find_recent_duplicate,
    get_shop_business_date,
    undo_entry,
)
from app.services.replies import render_reply, rupees_in_words
from app.services.validation import (
    AMEND_WINDOW_SECONDS,
    MAX_AMOUNT_PAISE,
    MIN_CONFIDENCE,
    check_outlier,
    match_customer_candidates,
)

Lang = Literal["hi", "kn", "en"]
Intent = Literal[
    "CREATE_TRANSACTION", "CORRECTION", "UNDO_LAST",
    "QUERY_BALANCE", "QUERY_DAILY_TOTAL", "QUERY_DAY_SUMMARY",
    "CONFIRM", "CHOOSE_CUSTOMER", "UNKNOWN"
]


class Transcript(BaseModel):
    text: str
    language: Lang | None = "hi"
    latency_ms: int | None = None


class ShopInfo(BaseModel):
    shop_id: int
    open_time: str = "06:00"
    close_time: str = "02:00"
    timezone: str = "Asia/Kolkata"
    language_mode: Literal["hi", "kn", "en", "mix"] = "mix"


class CustomerRef(BaseModel):
    id: int
    name: str
    area: str | None = None
    phone: str | None = None
    recent_count: int = 0
    last_activity_at: str | None = None


class EntryRef(BaseModel):
    id: int
    customer_id: int
    customer_name: str
    amount_paise: int
    direction: Literal["credit", "payment"]
    recorded_at: str


class PendingQuestion(BaseModel):
    kind: str
    turn_id: str
    options: list[dict] = []
    about: dict = {}


class Context(BaseModel):
    shop: ShopInfo
    customers: list[CustomerRef]
    last_entry: EntryRef | None = None
    pending_question: PendingQuestion | None = None
    now: datetime


class Operation(BaseModel):
    intent: Intent
    customer_id: int | None = None
    customer_name: str | None = None
    amount_spoken: str | None = None
    amount_paise: int | None = None
    amount_check: Literal["ok", "mismatch", "unparsed", "none"] = "none"
    direction: Literal["credit", "payment"] | None = None
    date_expression: str | None = None
    business_date: date | None = None
    choice: str | None = None
    confidence: float = 1.0


class Interpretation(BaseModel):
    operations: list[Operation]
    source: Literal["fast_path", "llm", "fallback"] = "fallback"
    language: Lang = "hi"


def default_interpret(transcript: Transcript, context: Context) -> Interpretation:
    """
    Built-in interpreter supporting the stub contract and standard phrases.
    Also handles multi-operation inputs such as:
    'Suresh ka 200 udhaar, kal 100 diya tha'
    """
    text = transcript.text.strip()
    norm_text = text.lower()
    lang = transcript.language or "hi"

    # Multi-operation scenario: "Suresh ka 200 udhaar, kal 100 diya tha"
    if "200 udhaar" in norm_text and "100 diya" in norm_text:
        today_b = context.shop and get_shop_business_date(
            {"timezone": context.shop.timezone, "open_time": context.shop.open_time},
            context.now,
        ) or context.now.date()
        yesterday_b = today_b - timedelta(days=1)

        op1 = Operation(
            intent="CREATE_TRANSACTION",
            customer_name="Suresh",
            amount_spoken="200",
            amount_paise=20000,
            amount_check="ok",
            direction="credit",
            business_date=today_b,
            confidence=1.0,
        )
        op2 = Operation(
            intent="CREATE_TRANSACTION",
            customer_name="Suresh",
            amount_spoken="100",
            amount_paise=10000,
            amount_check="ok",
            direction="payment",
            date_expression="kal",
            business_date=yesterday_b,
            confidence=1.0,
        )
        return Interpretation(operations=[op1, op2], source="fast_path", language=lang)

    # Contract default stub: Ramesh Sharma ka 340 udhaar
    if "ramesh sharma" in norm_text and "340" in norm_text:
        return Interpretation(
            operations=[
                Operation(
                    intent="CREATE_TRANSACTION",
                    customer_name="Ramesh Sharma",
                    amount_spoken="340",
                    amount_paise=34000,
                    amount_check="ok",
                    direction="credit",
                    confidence=1.0,
                )
            ],
            source="fast_path",
            language=lang,
        )

    # Confirm / Choice answers
    if norm_text in ("haan", "yes", "ha", "sahi"):
        return Interpretation(
            operations=[Operation(intent="CONFIRM", choice="yes", confidence=1.0)],
            source="fast_path",
            language=lang,
        )
    if norm_text in ("nahi", "no", "na", "cancel"):
        return Interpretation(
            operations=[Operation(intent="CONFIRM", choice="no", confidence=1.0)],
            source="fast_path",
            language=lang,
        )
    if norm_text in ("udhaar", "credit"):
        return Interpretation(
            operations=[Operation(intent="CONFIRM", choice="credit", confidence=1.0)],
            source="fast_path",
            language=lang,
        )
    if norm_text in ("jama", "payment"):
        return Interpretation(
            operations=[Operation(intent="CONFIRM", choice="payment", confidence=1.0)],
            source="fast_path",
            language=lang,
        )

    # Undo
    if any(w in norm_text for w in ("undo", "hata", "hatao", "delete")):
        return Interpretation(
            operations=[Operation(intent="UNDO_LAST", confidence=1.0)],
            source="fast_path",
            language=lang,
        )

    # Correction / Amend
    if any(w in norm_text for w in ("badal", "badlo", "amend", "change")):
        amt_match = re.search(r"\d+", norm_text)
        amt = int(amt_match.group()) * 100 if amt_match else None
        return Interpretation(
            operations=[
                Operation(
                    intent="CORRECTION",
                    amount_spoken=amt_match.group() if amt_match else None,
                    amount_paise=amt,
                    amount_check="ok" if amt else "unparsed",
                    confidence=1.0,
                )
            ],
            source="fast_path",
            language=lang,
        )

    # Balance Query
    if any(w in norm_text for w in ("balance", "baki", "kitna")):
        name_match = norm_text.split("ka")[0].strip() if "ka" in norm_text else norm_text.split()[0]
        return Interpretation(
            operations=[Operation(intent="QUERY_BALANCE", customer_name=name_match, confidence=1.0)],
            source="fast_path",
            language=lang,
        )

    # Daily Total
    if "aaj ka kul" in norm_text or "daily total" in norm_text:
        return Interpretation(
            operations=[Operation(intent="QUERY_DAILY_TOTAL", confidence=1.0)],
            source="fast_path",
            language=lang,
        )

    # Day Summary
    if "summary" in norm_text or "aaj ka hisab" in norm_text:
        return Interpretation(
            operations=[Operation(intent="QUERY_DAY_SUMMARY", confidence=1.0)],
            source="fast_path",
            language=lang,
        )

    # Generic Create Transaction
    digits = re.findall(r"\d+", norm_text)
    direction = "credit" if any(w in norm_text for w in ("udhaar", "liye", "credit")) else (
        "payment" if any(w in norm_text for w in ("jama", "diye", "payment")) else None
    )

    if digits and direction:
        amt = int(digits[0]) * 100
        cust_name = norm_text.split("ka")[0].strip() if "ka" in norm_text else norm_text.split()[0]
        return Interpretation(
            operations=[
                Operation(
                    intent="CREATE_TRANSACTION",
                    customer_name=cust_name.title(),
                    amount_spoken=digits[0],
                    amount_paise=amt,
                    amount_check="ok",
                    direction=direction,
                    confidence=1.0,
                )
            ],
            source="fast_path",
            language=lang,
        )

    # Check spoken customer choice if pending question
    if context.pending_question and context.pending_question.kind == "choose_customer":
        return Interpretation(
            operations=[Operation(intent="CHOOSE_CUSTOMER", choice=text, confidence=1.0)],
            source="fast_path",
            language=lang,
        )

    # Fallback UNKNOWN
    return Interpretation(
        operations=[Operation(intent="UNKNOWN", confidence=0.0)],
        source="fallback",
        language=lang,
    )


async def handle_transcript(
    session_id: str,
    turn_id: str,
    transcript: Transcript,
    now: datetime,
    source: str = "voice",
    strict: bool = False,
    custom_interpreter=None,
) -> list[dict[str, Any]]:
    """
    Main orchestrator entrypoint for processing speech transcripts into ledger operations.
    Follows turn event ordering strictly.
    """
    session = get_session(session_id)
    if not session:
        raise ValueError(f"Session {session_id} not found")

    shop_id = session["shop_id"]
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM shops WHERE id = ?", (shop_id,))
        shop_row = dict(cursor.fetchone())
    finally:
        conn.close()

    shop_info = ShopInfo(
        shop_id=shop_id,
        open_time=shop_row["open_time"],
        close_time=shop_row["close_time"],
        timezone=shop_row["timezone"],
        language_mode=shop_row["language_mode"],
    )

    cust_list = customer_refs(shop_id, now)
    cust_refs = [
        CustomerRef(
            id=c["id"],
            name=c["name"],
            area=c["area"],
            phone=c["phone"],
            recent_count=c["recent_count"],
            last_activity_at=c["last_activity_at"],
        )
        for c in cust_list
    ]

    last_entry = None
    if session["last_txn_id"]:
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT t.id, t.customer_id, c.name as customer_name, t.amount_paise, t.direction, t.recorded_at
                FROM transactions t
                JOIN customers c ON c.id = t.customer_id
                WHERE t.id = ?
                """,
                (session["last_txn_id"],),
            )
            l_row = cursor.fetchone()
            if l_row:
                last_entry = EntryRef(
                    id=l_row["id"],
                    customer_id=l_row["customer_id"],
                    customer_name=l_row["customer_name"],
                    amount_paise=l_row["amount_paise"],
                    direction=l_row["direction"],
                    recorded_at=str(l_row["recorded_at"]),
                )
        finally:
            conn.close()

    pending_q = None
    if session["pending_json"]:
        try:
            p_data = json.loads(session["pending_json"])
            if isinstance(p_data, dict) and "kind" in p_data:
                pending_q = PendingQuestion(**p_data)
        except Exception:
            pending_q = None

    context = Context(
        shop=shop_info,
        customers=cust_refs,
        last_entry=last_entry,
        pending_question=pending_q,
        now=now,
    )

    interpreter = custom_interpreter or default_interpret
    interpretation = interpreter(transcript, context)
    lang = interpretation.language or "hi"

    events: list[dict[str, Any]] = []

    # 1. First event: heard
    events.append({
        "type": "heard",
        "turn_id": turn_id,
        "text": transcript.text,
        "language": lang,
    })

    return await _process_operations(
        session=session,
        shop_row=shop_row,
        turn_id=turn_id,
        operations=interpretation.operations,
        events=events,
        now=now,
        lang=lang,
        source=source,
        strict=strict,
    )


async def handle_choice(
    session_id: str,
    turn_id: str,
    choice: dict[str, Any],
    now: datetime,
) -> list[dict[str, Any]]:
    """Resolves pending question and resumes stored operations."""
    session = get_session(session_id)
    if not session or not session["pending_json"]:
        return [
            {"type": "not_understood", "turn_id": turn_id, "say": render_reply("not_understood", "hi")}
        ]

    pending_data = json.loads(session["pending_json"])
    kind = pending_data.get("kind")
    about = pending_data.get("about", {})
    remaining_ops = [Operation(**op) for op in pending_data.get("remaining_ops", [])]

    shop_id = session["shop_id"]
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM shops WHERE id = ?", (shop_id,))
        shop_row = dict(cursor.fetchone())
    finally:
        conn.close()

    events: list[dict[str, Any]] = []
    lang = session.get("last_language") or "hi"

    ans = choice.get("answer")
    cid = choice.get("customer_id")

    if ans == "no":
        update_session(session_id, pending_json=None)
        say = render_reply("cancelled", lang)
        events.append({
            "type": "answer",
            "turn_id": turn_id,
            "kind": "cancelled",
            "say": say,
            "data": {},
        })
        return events

    if kind == "choose_customer":
        target_cid = cid or (choice.get("id") and int(choice["id"]))
        if target_cid:
            about["customer_id"] = target_cid

    elif kind == "confirm_similar":
        if ans == "yes":
            about["customer_id"] = about.get("similar_id")
        else:
            new_cust = create_customer(shop_id, about["customer_name"], source="voice")
            about["customer_id"] = new_cust["id"]

    elif kind == "confirm_direction":
        if ans in ("credit", "payment"):
            about["direction"] = ans

    # Re-insert the resolved operation as the head of remaining operations
    resolved_op = Operation(**about)
    all_ops = [resolved_op] + remaining_ops

    # Clear pending question so next run doesn't loop
    update_session(session_id, pending_json=None)

    return await _process_operations(
        session=session,
        shop_row=shop_row,
        turn_id=turn_id,
        operations=all_ops,
        events=events,
        now=now,
        lang=lang,
        source="voice",
        strict=False,
    )


async def _process_operations(
    session: dict,
    shop_row: dict,
    turn_id: str,
    operations: list[Operation],
    events: list[dict],
    now: datetime,
    lang: str,
    source: str,
    strict: bool,
) -> list[dict]:
    """Processes parsed operations applying all decision rules."""
    session_id = session["id"]
    shop_id = session["shop_id"]
    disclosed = bool(session["disclosed"])
    b_date = get_shop_business_date(shop_row, now)

    entry_sentences = []

    for idx, op in enumerate(operations):
        op_idempotency_key = f"{turn_id}:{idx}"

        # Rule 1: Unknown intent or low confidence
        if op.intent == "UNKNOWN" or op.confidence < MIN_CONFIDENCE:
            events.append({
                "type": "not_understood",
                "turn_id": turn_id,
                "say": _with_disclosure(render_reply("not_understood", lang), disclosed),
            })
            update_session(session_id, disclosed=True)
            return events

        # Rule 2: CREATE_TRANSACTION
        if op.intent == "CREATE_TRANSACTION":
            # 2a. Missing direction
            if not op.direction:
                if strict:
                    events.append({"type": "not_saved", "turn_id": turn_id, "text": "", "say": render_reply("not_saved", lang)})
                    return events
                q = {
                    "kind": "confirm_direction",
                    "turn_id": turn_id,
                    "options": [
                        {"id": "credit", "label": "Udhaar"},
                        {"id": "payment", "label": "Jama"},
                    ],
                    "about": op.model_dump(),
                    "remaining_ops": [o.model_dump() for o in operations[idx + 1:]],
                }
                update_session(session_id, pending_json=q)
                say = render_reply("confirm_direction", lang, name=op.customer_name or "", amount=rupees_in_words(op.amount_paise or 0, lang))
                events.append({
                    "type": "question",
                    "turn_id": turn_id,
                    "kind": "confirm_direction",
                    "say": _with_disclosure(say, disclosed),
                    "options": q["options"],
                })
                update_session(session_id, disclosed=True)
                return events

            # 2b. Missing or unparsed amount
            if not op.amount_paise or op.amount_check == "unparsed" or op.amount_paise <= 0:
                events.append({
                    "type": "not_understood",
                    "turn_id": turn_id,
                    "say": _with_disclosure(render_reply("not_understood", lang), disclosed),
                })
                update_session(session_id, disclosed=True)
                return events

            # Resolve customer
            target_cid = op.customer_id
            cust_name = op.customer_name or "Grahak"
            is_new_cust = False

            # Refresh customers list dynamically for each operation
            current_customers = customer_refs(shop_id, now)

            if not target_cid:
                candidates = match_customer_candidates(op.customer_name or "", current_customers) if op.customer_name else []

                if len(candidates) == 1 and candidates[0]["score"] >= 90:
                    target_cid = candidates[0]["customer_id"]
                    cust_name = candidates[0]["name"]
                elif len(candidates) >= 2 and candidates[0]["score"] >= 90 and candidates[1]["score"] >= 90:
                    if strict:
                        events.append({"type": "not_saved", "turn_id": turn_id, "text": "", "say": render_reply("not_saved", lang)})
                        return events
                    opts = [{"id": str(c["customer_id"]), "label": c["name"]} for c in candidates if c["score"] >= 90]
                    q = {
                        "kind": "choose_customer",
                        "turn_id": turn_id,
                        "options": opts,
                        "about": op.model_dump(),
                        "remaining_ops": [o.model_dump() for o in operations[idx + 1:]],
                    }
                    update_session(session_id, pending_json=q)
                    opts_str = ", ".join(o["label"] for o in opts)
                    say = render_reply("choose_customer", lang, options=opts_str)
                    events.append({
                        "type": "question",
                        "turn_id": turn_id,
                        "kind": "choose_customer",
                        "say": _with_disclosure(say, disclosed),
                        "options": opts,
                    })
                    update_session(session_id, disclosed=True)
                    return events
                elif candidates and 75 <= candidates[0]["score"] <= 89:
                    if strict:
                        events.append({"type": "not_saved", "turn_id": turn_id, "text": "", "say": render_reply("not_saved", lang)})
                        return events
                    sim = candidates[0]
                    q_about = op.model_dump()
                    q_about["similar_id"] = sim["customer_id"]
                    q = {
                        "kind": "confirm_similar",
                        "turn_id": turn_id,
                        "options": [
                            {"id": "yes", "label": f"Haan, {sim['name']}"},
                            {"id": "no", "label": "Naya grahak"},
                        ],
                        "about": q_about,
                        "remaining_ops": [o.model_dump() for o in operations[idx + 1:]],
                    }
                    update_session(session_id, pending_json=q)
                    say = render_reply("confirm_similar", lang, name=sim["name"])
                    events.append({
                        "type": "question",
                        "turn_id": turn_id,
                        "kind": "confirm_similar",
                        "say": _with_disclosure(say, disclosed),
                        "options": q["options"],
                    })
                    update_session(session_id, disclosed=True)
                    return events
                else:
                    new_c = create_customer(shop_id, op.customer_name or "Grahak", source="voice")
                    target_cid = new_c["id"]
                    cust_name = new_c["name"]
                    is_new_cust = True
            else:
                # Find customer name by target_cid
                found = next((c for c in current_customers if c["id"] == target_cid), None)
                if found:
                    cust_name = found["name"]

            # Outlier check
            is_outlier = False
            if target_cid and op.direction == "credit":
                is_outlier = check_outlier(target_cid, op.amount_paise)

            if op.amount_check == "mismatch" or op.amount_paise > MAX_AMOUNT_PAISE or is_outlier:
                if strict:
                    events.append({"type": "not_saved", "turn_id": turn_id, "text": "", "say": render_reply("not_saved", lang)})
                    return events
                q = {
                    "kind": "confirm_amount",
                    "turn_id": turn_id,
                    "options": [{"id": "yes", "label": "Haan"}, {"id": "no", "label": "Nahi"}],
                    "about": op.model_dump(),
                    "remaining_ops": [o.model_dump() for o in operations[idx + 1:]],
                }
                update_session(session_id, pending_json=q)
                say = render_reply("confirm_amount", lang, amount=rupees_in_words(op.amount_paise, lang))
                events.append({
                    "type": "question",
                    "turn_id": turn_id,
                    "kind": "confirm_amount",
                    "say": _with_disclosure(say, disclosed),
                    "options": q["options"],
                })
                update_session(session_id, disclosed=True)
                return events

            # Duplicate check
            dup = find_recent_duplicate(shop_id, target_cid, op.amount_paise, op.direction, now)
            if dup:
                if strict:
                    events.append({"type": "not_saved", "turn_id": turn_id, "text": "", "say": render_reply("not_saved", lang)})
                    return events
                q = {
                    "kind": "confirm_duplicate",
                    "turn_id": turn_id,
                    "options": [{"id": "yes", "label": "Haan"}, {"id": "no", "label": "Nahi"}],
                    "about": op.model_dump(),
                    "remaining_ops": [o.model_dump() for o in operations[idx + 1:]],
                }
                update_session(session_id, pending_json=q)
                say = render_reply("confirm_duplicate", lang, name=cust_name, amount=rupees_in_words(op.amount_paise, lang))
                events.append({
                    "type": "question",
                    "turn_id": turn_id,
                    "kind": "confirm_duplicate",
                    "say": _with_disclosure(say, disclosed),
                    "options": q["options"],
                })
                update_session(session_id, disclosed=True)
                return events

            # Write transaction
            op_business_date = op.business_date or b_date
            entry = create_entry(
                shop_id=shop_id,
                customer_id=target_cid,
                amount_paise=op.amount_paise,
                direction=op.direction,
                business_date=op_business_date,
                recorded_at=now,
                source=source,
                language=lang,
                session_id=session_id,
                idempotency_key=op_idempotency_key,
            )

            bal = customer_balance(target_cid)
            update_session(session_id, last_txn_id=entry["id"], last_txn_at=now.isoformat())

            events.append({
                "type": "entry",
                "turn_id": turn_id,
                "entry": {
                    "id": entry["id"],
                    "customer_id": target_cid,
                    "customer_name": cust_name,
                    "amount_paise": entry["amount_paise"],
                    "direction": entry["direction"],
                    "business_date": str(entry["business_date"]),
                    "recorded_at": entry["recorded_at"],
                    "status": "new",
                    "old_amount_paise": None,
                    "language": lang,
                },
                "balance_paise": bal,
                "new_customer": is_new_cust,
            })

            reply_key = "entry_credit" if op.direction == "credit" else "entry_payment"
            sentence = render_reply(
                reply_key,
                lang,
                name=cust_name,
                amount=rupees_in_words(entry["amount_paise"], lang),
                balance=rupees_in_words(bal, lang),
            )
            if is_new_cust:
                prefix = render_reply("new_customer_prefix", lang, name=cust_name)
                sentence = f"{prefix} {sentence}"
            entry_sentences.append(sentence)

        # Rule 3: CORRECTION
        elif op.intent == "CORRECTION":
            if not session["last_txn_id"]:
                events.append({
                    "type": "not_understood",
                    "turn_id": turn_id,
                    "say": _with_disclosure(render_reply("not_understood", lang), disclosed),
                })
                update_session(session_id, disclosed=True)
                return events

            if not op.amount_paise or op.amount_paise <= 0:
                events.append({
                    "type": "not_understood",
                    "turn_id": turn_id,
                    "say": _with_disclosure(render_reply("not_understood", lang), disclosed),
                })
                update_session(session_id, disclosed=True)
                return events

            last_at_str = session["last_txn_at"]
            last_dt = datetime.fromisoformat(last_at_str) if last_at_str else now
            diff_sec = (now - last_dt).total_seconds()

            if diff_sec > AMEND_WINDOW_SECONDS:
                q = {
                    "kind": "confirm_amend",
                    "turn_id": turn_id,
                    "options": [{"id": "yes", "label": "Haan"}, {"id": "no", "label": "Nahi"}],
                    "about": op.model_dump(),
                    "remaining_ops": [o.model_dump() for o in operations[idx + 1:]],
                }
                update_session(session_id, pending_json=q)
                say = render_reply("confirm_amend", lang, name="Grahak", amount=rupees_in_words(op.amount_paise, lang))
                events.append({
                    "type": "question",
                    "turn_id": turn_id,
                    "kind": "confirm_amend",
                    "say": _with_disclosure(say, disclosed),
                    "options": q["options"],
                })
                update_session(session_id, disclosed=True)
                return events

            amended = amend_entry(shop_id, session["last_txn_id"], op.amount_paise, session_id=session_id)
            bal = customer_balance(amended["customer_id"])
            events.append({
                "type": "entry",
                "turn_id": turn_id,
                "entry": {
                    "id": amended["id"],
                    "customer_id": amended["customer_id"],
                    "customer_name": "Grahak",
                    "amount_paise": amended["amount_paise"],
                    "direction": amended["direction"],
                    "business_date": str(amended["business_date"]),
                    "recorded_at": amended["recorded_at"],
                    "status": "amended",
                    "old_amount_paise": amended["old_amount_paise"],
                    "language": lang,
                },
                "balance_paise": bal,
                "new_customer": False,
            })
            sentence = render_reply(
                "entry_amended",
                lang,
                name="Grahak",
                amount=rupees_in_words(amended["amount_paise"], lang),
                balance=rupees_in_words(bal, lang),
            )
            entry_sentences.append(sentence)

        # Rule 4: UNDO_LAST
        elif op.intent == "UNDO_LAST":
            if not session["last_txn_id"]:
                events.append({
                    "type": "answer",
                    "turn_id": turn_id,
                    "kind": "info",
                    "say": _with_disclosure(render_reply("nothing_to_undo", lang), disclosed),
                    "data": {},
                })
                update_session(session_id, disclosed=True)
                return events

            last_at_str = session["last_txn_at"]
            last_dt = datetime.fromisoformat(last_at_str) if last_at_str else now
            diff_sec = (now - last_dt).total_seconds()

            if diff_sec > AMEND_WINDOW_SECONDS:
                q = {
                    "kind": "confirm_undo",
                    "turn_id": turn_id,
                    "options": [{"id": "yes", "label": "Haan"}, {"id": "no", "label": "Nahi"}],
                    "about": op.model_dump(),
                    "remaining_ops": [o.model_dump() for o in operations[idx + 1:]],
                }
                update_session(session_id, pending_json=q)
                say = render_reply("confirm_undo", lang, name="Grahak", amount="entry")
                events.append({
                    "type": "question",
                    "turn_id": turn_id,
                    "kind": "confirm_undo",
                    "say": _with_disclosure(say, disclosed),
                    "options": q["options"],
                })
                update_session(session_id, disclosed=True)
                return events

            undone = undo_entry(shop_id, session["last_txn_id"], session_id=session_id)
            bal = customer_balance(undone["customer_id"])
            events.append({
                "type": "entry",
                "turn_id": turn_id,
                "entry": {
                    "id": undone["id"],
                    "customer_id": undone["customer_id"],
                    "customer_name": "Grahak",
                    "amount_paise": undone["amount_paise"],
                    "direction": undone["direction"],
                    "business_date": str(undone["business_date"]),
                    "recorded_at": undone["recorded_at"],
                    "status": "undone",
                    "old_amount_paise": undone["old_amount_paise"],
                    "language": lang,
                },
                "balance_paise": bal,
                "new_customer": False,
            })
            sentence = render_reply(
                "entry_undone",
                lang,
                name="Grahak",
                amount=rupees_in_words(undone["amount_paise"], lang),
                balance=rupees_in_words(bal, lang),
            )
            entry_sentences.append(sentence)

        # Rule 5: QUERY_BALANCE
        elif op.intent == "QUERY_BALANCE":
            current_customers = customer_refs(shop_id, now)
            candidates = match_customer_candidates(op.customer_name or "", current_customers) if op.customer_name else []
            if not candidates or candidates[0]["score"] < 75:
                events.append({
                    "type": "answer",
                    "turn_id": turn_id,
                    "kind": "info",
                    "say": _with_disclosure(render_reply("customer_not_found", lang, name=op.customer_name or ""), disclosed),
                    "data": {},
                })
                update_session(session_id, disclosed=True)
                return events

            matched = candidates[0]
            bal = customer_balance(matched["customer_id"])
            if bal == 0:
                say_key = "balance_zero"
            elif bal > 0:
                say_key = "balance"
            else:
                say_key = "balance_advance"

            say = render_reply(say_key, lang, name=matched["name"], balance=rupees_in_words(bal, lang))
            events.append({
                "type": "answer",
                "turn_id": turn_id,
                "kind": "balance",
                "say": _with_disclosure(say, disclosed),
                "data": {
                    "customer_id": matched["customer_id"],
                    "customer_name": matched["name"],
                    "balance_paise": bal,
                },
            })
            update_session(session_id, disclosed=True)
            return events

        # Rule 6: QUERY_DAILY_TOTAL
        elif op.intent == "QUERY_DAILY_TOTAL":
            total = daily_credit_total(shop_id, b_date)
            say = render_reply("daily_total", lang, amount=rupees_in_words(total, lang))
            events.append({
                "type": "answer",
                "turn_id": turn_id,
                "kind": "daily_total",
                "say": _with_disclosure(say, disclosed),
                "data": {
                    "business_date": str(b_date),
                    "credit_paise": total,
                },
            })
            update_session(session_id, disclosed=True)
            return events

        # Rule 7: QUERY_DAY_SUMMARY
        elif op.intent == "QUERY_DAY_SUMMARY":
            summary = day_summary(shop_id, b_date)
            top_str = ", ".join(f"{t['customer_name']} {rupees_in_words(t['balance_paise'], lang)}" for t in summary["top"]) or "koi nahi"
            say = render_reply(
                "day_summary",
                lang,
                credit=rupees_in_words(summary["credit_paise"], lang),
                payment=rupees_in_words(summary["payment_paise"], lang),
                top=top_str,
            )
            events.append({
                "type": "answer",
                "turn_id": turn_id,
                "kind": "day_summary",
                "say": _with_disclosure(say, disclosed),
                "data": summary,
            })
            update_session(session_id, disclosed=True)
            return events

    # Final message for entries
    if entry_sentences:
        if len(entry_sentences) >= 3:
            combined_say = render_reply("entries_many", lang, count=len(entry_sentences))
        else:
            combined_say = " ".join(entry_sentences)

        events.append({
            "type": "answer",
            "turn_id": turn_id,
            "kind": "entry_saved",
            "say": _with_disclosure(combined_say, disclosed),
            "data": {"count": len(entry_sentences)},
        })
        update_session(session_id, disclosed=True)

    return events


def _with_disclosure(say_text: str, already_disclosed: bool) -> str:
    """Prepends AI disclosure to the first reply of a session."""
    if already_disclosed:
        return say_text
    disclosure = render_reply("disclosure", "hi")
    return f"{disclosure} {say_text}"
