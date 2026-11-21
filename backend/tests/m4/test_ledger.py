"""
backend/tests/m4/test_ledger.py

Tests for core ledger service functions:
- customer_balance
- create_entry and idempotency
- amend_entry and undo_entry
- find_recent_duplicate
- credit_stats
- daily_credit_total and day_summary
- delete_shop_data
- shop isolation
"""

from datetime import datetime, timedelta, timezone
from app.services.ledger import (
    amend_entry,
    create_customer,
    create_entry,
    credit_stats,
    customer_balance,
    daily_credit_total,
    day_summary,
    delete_shop_data,
    find_recent_duplicate,
    undo_entry,
)
from app.database.db import get_connection


def _create_shop(phone="9000000001") -> int:
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO shops (owner_name, phone, pin_hash)
            VALUES ('Owner', ?, 'hash')
            """,
            (phone,),
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def test_customer_balance_calculation():
    shop_id = _create_shop("9111111111")
    cust = create_customer(shop_id, "Ramesh")
    cid = cust["id"]

    assert customer_balance(cid) == 0

    # Add 500 credit
    create_entry(shop_id, cid, 50000, "credit", "2026-11-21", datetime.now(timezone.utc))
    assert customer_balance(cid) == 50000

    # Add 200 payment
    create_entry(shop_id, cid, 20000, "payment", "2026-11-21", datetime.now(timezone.utc))
    assert customer_balance(cid) == 30000

    # Add 100 payment -> balance 20000
    p2 = create_entry(shop_id, cid, 10000, "payment", "2026-11-21", datetime.now(timezone.utc))
    assert customer_balance(cid) == 20000

    # Undo 100 payment -> balance returns to 30000
    undo_entry(shop_id, p2["id"])
    assert customer_balance(cid) == 30000


def test_create_entry_idempotency():
    shop_id = _create_shop("9111111112")
    cust = create_customer(shop_id, "Suresh")
    cid = cust["id"]

    key = "turn-uuid-1:0"
    e1 = create_entry(shop_id, cid, 30000, "credit", "2026-11-21", datetime.now(timezone.utc), idempotency_key=key)
    e2 = create_entry(shop_id, cid, 30000, "credit", "2026-11-21", datetime.now(timezone.utc), idempotency_key=key)

    assert e1["id"] == e2["id"]
    assert customer_balance(cid) == 30000


def test_amend_and_undo_lifecycle():
    shop_id = _create_shop("9111111113")
    cust = create_customer(shop_id, "Amit")
    cid = cust["id"]

    entry = create_entry(shop_id, cid, 10000, "credit", "2026-11-21", datetime.now(timezone.utc))
    eid = entry["id"]

    # Amend to 25000
    amended = amend_entry(shop_id, eid, 25000, session_id="sess-1")
    assert amended["amount_paise"] == 25000
    assert amended["old_amount_paise"] == 10000
    assert customer_balance(cid) == 25000

    # Undo
    undone = undo_entry(shop_id, eid, session_id="sess-1")
    assert undone["status"] == "undone"
    assert customer_balance(cid) == 0


def test_find_recent_duplicate():
    shop_id = _create_shop("9111111114")
    cust = create_customer(shop_id, "Ganesh")
    cid = cust["id"]

    now = datetime.now(timezone.utc)
    create_entry(shop_id, cid, 40000, "credit", "2026-11-21", now)

    # Within 120 seconds
    dup = find_recent_duplicate(shop_id, cid, 40000, "credit", now + timedelta(seconds=60))
    assert dup is not None
    assert dup["amount_paise"] == 40000

    # Outside 120 seconds
    dup_old = find_recent_duplicate(shop_id, cid, 40000, "credit", now + timedelta(seconds=130))
    assert dup_old is None


def test_credit_stats_and_median():
    shop_id = _create_shop("9111111115")
    cust = create_customer(shop_id, "Dinesh")
    cid = cust["id"]

    now = datetime.now(timezone.utc)
    # Add 4 credits: 100, 200, 300, 400
    for amt in [10000, 20000, 30000, 40000]:
        create_entry(shop_id, cid, amt, "credit", "2026-11-21", now)

    stats = credit_stats(cid)
    assert stats["earlier_count"] == 4
    # Median of [40000, 30000, 20000, 10000] is 25000
    assert stats["median_last_10"] == 25000.0


def test_daily_credit_and_day_summary():
    shop_id = _create_shop("9111111116")
    c1 = create_customer(shop_id, "Customer1")
    c2 = create_customer(shop_id, "Customer2")

    now = datetime.now(timezone.utc)
    create_entry(shop_id, c1["id"], 50000, "credit", "2026-11-21", now)
    create_entry(shop_id, c2["id"], 80000, "credit", "2026-11-21", now)
    create_entry(shop_id, c1["id"], 10000, "payment", "2026-11-21", now)

    assert daily_credit_total(shop_id, "2026-11-21") == 130000

    summary = day_summary(shop_id, "2026-11-21")
    assert summary["business_date"] == "2026-11-21"
    assert summary["credit_paise"] == 130000
    assert summary["payment_paise"] == 10000
    assert len(summary["top"]) == 2
    # Highest balance first
    assert summary["top"][0]["customer_name"] == "Customer2"
    assert summary["top"][0]["balance_paise"] == 80000
    assert summary["top"][1]["customer_name"] == "Customer1"
    assert summary["top"][1]["balance_paise"] == 40000


def test_shop_isolation_and_cascade_delete():
    shop1 = _create_shop("9111111117")
    shop2 = _create_shop("9111111118")

    c1 = create_customer(shop1, "Ramesh Shop1")
    c2 = create_customer(shop2, "Ramesh Shop2")

    now = datetime.now(timezone.utc)
    create_entry(shop1, c1["id"], 50000, "credit", "2026-11-21", now)
    create_entry(shop2, c2["id"], 90000, "credit", "2026-11-21", now)

    # Shop 2 summary must not see Shop 1 entries
    s2_sum = day_summary(shop2, "2026-11-21")
    assert s2_sum["credit_paise"] == 90000
    assert len(s2_sum["top"]) == 1
    assert s2_sum["top"][0]["customer_name"] == "Ramesh Shop2"

    # Delete Shop 1 data
    delete_shop_data(shop1)

    # Shop 1 customer balance is 0 and records are gone
    assert customer_balance(c1["id"]) == 0
    # Shop 2 remains intact
    assert customer_balance(c2["id"]) == 90000
