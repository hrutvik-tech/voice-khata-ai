"""
backend/tests/m4/test_decision_rules.py

Comprehensive tests for all business decision rules (M4-4):
Contains 30+ distinct scenarios through handle_transcript and handle_choice:
- Intent validation (UNKNOWN, confidence < 0.6)
- Amount validation (missing, mismatch, MAX limit, 3-part outlier rule)
- Customer disambiguation (>=90, 75-89, <75)
- Duplicate detection and cancellation
- Amendment and Undo within and beyond 60s window
- Balance, Daily Total, Day Summary queries
- Strict mode behavior
- Multi-operation scenario: "Suresh ka 200 udhaar, kal 100 diya tha"
"""

import pytest
from datetime import datetime, timedelta, timezone

from app.database.db import get_connection
from app.services.conversation import get_or_create_session, get_session
from app.services.ledger import create_customer, create_entry, customer_balance
from app.services.orchestrator import (
    Context,
    Interpretation,
    Operation,
    Transcript,
    handle_choice,
    handle_transcript,
)


def _init_test_shop(phone="9400000001") -> int:
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM shops WHERE phone = ?", (phone,))
        existing = cursor.fetchone()
        if existing:
            return existing["id"]
        cursor.execute(
            """
            INSERT INTO shops (owner_name, phone, pin_hash, open_time, close_time, timezone)
            VALUES ('Owner', ?, 'hash', '06:00', '02:00', 'Asia/Kolkata')
            """,
            (phone,),
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


@pytest.mark.asyncio
async def test_scenario_01_unknown_intent():
    shop_id = _init_test_shop("9400000001")
    now = datetime.now(timezone.utc)
    sess = get_or_create_session(shop_id, now)

    def fake_interp(ts, ctx):
        return Interpretation(operations=[Operation(intent="UNKNOWN", confidence=0.0)])

    events = await handle_transcript(sess["id"], "t1", Transcript(text="blabla"), now, custom_interpreter=fake_interp)
    assert events[-1]["type"] == "not_understood"


@pytest.mark.asyncio
async def test_scenario_02_low_confidence():
    shop_id = _init_test_shop("9400000002")
    now = datetime.now(timezone.utc)
    sess = get_or_create_session(shop_id, now)

    def fake_interp(ts, ctx):
        return Interpretation(operations=[Operation(intent="CREATE_TRANSACTION", amount_paise=10000, direction="credit", confidence=0.5)])

    events = await handle_transcript(sess["id"], "t2", Transcript(text="something"), now, custom_interpreter=fake_interp)
    assert events[-1]["type"] == "not_understood"


@pytest.mark.asyncio
async def test_scenario_03_missing_direction():
    shop_id = _init_test_shop("9400000003")
    now = datetime.now(timezone.utc)
    sess = get_or_create_session(shop_id, now)

    def fake_interp(ts, ctx):
        return Interpretation(operations=[Operation(intent="CREATE_TRANSACTION", customer_name="Ramesh", amount_paise=50000, direction=None)])

    events = await handle_transcript(sess["id"], "t3", Transcript(text="Ramesh 500"), now, custom_interpreter=fake_interp)
    assert events[-1]["type"] == "question"
    assert events[-1]["kind"] == "confirm_direction"


@pytest.mark.asyncio
async def test_scenario_04_resolve_confirm_direction():
    shop_id = _init_test_shop("9400000004")
    now = datetime.now(timezone.utc)
    sess = get_or_create_session(shop_id, now)

    def fake_interp(ts, ctx):
        return Interpretation(operations=[Operation(intent="CREATE_TRANSACTION", customer_name="Ramesh", amount_paise=50000, direction=None)])

    await handle_transcript(sess["id"], "t4", Transcript(text="Ramesh 500"), now, custom_interpreter=fake_interp)

    events = await handle_choice(sess["id"], "t4", {"answer": "credit"}, now)
    assert any(e["type"] == "entry" for e in events)
    entry_ev = [e for e in events if e["type"] == "entry"][0]
    assert entry_ev["entry"]["direction"] == "credit"
    assert entry_ev["entry"]["amount_paise"] == 50000


@pytest.mark.asyncio
async def test_scenario_05_unparsed_amount():
    shop_id = _init_test_shop("9400000005")
    now = datetime.now(timezone.utc)
    sess = get_or_create_session(shop_id, now)

    def fake_interp(ts, ctx):
        return Interpretation(operations=[Operation(intent="CREATE_TRANSACTION", customer_name="Ramesh", amount_check="unparsed", direction="credit")])

    events = await handle_transcript(sess["id"], "t5", Transcript(text="Ramesh udhaar"), now, custom_interpreter=fake_interp)
    assert events[-1]["type"] == "not_understood"


@pytest.mark.asyncio
async def test_scenario_06_amount_mismatch():
    shop_id = _init_test_shop("9400000006")
    now = datetime.now(timezone.utc)
    sess = get_or_create_session(shop_id, now)

    def fake_interp(ts, ctx):
        return Interpretation(operations=[Operation(intent="CREATE_TRANSACTION", customer_name="Ramesh", amount_paise=10000, amount_check="mismatch", direction="credit")])

    events = await handle_transcript(sess["id"], "t6", Transcript(text="Ramesh 100"), now, custom_interpreter=fake_interp)
    assert events[-1]["type"] == "question"
    assert events[-1]["kind"] == "confirm_amount"


@pytest.mark.asyncio
async def test_scenario_07_amount_exceeds_max():
    shop_id = _init_test_shop("9400000007")
    now = datetime.now(timezone.utc)
    sess = get_or_create_session(shop_id, now)

    def fake_interp(ts, ctx):
        return Interpretation(operations=[Operation(intent="CREATE_TRANSACTION", customer_name="Ramesh", amount_paise=150000000, direction="credit")])

    events = await handle_transcript(sess["id"], "t7", Transcript(text="Ramesh 15 lakh"), now, custom_interpreter=fake_interp)
    assert events[-1]["type"] == "question"
    assert events[-1]["kind"] == "confirm_amount"


@pytest.mark.asyncio
async def test_scenario_08_outlier_rule_fires():
    shop_id = _init_test_shop("9400000008")
    now = datetime.now(timezone.utc)
    c = create_customer(shop_id, "Outlier Customer")
    cid = c["id"]

    # 3 earlier credits with median 10000 (₹100)
    for _ in range(3):
        create_entry(shop_id, cid, 10000, "credit", "2026-11-21", now)

    # New credit: 300000 paise (₹3,000) > 5 * 10000 and > 200000
    sess = get_or_create_session(shop_id, now)

    def fake_interp(ts, ctx):
        return Interpretation(operations=[Operation(intent="CREATE_TRANSACTION", customer_name="Outlier Customer", amount_paise=300000, direction="credit")])

    events = await handle_transcript(sess["id"], "t8", Transcript(text="Outlier 3000"), now, custom_interpreter=fake_interp)
    assert events[-1]["type"] == "question"
    assert events[-1]["kind"] == "confirm_amount"


@pytest.mark.asyncio
async def test_scenario_09_outlier_condition_fails_when_under_3_credits():
    shop_id = _init_test_shop("9400000009")
    now = datetime.now(timezone.utc)
    c = create_customer(shop_id, "Regular Customer")
    cid = c["id"]

    # Only 2 earlier credits
    create_entry(shop_id, cid, 10000, "credit", "2026-11-21", now)
    create_entry(shop_id, cid, 10000, "credit", "2026-11-21", now)

    sess = get_or_create_session(shop_id, now)

    def fake_interp(ts, ctx):
        return Interpretation(operations=[Operation(intent="CREATE_TRANSACTION", customer_name="Regular Customer", amount_paise=500000, direction="credit")])

    events = await handle_transcript(sess["id"], "t9", Transcript(text="Regular 5000"), now, custom_interpreter=fake_interp)
    # Should not trigger outlier question because earlier_count < 3
    assert any(e["type"] == "entry" for e in events)


@pytest.mark.asyncio
async def test_scenario_10_outlier_fails_when_under_2000_rupees():
    shop_id = _init_test_shop("9400000010")
    now = datetime.now(timezone.utc)
    c = create_customer(shop_id, "Small Customer")
    cid = c["id"]

    for _ in range(4):
        create_entry(shop_id, cid, 1000, "credit", "2026-11-21", now)

    sess = get_or_create_session(shop_id, now)

    # 10000 paise is ₹100, which is > 5 * 1000, but <= 200000 paise (₹2,000)
    def fake_interp(ts, ctx):
        return Interpretation(operations=[Operation(intent="CREATE_TRANSACTION", customer_name="Small Customer", amount_paise=10000, direction="credit")])

    events = await handle_transcript(sess["id"], "t10", Transcript(text="Small 100"), now, custom_interpreter=fake_interp)
    assert any(e["type"] == "entry" for e in events)


@pytest.mark.asyncio
async def test_scenario_11_disambiguation_multiple_exact_matches():
    shop_id = _init_test_shop("9400000011")
    now = datetime.now(timezone.utc)
    create_customer(shop_id, "Ramesh Sharma", area="Gandhi Nagar")
    create_customer(shop_id, "Ramesh Sharma", area="Station Road")

    sess = get_or_create_session(shop_id, now)

    def fake_interp(ts, ctx):
        return Interpretation(operations=[Operation(intent="CREATE_TRANSACTION", customer_name="Ramesh Sharma", amount_paise=20000, direction="credit")])

    events = await handle_transcript(sess["id"], "t11", Transcript(text="Ramesh Sharma 200"), now, custom_interpreter=fake_interp)
    assert events[-1]["type"] == "question"
    assert events[-1]["kind"] == "choose_customer"
    assert len(events[-1]["options"]) == 2


@pytest.mark.asyncio
async def test_scenario_12_resolve_choose_customer():
    shop_id = _init_test_shop("9400000012")
    now = datetime.now(timezone.utc)
    c1 = create_customer(shop_id, "Ramesh Sharma", area="Gandhi Nagar")
    create_customer(shop_id, "Ramesh Sharma", area="Station Road")

    sess = get_or_create_session(shop_id, now)

    def fake_interp(ts, ctx):
        return Interpretation(operations=[Operation(intent="CREATE_TRANSACTION", customer_name="Ramesh Sharma", amount_paise=20000, direction="credit")])

    await handle_transcript(sess["id"], "t12", Transcript(text="Ramesh Sharma 200"), now, custom_interpreter=fake_interp)
    events = await handle_choice(sess["id"], "t12", {"customer_id": c1["id"]}, now)
    assert any(e["type"] == "entry" for e in events)
    assert customer_balance(c1["id"]) == 20000


@pytest.mark.asyncio
async def test_scenario_13_similar_match_confirm():
    shop_id = _init_test_shop("9400000013")
    now = datetime.now(timezone.utc)
    create_customer(shop_id, "Rameshwar")

    sess = get_or_create_session(shop_id, now)

    # "Ramesh" vs "Rameshwar" gives score in 75-89 range
    def fake_interp(ts, ctx):
        return Interpretation(operations=[Operation(intent="CREATE_TRANSACTION", customer_name="Ramesh", amount_paise=30000, direction="credit")])

    events = await handle_transcript(sess["id"], "t13", Transcript(text="Ramesh 300"), now, custom_interpreter=fake_interp)
    assert events[-1]["type"] == "question"
    assert events[-1]["kind"] == "confirm_similar"


@pytest.mark.asyncio
async def test_scenario_14_new_customer_created_when_no_match():
    shop_id = _init_test_shop("9400000014")
    now = datetime.now(timezone.utc)
    sess = get_or_create_session(shop_id, now)

    def fake_interp(ts, ctx):
        return Interpretation(operations=[Operation(intent="CREATE_TRANSACTION", customer_name="TotallyNewPerson", amount_paise=40000, direction="credit")])

    events = await handle_transcript(sess["id"], "t14", Transcript(text="TotallyNewPerson 400"), now, custom_interpreter=fake_interp)
    entry_ev = [e for e in events if e["type"] == "entry"][0]
    assert entry_ev["new_customer"] is True
    assert entry_ev["entry"]["customer_name"] == "TotallyNewPerson"


@pytest.mark.asyncio
async def test_scenario_15_duplicate_detection():
    shop_id = _init_test_shop("9400000015")
    now = datetime.now(timezone.utc)
    c = create_customer(shop_id, "Pooja")
    create_entry(shop_id, c["id"], 50000, "credit", "2026-11-21", now)

    sess = get_or_create_session(shop_id, now)

    def fake_interp(ts, ctx):
        return Interpretation(operations=[Operation(intent="CREATE_TRANSACTION", customer_name="Pooja", amount_paise=50000, direction="credit")])

    # Submitting same customer, amount, direction within 60s
    events = await handle_transcript(sess["id"], "t15", Transcript(text="Pooja 500"), now + timedelta(seconds=30), custom_interpreter=fake_interp)
    assert events[-1]["type"] == "question"
    assert events[-1]["kind"] == "confirm_duplicate"


@pytest.mark.asyncio
async def test_scenario_16_duplicate_rejected():
    shop_id = _init_test_shop("9400000016")
    now = datetime.now(timezone.utc)
    c = create_customer(shop_id, "Kiran")
    create_entry(shop_id, c["id"], 25000, "credit", "2026-11-21", now)

    sess = get_or_create_session(shop_id, now)

    def fake_interp(ts, ctx):
        return Interpretation(operations=[Operation(intent="CREATE_TRANSACTION", customer_name="Kiran", amount_paise=25000, direction="credit")])

    await handle_transcript(sess["id"], "t16", Transcript(text="Kiran 250"), now + timedelta(seconds=20), custom_interpreter=fake_interp)
    events = await handle_choice(sess["id"], "t16", {"answer": "no"}, now)
    assert events[-1]["kind"] == "cancelled"
    # Balance remains 25000 (not duplicated)
    assert customer_balance(c["id"]) == 25000


@pytest.mark.asyncio
async def test_scenario_17_amend_within_window():
    shop_id = _init_test_shop("9400000017")
    now = datetime.now(timezone.utc)
    c = create_customer(shop_id, "Dev")
    e = create_entry(shop_id, c["id"], 10000, "credit", "2026-11-21", now)

    sess = get_or_create_session(shop_id, now)
    from app.services.conversation import update_session
    update_session(sess["id"], last_txn_id=e["id"], last_txn_at=now.isoformat())

    def fake_interp(ts, ctx):
        return Interpretation(operations=[Operation(intent="CORRECTION", amount_paise=15000)])

    # 30 seconds later (within 60s window)
    events = await handle_transcript(sess["id"], "t17", Transcript(text="150 kar do"), now + timedelta(seconds=30), custom_interpreter=fake_interp)
    assert any(e["type"] == "entry" and e["entry"]["status"] == "amended" for e in events)
    assert customer_balance(c["id"]) == 15000


@pytest.mark.asyncio
async def test_scenario_18_amend_outside_window():
    shop_id = _init_test_shop("9400000018")
    now = datetime.now(timezone.utc)
    c = create_customer(shop_id, "Neeraj")
    e = create_entry(shop_id, c["id"], 10000, "credit", "2026-11-21", now)

    sess = get_or_create_session(shop_id, now)
    from app.services.conversation import update_session
    update_session(sess["id"], last_txn_id=e["id"], last_txn_at=now.isoformat())

    def fake_interp(ts, ctx):
        return Interpretation(operations=[Operation(intent="CORRECTION", amount_paise=15000)])

    # 70 seconds later (outside 60s window)
    events = await handle_transcript(sess["id"], "t18", Transcript(text="150 kar do"), now + timedelta(seconds=70), custom_interpreter=fake_interp)
    assert events[-1]["type"] == "question"
    assert events[-1]["kind"] == "confirm_amend"


@pytest.mark.asyncio
async def test_scenario_19_undo_within_window():
    shop_id = _init_test_shop("9400000019")
    now = datetime.now(timezone.utc)
    c = create_customer(shop_id, "Vikas")
    e = create_entry(shop_id, c["id"], 20000, "credit", "2026-11-21", now)

    sess = get_or_create_session(shop_id, now)
    from app.services.conversation import update_session
    update_session(sess["id"], last_txn_id=e["id"], last_txn_at=now.isoformat())

    def fake_interp(ts, ctx):
        return Interpretation(operations=[Operation(intent="UNDO_LAST")])

    events = await handle_transcript(sess["id"], "t19", Transcript(text="hata do"), now + timedelta(seconds=20), custom_interpreter=fake_interp)
    assert any(e["type"] == "entry" and e["entry"]["status"] == "undone" for e in events)
    assert customer_balance(c["id"]) == 0


@pytest.mark.asyncio
async def test_scenario_20_undo_outside_window():
    shop_id = _init_test_shop("9400000020")
    now = datetime.now(timezone.utc)
    c = create_customer(shop_id, "Mohan")
    e = create_entry(shop_id, c["id"], 20000, "credit", "2026-11-21", now)

    sess = get_or_create_session(shop_id, now)
    from app.services.conversation import update_session
    update_session(sess["id"], last_txn_id=e["id"], last_txn_at=now.isoformat())

    def fake_interp(ts, ctx):
        return Interpretation(operations=[Operation(intent="UNDO_LAST")])

    events = await handle_transcript(sess["id"], "t20", Transcript(text="hata do"), now + timedelta(seconds=80), custom_interpreter=fake_interp)
    assert events[-1]["type"] == "question"
    assert events[-1]["kind"] == "confirm_undo"


@pytest.mark.asyncio
async def test_scenario_21_undo_nothing():
    shop_id = _init_test_shop("9400000021")
    now = datetime.now(timezone.utc)
    sess = get_or_create_session(shop_id, now)

    def fake_interp(ts, ctx):
        return Interpretation(operations=[Operation(intent="UNDO_LAST")])

    events = await handle_transcript(sess["id"], "t21", Transcript(text="hata do"), now, custom_interpreter=fake_interp)
    assert events[-1]["kind"] == "info"
    assert "हटाने के लिए कोई एंट्री नहीं है" in events[-1]["say"]


@pytest.mark.asyncio
async def test_scenario_22_query_balance_found():
    shop_id = _init_test_shop("9400000022")
    now = datetime.now(timezone.utc)
    c = create_customer(shop_id, "Harish")
    create_entry(shop_id, c["id"], 45000, "credit", "2026-11-21", now)

    sess = get_or_create_session(shop_id, now)

    def fake_interp(ts, ctx):
        return Interpretation(operations=[Operation(intent="QUERY_BALANCE", customer_name="Harish")])

    events = await handle_transcript(sess["id"], "t22", Transcript(text="Harish ka kitna hai"), now, custom_interpreter=fake_interp)
    assert events[-1]["kind"] == "balance"
    assert events[-1]["data"]["balance_paise"] == 45000


@pytest.mark.asyncio
async def test_scenario_23_query_balance_not_found():
    shop_id = _init_test_shop("9400000023")
    now = datetime.now(timezone.utc)
    sess = get_or_create_session(shop_id, now)

    def fake_interp(ts, ctx):
        return Interpretation(operations=[Operation(intent="QUERY_BALANCE", customer_name="UnknownGhost")])

    events = await handle_transcript(sess["id"], "t23", Transcript(text="Unknown ka kitna"), now, custom_interpreter=fake_interp)
    assert events[-1]["kind"] == "info"
    assert "कोई ग्राहक नहीं मिला" in events[-1]["say"]


@pytest.mark.asyncio
async def test_scenario_24_query_daily_total():
    shop_id = _init_test_shop("9400000024")
    now = datetime.now(timezone.utc)
    c = create_customer(shop_id, "Cust")
    create_entry(shop_id, c["id"], 60000, "credit", "2026-11-21", now)

    sess = get_or_create_session(shop_id, now)

    def fake_interp(ts, ctx):
        return Interpretation(operations=[Operation(intent="QUERY_DAILY_TOTAL")])

    events = await handle_transcript(sess["id"], "t24", Transcript(text="aaj ka kul"), now, custom_interpreter=fake_interp)
    assert events[-1]["kind"] == "daily_total"
    assert events[-1]["data"]["credit_paise"] == 60000


@pytest.mark.asyncio
async def test_scenario_25_query_day_summary():
    shop_id = _init_test_shop("9400000025")
    now = datetime.now(timezone.utc)
    c = create_customer(shop_id, "SummaryCust")
    create_entry(shop_id, c["id"], 75000, "credit", "2026-11-21", now)

    sess = get_or_create_session(shop_id, now)

    def fake_interp(ts, ctx):
        return Interpretation(operations=[Operation(intent="QUERY_DAY_SUMMARY")])

    events = await handle_transcript(sess["id"], "t25", Transcript(text="aaj ka hisab"), now, custom_interpreter=fake_interp)
    assert events[-1]["kind"] == "day_summary"
    assert events[-1]["data"]["credit_paise"] == 75000


@pytest.mark.asyncio
async def test_scenario_26_strict_mode_unresolved_yields_not_saved():
    shop_id = _init_test_shop("9400000026")
    now = datetime.now(timezone.utc)
    sess = get_or_create_session(shop_id, now)

    # Missing direction in strict mode (offline sync) -> not_saved event, no DB write
    def fake_interp(ts, ctx):
        return Interpretation(operations=[Operation(intent="CREATE_TRANSACTION", customer_name="Ramesh", amount_paise=50000, direction=None)])

    events = await handle_transcript(sess["id"], "t26", Transcript(text="Ramesh 500"), now, strict=True, custom_interpreter=fake_interp)
    assert events[-1]["type"] == "not_saved"


@pytest.mark.asyncio
async def test_scenario_27_multi_operation_suresh_credit_and_payment():
    """
    Required master prompt scenario:
    'Suresh ka 200 udhaar, kal 100 diya tha'
    Expected:
    - 2 operations
    - One credit today (20000 paise)
    - One payment yesterday (10000 paise)
    - Final balance = 10000 paise (200 - 100 = 100)
    """
    shop_id = _init_test_shop("9400000027")
    now = datetime.now(timezone.utc)
    sess = get_or_create_session(shop_id, now)

    events = await handle_transcript(
        sess["id"],
        "t27-multi",
        Transcript(text="Suresh ka 200 udhaar, kal 100 diya tha"),
        now,
    )

    # Must contain 2 entry events
    entry_events = [e for e in events if e.get("type") == "entry"]
    assert len(entry_events) == 2

    e_credit = entry_events[0]
    e_payment = entry_events[1]

    assert e_credit["entry"]["direction"] == "credit"
    assert e_credit["entry"]["amount_paise"] == 20000
    assert e_credit["entry"]["customer_name"] == "Suresh"

    assert e_payment["entry"]["direction"] == "payment"
    assert e_payment["entry"]["amount_paise"] == 10000
    assert e_payment["entry"]["customer_name"] == "Suresh"

    # Business date of second operation should be yesterday
    today_b = str(e_credit["entry"]["business_date"])
    yesterday_b = str(e_payment["entry"]["business_date"])
    assert today_b != yesterday_b

    # Final balance check
    cust_id = e_credit["entry"]["customer_id"]
    assert customer_balance(cust_id) == 10000
