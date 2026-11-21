"""
backend/app/core/retention.py

Data retention policies and cleanup routines for Bolta Khata AI.
- purge(now): sets raw_transcript to NULL on transactions recorded more than
  TRANSCRIPT_RETENTION_HOURS ago, deletes expired conversation_sessions, and returns the counts.
- retention_loop(): runs purge() at startup and then hourly.
- CLI: python -m app.core.retention --all clears every raw_transcript (run after judging).
"""

import argparse
import asyncio
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from sqlalchemy import text
from app.core.crypto import make_engine


def get_retention_db_path() -> str:
    """Returns database path from environment."""
    return os.getenv("DB_PATH", os.getenv("DATABASE_PATH", "./data/khata.db"))


def get_retention_hours() -> int:
    """Returns transcript retention threshold in hours (default: 48)."""
    raw = os.getenv("TRANSCRIPT_RETENTION_HOURS", "48")
    try:
        return int(raw)
    except ValueError:
        return 48


def purge(now: datetime | None = None, db_path: str | None = None) -> dict:
    """
    Purges transcripts older than TRANSCRIPT_RETENTION_HOURS and deletes expired conversation sessions.
    Returns: {"transcripts_cleared": n, "sessions_deleted": n}
    """
    if now is None:
        now = datetime.now(timezone.utc)
    elif now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)

    hours = get_retention_hours()
    cutoff = now - timedelta(hours=hours)

    path = db_path or get_retention_db_path()
    engine = make_engine(path)

    cutoff_iso = cutoff.isoformat()
    now_iso = now.isoformat()

    transcripts_cleared = 0
    sessions_deleted = 0

    with engine.begin() as conn:
        # Update raw_transcript to NULL on transactions older than cutoff
        try:
            res_tx = conn.execute(
                text(
                    """
                    UPDATE transactions
                    SET raw_transcript = NULL
                    WHERE raw_transcript IS NOT NULL
                      AND (
                          recorded_at < :cutoff_iso
                          OR datetime(recorded_at) < datetime(:cutoff_iso)
                      )
                    """
                ),
                {"cutoff_iso": cutoff_iso},
            )
            transcripts_cleared = res_tx.rowcount if res_tx.rowcount is not None else 0
        except Exception as e:
            # Table might not exist yet
            pass

        # Delete expired conversation sessions
        try:
            res_sess = conn.execute(
                text(
                    """
                    DELETE FROM conversation_sessions
                    WHERE expires_at < :now_iso
                       OR datetime(expires_at) < datetime(:now_iso)
                    """
                ),
                {"now_iso": now_iso},
            )
            sessions_deleted = res_sess.rowcount if res_sess.rowcount is not None else 0
        except Exception as e:
            # Table might not exist yet
            pass

    return {
        "transcripts_cleared": max(0, transcripts_cleared),
        "sessions_deleted": max(0, sessions_deleted),
    }


def clear_all(db_path: str | None = None) -> int:
    """
    Clears every raw_transcript across all transactions (used post-judging / demo reset).
    Returns count of cleared transcripts.
    """
    path = db_path or get_retention_db_path()
    engine = make_engine(path)

    with engine.begin() as conn:
        try:
            res = conn.execute(
                text(
                    """
                    UPDATE transactions
                    SET raw_transcript = NULL
                    WHERE raw_transcript IS NOT NULL
                    """
                )
            )
            return res.rowcount if res.rowcount is not None else 0
        except Exception:
            return 0


async def retention_loop() -> None:
    """
    Background worker loop: executes purge() immediately at start,
    and then repeats every hour (3600 seconds).
    """
    while True:
        try:
            purge()
        except Exception as err:
            # Keep loop resilient
            pass
        await asyncio.sleep(3600)


def main() -> None:
    """CLI entry point for retention management."""
    parser = argparse.ArgumentParser(description="Bolta Khata data retention utility")
    parser.add_argument(
        "--all",
        action="store_true",
        help="Clear every raw_transcript in the database (run after judging)",
    )
    args = parser.parse_args()

    if args.all:
        count = clear_all()
        print(f"cleared {count} raw transcripts")
    else:
        res = purge()
        print(f"purged: {res}")


if __name__ == "__main__":
    main()
