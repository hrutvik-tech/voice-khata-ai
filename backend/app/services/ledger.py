"""
backend/app/services/ledger.py

Ledger service implementing core accounting, customer management,
transaction lifecycle, and summary statistics for Bolta Khata AI.
"""

import math
import statistics
from datetime import date, datetime, timedelta, timezone
from typing import Any
from zoneinfo import ZoneInfo
from rapidfuzz import fuzz

from app.database.db import get_connection
from app.core.tokens import ensure_db_tables


def normalize_name(name: str) -> str:
    """Normalize a customer name: lowercase, strip punctuation and extra spaces."""
    if not name:
        return ""
    cleaned = "".join(c if c.isalnum() or c.isspace() else " " for c in name.lower())
    return " ".join(cleaned.split())


def encrypt_text(value: str | None) -> str | None:
    """Pass-through/safe encryption stub for text fields (phone/transcript)."""
    return value


def decrypt_text(value: str | None) -> str | None:
    """Pass-through/safe decryption stub for text fields (phone/transcript)."""
    return value


def get_shop_business_date(shop_row: dict | Any, moment: datetime | None = None) -> date:
    """
    Computes the business date according to the shop's opening time and timezone.
    Business day runs from opening time to the next opening time.
    """
    tz_name = shop_row.get("timezone") or "Asia/Kolkata"
    try:
        tz = ZoneInfo(tz_name)
    except Exception:
        tz = timezone(timedelta(hours=5, minutes=30))

    if moment is None:
        now_dt = datetime.now(tz)
    else:
        if moment.tzinfo is None:
            now_dt = moment.replace(tzinfo=timezone.utc).astimezone(tz)
        else:
            now_dt = moment.astimezone(tz)

    open_time_str = shop_row.get("open_time") or "06:00"
    try:
        open_h, open_m = map(int, open_time_str.split(":"))
    except ValueError:
        open_h, open_m = 6, 0

    if (now_dt.hour, now_dt.minute) >= (open_h, open_m):
        return now_dt.date()
    else:
        return now_dt.date() - timedelta(days=1)


def customer_balance(customer_id: int) -> int:
    """
    Computes customer balance in paise: sum of active credits minus sum of active payments.
    Calculated on every read and never stored.
    """
    conn = get_connection()
    try:
        ensure_db_tables(conn)
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT
                COALESCE(SUM(CASE WHEN direction = 'credit' THEN amount_paise ELSE 0 END), 0) -
                COALESCE(SUM(CASE WHEN direction = 'payment' THEN amount_paise ELSE 0 END), 0) AS balance
            FROM transactions
            WHERE customer_id = ? AND status = 'active'
            """,
            (customer_id,),
        )
        row = cursor.fetchone()
        return int(row["balance"]) if row and row["balance"] is not None else 0
    finally:
        conn.close()


def list_customers(shop_id: int, search: str | None = None) -> list[dict]:
    """
    Returns list of customers for a shop with decrypted phone, balance, and latest activity.
    Sorted: newest activity first; customers without activity last, sorted alphabetically by name.
    """
    conn = get_connection()
    try:
        ensure_db_tables(conn)
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT
                c.id,
                c.shop_id,
                c.name,
                c.name_key,
                c.phone,
                c.area,
                c.source,
                c.created_at,
                MAX(t.recorded_at) AS last_activity_at,
                COALESCE(SUM(CASE WHEN t.status = 'active' AND t.direction = 'credit' THEN t.amount_paise ELSE 0 END), 0) -
                COALESCE(SUM(CASE WHEN t.status = 'active' AND t.direction = 'payment' THEN t.amount_paise ELSE 0 END), 0) AS balance_paise
            FROM customers c
            LEFT JOIN transactions t ON t.customer_id = c.id
            WHERE c.shop_id = ?
            GROUP BY c.id
            """,
            (shop_id,),
        )
        rows = cursor.fetchall()
        results = []

        norm_search = normalize_name(search) if search else None

        for row in rows:
            decrypted_phone = decrypt_text(row["phone"])
            c_name = row["name"]
            c_name_key = row["name_key"]
            c_area = row["area"] or ""

            if norm_search:
                matches_name = norm_search in c_name_key
                matches_area = norm_search in normalize_name(c_area)
                matches_phone = (decrypted_phone and norm_search in decrypted_phone)
                if not (matches_name or matches_area or matches_phone):
                    continue

            results.append({
                "id": row["id"],
                "name": c_name,
                "phone": decrypted_phone,
                "area": row["area"],
                "balance_paise": int(row["balance_paise"]),
                "last_activity_at": row["last_activity_at"],
            })

        # Sort: newest activity first; customers without activity last, sorted alphabetically
        def sort_key(item):
            has_act = 1 if item["last_activity_at"] else 0
            act = item["last_activity_at"] or ""
            # -has_act puts active first, then -act (reverse chronological), then name
            return (-has_act, "" if has_act else item["name"].lower(), act if not has_act else "")

        # Proper python sorting
        active_items = [x for x in results if x["last_activity_at"] is not None]
        inactive_items = [x for x in results if x["last_activity_at"] is None]

        active_items.sort(key=lambda x: x["last_activity_at"], reverse=True)
        inactive_items.sort(key=lambda x: x["name"].lower())

        return active_items + inactive_items
    finally:
        conn.close()


def customer_refs(shop_id: int, now: datetime) -> list[dict]:
    """
    Returns customer references for orchestrator context:
    includes active entry count in the last 30 days and latest activity timestamp.
    """
    thirty_days_ago = (now - timedelta(days=30)).isoformat()
    conn = get_connection()
    try:
        ensure_db_tables(conn)
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT
                c.id,
                c.name,
                c.area,
                c.phone,
                MAX(t.recorded_at) AS last_activity_at,
                COUNT(CASE WHEN t.status = 'active' AND t.recorded_at >= ? THEN 1 END) AS recent_count
            FROM customers c
            LEFT JOIN transactions t ON t.customer_id = c.id
            WHERE c.shop_id = ?
            GROUP BY c.id
            ORDER BY c.name ASC
            """,
            (thirty_days_ago, shop_id),
        )
        rows = cursor.fetchall()
        return [
            {
                "id": row["id"],
                "name": row["name"],
                "area": row["area"],
                "phone": decrypt_text(row["phone"]),
                "recent_count": int(row["recent_count"]),
                "last_activity_at": row["last_activity_at"],
            }
            for row in rows
        ]
    finally:
        conn.close()


def find_similar_customers(shop_id: int, name: str) -> list[dict]:
    """Finds existing customers with similarity score >= 75 using normalized name comparison."""
    norm = normalize_name(name)
    conn = get_connection()
    try:
        ensure_db_tables(conn)
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, area, name_key FROM customers WHERE shop_id = ?", (shop_id,))
        rows = cursor.fetchall()

        similar = []
        for r in rows:
            score = fuzz.token_sort_ratio(norm, r["name_key"])
            if score >= 75:
                similar.append({
                    "id": r["id"],
                    "name": r["name"],
                    "area": r["area"],
                    "score": score,
                })
        similar.sort(key=lambda x: x["score"], reverse=True)
        return similar
    finally:
        conn.close()


def create_customer(
    shop_id: int,
    name: str,
    phone: str | None = None,
    area: str | None = None,
    source: str = "manual",
) -> dict:
    """Creates a new customer record."""
    norm_key = normalize_name(name)
    enc_phone = encrypt_text(phone) if phone else None
    conn = get_connection()
    try:
        ensure_db_tables(conn)
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO customers (shop_id, name, name_key, phone, area, source)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (shop_id, name, norm_key, enc_phone, area, source),
        )
        conn.commit()
        cust_id = cursor.lastrowid
        cursor.execute("SELECT * FROM customers WHERE id = ?", (cust_id,))
        row = cursor.fetchone()
        return {
            "id": row["id"],
            "shop_id": row["shop_id"],
            "name": row["name"],
            "name_key": row["name_key"],
            "phone": decrypt_text(row["phone"]),
            "area": row["area"],
            "source": row["source"],
            "created_at": str(row["created_at"]),
        }
    finally:
        conn.close()


def create_entry(
    shop_id: int,
    customer_id: int,
    amount_paise: int,
    direction: str,
    business_date: str | date,
    recorded_at: str | datetime,
    source: str = "voice",
    language: str | None = None,
    raw_transcript: str | None = None,
    session_id: str | None = None,
    idempotency_key: str | None = None,
) -> dict:
    """
    Creates an entry with atomic transaction management and idempotency.
    If idempotency_key already exists, returns existing entry.
    """
    if amount_paise <= 0:
        raise ValueError("amount_paise must be positive")
    if direction not in ("credit", "payment"):
        raise ValueError("direction must be 'credit' or 'payment'")

    b_date = str(business_date)
    r_at = recorded_at.isoformat() if isinstance(recorded_at, datetime) else str(recorded_at)
    enc_transcript = encrypt_text(raw_transcript) if raw_transcript else None

    conn = get_connection()
    try:
        ensure_db_tables(conn)
        cursor = conn.cursor()

        if idempotency_key:
            cursor.execute("SELECT * FROM transactions WHERE idempotency_key = ?", (idempotency_key,))
            existing = cursor.fetchone()
            if existing:
                return dict(existing)

        cursor.execute(
            """
            INSERT INTO transactions (
                shop_id, customer_id, amount_paise, direction, business_date,
                recorded_at, status, source, language, raw_transcript, session_id, idempotency_key
            ) VALUES (?, ?, ?, ?, ?, ?, 'active', ?, ?, ?, ?, ?)
            """,
            (
                shop_id,
                customer_id,
                amount_paise,
                direction,
                b_date,
                r_at,
                source,
                language,
                enc_transcript,
                session_id,
                idempotency_key,
            ),
        )
        conn.commit()
        entry_id = cursor.lastrowid
        cursor.execute("SELECT * FROM transactions WHERE id = ?", (entry_id,))
        return dict(cursor.fetchone())
    finally:
        conn.close()


def amend_entry(
    shop_id: int,
    entry_id: int,
    new_amount_paise: int,
    session_id: str | None = None,
) -> dict:
    """
    Amends an active transaction and writes correction history in one atomic transaction.
    """
    if new_amount_paise <= 0:
        raise ValueError("new_amount_paise must be positive")

    conn = get_connection()
    try:
        ensure_db_tables(conn)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM transactions WHERE id = ? AND shop_id = ? AND status = 'active'",
            (entry_id, shop_id),
        )
        entry = cursor.fetchone()
        if not entry:
            raise ValueError("Entry not found or already undone")

        old_amount = entry["amount_paise"]

        cursor.execute(
            """
            INSERT INTO correction_history (
                transaction_id, action, old_amount_paise, new_amount_paise, session_id
            ) VALUES (?, 'amend', ?, ?, ?)
            """,
            (entry_id, old_amount, new_amount_paise, session_id),
        )
        cursor.execute(
            "UPDATE transactions SET amount_paise = ? WHERE id = ?",
            (new_amount_paise, entry_id),
        )
        conn.commit()

        cursor.execute("SELECT * FROM transactions WHERE id = ?", (entry_id,))
        updated = dict(cursor.fetchone())
        updated["old_amount_paise"] = old_amount
        return updated
    finally:
        conn.close()


def undo_entry(
    shop_id: int,
    entry_id: int,
    session_id: str | None = None,
) -> dict:
    """
    Marks an active transaction as 'undone' and records correction history in one atomic transaction.
    """
    conn = get_connection()
    try:
        ensure_db_tables(conn)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM transactions WHERE id = ? AND shop_id = ? AND status = 'active'",
            (entry_id, shop_id),
        )
        entry = cursor.fetchone()
        if not entry:
            raise ValueError("Entry not found or already undone")

        old_amount = entry["amount_paise"]

        cursor.execute(
            """
            INSERT INTO correction_history (
                transaction_id, action, old_amount_paise, new_amount_paise, session_id
            ) VALUES (?, 'undo', ?, NULL, ?)
            """,
            (entry_id, old_amount, session_id),
        )
        cursor.execute(
            "UPDATE transactions SET status = 'undone' WHERE id = ?",
            (entry_id,),
        )
        conn.commit()

        cursor.execute("SELECT * FROM transactions WHERE id = ?", (entry_id,))
        updated = dict(cursor.fetchone())
        updated["old_amount_paise"] = old_amount
        return updated
    finally:
        conn.close()


def find_recent_duplicate(
    shop_id: int,
    customer_id: int,
    amount_paise: int,
    direction: str,
    now: datetime,
) -> dict | None:
    """
    Checks if an active transaction with same customer, amount, and direction
    was recorded within DUPLICATE_WINDOW_SECONDS (120 seconds) of `now`.
    """
    window_start = (now - timedelta(seconds=120)).isoformat()
    conn = get_connection()
    try:
        ensure_db_tables(conn)
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT * FROM transactions
            WHERE shop_id = ?
              AND customer_id = ?
              AND amount_paise = ?
              AND direction = ?
              AND status = 'active'
              AND recorded_at >= ?
            ORDER BY recorded_at DESC
            LIMIT 1
            """,
            (shop_id, customer_id, amount_paise, direction, window_start),
        )
        row = cursor.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def credit_stats(customer_id: int) -> dict:
    """
    Returns active credit statistics for outlier detection:
    earlier_count and median of the last 10 active credits.
    """
    conn = get_connection()
    try:
        ensure_db_tables(conn)
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT amount_paise
            FROM transactions
            WHERE customer_id = ? AND direction = 'credit' AND status = 'active'
            ORDER BY recorded_at DESC
            """,
            (customer_id,),
        )
        rows = cursor.fetchall()
        amounts = [r["amount_paise"] for r in rows]
        earlier_count = len(amounts)
        last_10 = amounts[:10]
        med = statistics.median(last_10) if last_10 else 0
        return {
            "earlier_count": earlier_count,
            "median_last_10": med,
        }
    finally:
        conn.close()


def daily_credit_total(shop_id: int, business_date: date | str) -> int:
    """Calculates total active credit in paise for a given business day."""
    b_date = str(business_date)
    conn = get_connection()
    try:
        ensure_db_tables(conn)
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT COALESCE(SUM(amount_paise), 0) AS total_credit
            FROM transactions
            WHERE shop_id = ? AND business_date = ? AND direction = 'credit' AND status = 'active'
            """,
            (shop_id, b_date),
        )
        row = cursor.fetchone()
        return int(row["total_credit"]) if row and row["total_credit"] else 0
    finally:
        conn.close()


def day_summary(shop_id: int, business_date: date | str) -> dict:
    """
    Computes daily summary: total credit, total payment, and top 3 positive customer balances.
    """
    b_date = str(business_date)
    conn = get_connection()
    try:
        ensure_db_tables(conn)
        cursor = conn.cursor()

        # Day totals
        cursor.execute(
            """
            SELECT
                COALESCE(SUM(CASE WHEN direction = 'credit' THEN amount_paise ELSE 0 END), 0) AS credit_paise,
                COALESCE(SUM(CASE WHEN direction = 'payment' THEN amount_paise ELSE 0 END), 0) AS payment_paise
            FROM transactions
            WHERE shop_id = ? AND business_date = ? AND status = 'active'
            """,
            (shop_id, b_date),
        )
        totals = cursor.fetchone()
        credit_paise = int(totals["credit_paise"])
        payment_paise = int(totals["payment_paise"])

        # Customer balances across shop
        cursor.execute(
            """
            SELECT
                c.id AS customer_id,
                c.name AS customer_name,
                COALESCE(SUM(CASE WHEN t.direction = 'credit' THEN t.amount_paise ELSE 0 END), 0) -
                COALESCE(SUM(CASE WHEN t.direction = 'payment' THEN t.amount_paise ELSE 0 END), 0) AS balance_paise
            FROM customers c
            LEFT JOIN transactions t ON t.customer_id = c.id AND t.status = 'active'
            WHERE c.shop_id = ?
            GROUP BY c.id
            HAVING balance_paise > 0
            ORDER BY balance_paise DESC, c.name ASC
            LIMIT 3
            """,
            (shop_id,),
        )
        top_rows = cursor.fetchall()
        top_list = [
            {
                "customer_id": r["customer_id"],
                "customer_name": r["customer_name"],
                "balance_paise": int(r["balance_paise"]),
            }
            for r in top_rows
        ]

        return {
            "business_date": b_date,
            "credit_paise": credit_paise,
            "payment_paise": payment_paise,
            "top": top_list,
        }
    finally:
        conn.close()


def delete_shop_data(shop_id: int) -> None:
    """Cascading deletion of all data associated with a shop."""
    conn = get_connection()
    try:
        ensure_db_tables(conn)
        cursor = conn.cursor()
        # Delete correction history for shop's transactions
        cursor.execute(
            """
            DELETE FROM correction_history
            WHERE transaction_id IN (SELECT id FROM transactions WHERE shop_id = ?)
            """,
            (shop_id,),
        )
        cursor.execute("DELETE FROM transactions WHERE shop_id = ?", (shop_id,))
        cursor.execute("DELETE FROM conversation_sessions WHERE shop_id = ?", (shop_id,))
        cursor.execute("DELETE FROM customers WHERE shop_id = ?", (shop_id,))
        cursor.execute("DELETE FROM shops WHERE id = ?", (shop_id,))
        conn.commit()
    finally:
        conn.close()
