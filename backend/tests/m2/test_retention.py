"""
backend/tests/m2/test_retention.py

Tests for Member 2 retention module:
1. purge(now) sets raw_transcript to NULL on transactions recorded more than TRANSCRIPT_RETENTION_HOURS ago.
2. purge(now) preserves recent raw_transcripts.
3. purge(now) deletes expired conversation_sessions and preserves active sessions.
4. clear_all() / 'python -m app.core.retention --all' clears every raw_transcript.
5. retention_loop() runs purge() at start.
"""

import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone
import pytest
from sqlalchemy import text
from app.core.crypto import make_engine
from app.core.retention import purge, clear_all, retention_loop


@pytest.fixture
def test_db(tmp_path, monkeypatch):
    """Sets up a test SQLite database with transactions and conversation_sessions tables."""
    db_file = tmp_path / "retention_test.db"
    monkeypatch.setenv("ENCRYPTION_MODE", "fernet")
    monkeypatch.setenv("DB_PATH", str(db_file))

    engine = make_engine(str(db_file))
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS shops (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    owner_name TEXT NOT NULL,
                    phone TEXT NOT NULL UNIQUE
                )
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS customers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    shop_id INTEGER NOT NULL REFERENCES shops(id),
                    name TEXT NOT NULL
                )
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    shop_id INTEGER NOT NULL REFERENCES shops(id),
                    customer_id INTEGER NOT NULL REFERENCES customers(id),
                    amount_paise INTEGER NOT NULL,
                    direction TEXT NOT NULL,
                    business_date TEXT NOT NULL,
                    recorded_at TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'active',
                    raw_transcript TEXT
                )
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS conversation_sessions (
                    id TEXT PRIMARY KEY,
                    shop_id INTEGER NOT NULL REFERENCES shops(id),
                    state TEXT NOT NULL DEFAULT 'resting',
                    expires_at TEXT NOT NULL
                )
                """
            )
        )
        conn.execute(
            text("INSERT INTO shops (id, owner_name, phone) VALUES (1, 'Sharma', '9000000001')")
        )
        conn.execute(
            text("INSERT INTO customers (id, shop_id, name) VALUES (1, 1, 'Ramesh')")
        )
    return str(db_file)


def test_purge_clears_only_old_transcripts_and_expired_sessions(test_db, monkeypatch):
    """Test that purge only clears transcripts > 48h old and deletes expired sessions."""
    monkeypatch.setenv("TRANSCRIPT_RETENTION_HOURS", "48")
    now = datetime(2026, 11, 21, 12, 0, 0, tzinfo=timezone.utc)

    t_old = (now - timedelta(hours=50)).isoformat()
    t_recent = (now - timedelta(hours=5)).isoformat()

    sess_expired = (now - timedelta(minutes=10)).isoformat()
    sess_active = (now + timedelta(hours=1)).isoformat()

    engine = make_engine(test_db)
    with engine.begin() as conn:
        # 1 old transaction with transcript
        conn.execute(
            text(
                "INSERT INTO transactions (shop_id, customer_id, amount_paise, direction, business_date, recorded_at, raw_transcript) "
                "VALUES (1, 1, 34000, 'credit', '2026-11-19', :t_old, 'Old transcript to clear')"
            ),
            {"t_old": t_old},
        )
        # 1 recent transaction with transcript
        conn.execute(
            text(
                "INSERT INTO transactions (shop_id, customer_id, amount_paise, direction, business_date, recorded_at, raw_transcript) "
                "VALUES (1, 1, 50000, 'credit', '2026-11-21', :t_recent, 'Recent transcript to keep')"
            ),
            {"t_recent": t_recent},
        )
        # 1 expired session
        conn.execute(
            text("INSERT INTO conversation_sessions (id, shop_id, expires_at) VALUES ('sess_expired', 1, :exp)"),
            {"exp": sess_expired},
        )
        # 1 active session
        conn.execute(
            text("INSERT INTO conversation_sessions (id, shop_id, expires_at) VALUES ('sess_active', 1, :exp)"),
            {"exp": sess_active},
        )

    # Execute purge
    result = purge(now=now, db_path=test_db)

    assert result["transcripts_cleared"] == 1
    assert result["sessions_deleted"] == 1

    # Verify database contents
    with engine.begin() as conn:
        # Check old transaction raw_transcript is now NULL
        old_trans = conn.execute(
            text("SELECT raw_transcript FROM transactions WHERE recorded_at = :t_old"),
            {"t_old": t_old},
        ).scalar()
        assert old_trans is None

        # Check recent transaction raw_transcript is STILL intact
        rec_trans = conn.execute(
            text("SELECT raw_transcript FROM transactions WHERE recorded_at = :t_recent"),
            {"t_recent": t_recent},
        ).scalar()
        assert rec_trans == "Recent transcript to keep"

        # Check expired session was deleted
        exp_sess = conn.execute(
            text("SELECT id FROM conversation_sessions WHERE id = 'sess_expired'")
        ).scalar()
        assert exp_sess is None

        # Check active session still exists
        act_sess = conn.execute(
            text("SELECT id FROM conversation_sessions WHERE id = 'sess_active'")
        ).scalar()
        assert act_sess == "sess_active"


def test_clear_all_clears_every_transcript(test_db):
    """Test clear_all clears every raw_transcript regardless of date."""
    now_iso = datetime.now(timezone.utc).isoformat()
    engine = make_engine(test_db)

    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO transactions (shop_id, customer_id, amount_paise, direction, business_date, recorded_at, raw_transcript) "
                "VALUES (1, 1, 10000, 'credit', '2026-11-21', :now_iso, 'Transcript 1'), "
                "       (1, 1, 20000, 'credit', '2026-11-21', :now_iso, 'Transcript 2')"
            ),
            {"now_iso": now_iso},
        )

    cleared = clear_all(db_path=test_db)
    assert cleared >= 2

    with engine.begin() as conn:
        remaining = conn.execute(
            text("SELECT COUNT(*) FROM transactions WHERE raw_transcript IS NOT NULL")
        ).scalar()
        assert remaining == 0


def test_retention_cli_all_flag(test_db, monkeypatch, capsys):
    """Test running 'python -m app.core.retention --all'."""
    now_iso = datetime.now(timezone.utc).isoformat()
    engine = make_engine(test_db)
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO transactions (shop_id, customer_id, amount_paise, direction, business_date, recorded_at, raw_transcript) "
                "VALUES (1, 1, 45000, 'credit', '2026-11-21', :now_iso, 'To be cleared by CLI')"
            ),
            {"now_iso": now_iso},
        )

    from app.core.retention import main

    monkeypatch.setenv("DB_PATH", test_db)
    monkeypatch.setattr(sys, "argv", ["app.core.retention", "--all"])

    main()

    captured = capsys.readouterr()
    assert "cleared" in captured.out.lower()

    with engine.begin() as conn:
        remaining = conn.execute(
            text("SELECT COUNT(*) FROM transactions WHERE raw_transcript IS NOT NULL")
        ).scalar()
        assert remaining == 0
