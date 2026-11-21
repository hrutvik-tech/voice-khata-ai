"""
backend/app/core/tokens.py

JWT creation, verification, and authentication dependencies for Bolta Khata AI.
Also provides database table initialization, PIN hashing, and shop serialization helpers.
"""

import os
from datetime import datetime, timedelta, timezone
from typing import Any
import bcrypt
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from app.database.db import get_connection

security = HTTPBearer(auto_error=False)


def get_jwt_secret() -> str:
    """
    Safely retrieves the JWT secret from environment variables.
    Never uses an insecure hardcoded fallback.
    """
    secret = os.getenv("JWT_SECRET")
    if not secret:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="JWT_SECRET is not configured",
        )
    return secret


def get_jwt_expire_days() -> int:
    raw = os.getenv("JWT_EXPIRE_DAYS", "30")
    try:
        return int(raw)
    except ValueError:
        return 30


def create_access_token(shop_id: int) -> str:
    secret = get_jwt_secret()
    expire_days = get_jwt_expire_days()
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(shop_id),
        "shop_id": shop_id,
        "iat": now,
        "exp": now + timedelta(days=expire_days),
    }
    return jwt.encode(payload, secret, algorithm="HS256")


def decode_access_token(token: str) -> dict:
    secret = get_jwt_secret()
    try:
        payload = jwt.decode(token, secret, algorithms=["HS256"])
        return payload
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="unauthorized",
        )


def get_current_shop_id(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> int:
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="unauthorized",
        )
    payload = decode_access_token(credentials.credentials)
    shop_id = payload.get("shop_id")
    if not shop_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="unauthorized",
        )
    return int(shop_id)


def get_current_shop(shop_id: int = Depends(get_current_shop_id)) -> dict:
    conn = get_connection()
    try:
        ensure_db_tables(conn)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM shops WHERE id = ?", (shop_id,))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="unauthorized",
            )
        return dict(row)
    finally:
        conn.close()


def ensure_db_tables(conn) -> None:
    """Ensures all 5 tables exist according to docs/contracts.md schema."""
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS shops (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            owner_name TEXT NOT NULL,
            shop_name TEXT NOT NULL DEFAULT '',
            phone TEXT NOT NULL UNIQUE,
            pin_hash TEXT NOT NULL,
            open_time TEXT NOT NULL DEFAULT '06:00',
            close_time TEXT NOT NULL DEFAULT '02:00',
            timezone TEXT NOT NULL DEFAULT 'Asia/Kolkata',
            language_mode TEXT NOT NULL DEFAULT 'mix',
            setup_complete BOOLEAN NOT NULL DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            shop_id INTEGER NOT NULL REFERENCES shops(id),
            name TEXT NOT NULL,
            name_key TEXT NOT NULL,
            phone TEXT,
            area TEXT,
            source TEXT NOT NULL DEFAULT 'manual',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            shop_id INTEGER NOT NULL REFERENCES shops(id),
            customer_id INTEGER NOT NULL REFERENCES customers(id),
            amount_paise INTEGER NOT NULL CHECK (amount_paise > 0),
            direction TEXT NOT NULL CHECK (direction IN ('credit', 'payment')),
            business_date TEXT NOT NULL,
            recorded_at TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'undone')),
            source TEXT NOT NULL DEFAULT 'voice',
            language TEXT,
            raw_transcript TEXT,
            session_id TEXT,
            idempotency_key TEXT UNIQUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS correction_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            transaction_id INTEGER NOT NULL REFERENCES transactions(id),
            action TEXT NOT NULL CHECK (action IN ('amend', 'undo')),
            old_amount_paise INTEGER NOT NULL,
            new_amount_paise INTEGER,
            session_id TEXT,
            at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS conversation_sessions (
            id TEXT PRIMARY KEY,
            shop_id INTEGER NOT NULL REFERENCES shops(id),
            state TEXT NOT NULL DEFAULT 'resting',
            last_txn_id INTEGER,
            last_txn_at TEXT,
            pending_json TEXT,
            disclosed BOOLEAN NOT NULL DEFAULT 0,
            last_language TEXT,
            expires_at TEXT NOT NULL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
    )
    conn.commit()


def ensure_shops_table(conn) -> None:
    """Backward-compatible alias for ensure_db_tables."""
    ensure_db_tables(conn)


def hash_pin(pin: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pin.encode("utf-8"), salt).decode("utf-8")


def verify_pin(pin: str, pin_hash: str) -> bool:
    try:
        return bcrypt.checkpw(pin.encode("utf-8"), pin_hash.encode("utf-8"))
    except Exception:
        return False


def format_shop(row: Any) -> dict:
    """
    Serializes a shop database row to the exact schema defined in docs/contracts.md.
    Never exposes internal credentials or pin_hash.
    """
    return {
        "id": int(row["id"]),
        "owner_name": str(row["owner_name"]),
        "shop_name": str(row["shop_name"]),
        "phone": str(row["phone"]),
        "open_time": str(row["open_time"]),
        "close_time": str(row["close_time"]),
        "timezone": str(row["timezone"]),
        "language_mode": str(row["language_mode"]),
        "setup_complete": bool(row["setup_complete"]),
    }
