"""
backend/app/services/conversation.py

Conversation session management for Bolta Khata AI.
Tracks session state, last transactions, pending questions, and disclosure flags.
"""

import json
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any
from app.database.db import get_connection
from app.core.tokens import ensure_db_tables

SESSION_IDLE_MINUTES = 30


def get_or_create_session(
    shop_id: int,
    now: datetime | None = None,
    session_id: str | None = None,
) -> dict[str, Any]:
    """
    Retrieves an active session or creates a new one.
    Sessions expire after 30 minutes of idle time.
    """
    if now is None:
        now = datetime.now(timezone.utc)
    now_iso = now.isoformat()
    expires_iso = (now + timedelta(minutes=SESSION_IDLE_MINUTES)).isoformat()

    conn = get_connection()
    try:
        ensure_db_tables(conn)
        cursor = conn.cursor()

        if session_id:
            cursor.execute(
                "SELECT * FROM conversation_sessions WHERE id = ? AND shop_id = ?",
                (session_id, shop_id),
            )
            row = cursor.fetchone()
            if row:
                # Check expiration
                if row["expires_at"] > now_iso:
                    # Active session, extend expiration
                    cursor.execute(
                        """
                        UPDATE conversation_sessions
                        SET expires_at = ?, updated_at = ?
                        WHERE id = ?
                        """,
                        (expires_iso, now_iso, session_id),
                    )
                    conn.commit()
                    cursor.execute("SELECT * FROM conversation_sessions WHERE id = ?", (session_id,))
                    return dict(cursor.fetchone())

        # Look for most recent unexpired session for this shop
        cursor.execute(
            """
            SELECT * FROM conversation_sessions
            WHERE shop_id = ? AND expires_at > ?
            ORDER BY updated_at DESC
            LIMIT 1
            """,
            (shop_id, now_iso),
        )
        existing = cursor.fetchone()
        if existing:
            s_id = existing["id"]
            cursor.execute(
                """
                UPDATE conversation_sessions
                SET expires_at = ?, updated_at = ?
                WHERE id = ?
                """,
                (expires_iso, now_iso, s_id),
            )
            conn.commit()
            cursor.execute("SELECT * FROM conversation_sessions WHERE id = ?", (s_id,))
            return dict(cursor.fetchone())

        # Create new session
        new_id = str(uuid.uuid4())
        cursor.execute(
            """
            INSERT INTO conversation_sessions (
                id, shop_id, state, last_txn_id, last_txn_at, pending_json,
                disclosed, last_language, expires_at, updated_at
            ) VALUES (?, ?, 'resting', NULL, NULL, NULL, 0, NULL, ?, ?)
            """,
            (new_id, shop_id, expires_iso, now_iso),
        )
        conn.commit()
        cursor.execute("SELECT * FROM conversation_sessions WHERE id = ?", (new_id,))
        return dict(cursor.fetchone())
    finally:
        conn.close()


def get_session(session_id: str) -> dict[str, Any] | None:
    """Retrieves session record by ID."""
    conn = get_connection()
    try:
        ensure_db_tables(conn)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM conversation_sessions WHERE id = ?", (session_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def update_session(session_id: str, **kwargs: Any) -> dict[str, Any]:
    """Updates fields on an existing session."""
    now_iso = datetime.now(timezone.utc).isoformat()
    fields = []
    values = []

    for k, v in kwargs.items():
        if k == "pending_json" and isinstance(v, (dict, list)):
            v = json.dumps(v)
        fields.append(f"{k} = ?")
        values.append(v)

    fields.append("updated_at = ?")
    values.append(now_iso)
    values.append(session_id)

    query = f"UPDATE conversation_sessions SET {', '.join(fields)} WHERE id = ?"

    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(query, tuple(values))
        conn.commit()
        cursor.execute("SELECT * FROM conversation_sessions WHERE id = ?", (session_id,))
        return dict(cursor.fetchone())
    finally:
        conn.close()
