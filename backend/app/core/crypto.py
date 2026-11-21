"""
backend/app/core/crypto.py

Database engine factory and field-level encryption helpers for Bolta Khata AI.
Supports two encryption modes defined in docs/contracts.md:
- 'fernet' (default for development/laptops): plain SQLite database file with
  application-level Fernet ciphertext for sensitive text fields (raw_transcript, phone).
- 'sqlcipher' (production / Linux server): entire SQLite database file is encrypted at rest
  using SQLCipher (sqlite+pysqlcipher). Text fields pass through unencrypted.
"""

import os
import urllib.parse
from pathlib import Path
from sqlalchemy.engine import Engine, URL, create_engine
from cryptography.fernet import Fernet, InvalidToken


def get_encryption_mode() -> str:
    """Returns normalized encryption mode ('fernet' or 'sqlcipher')."""
    return os.getenv("ENCRYPTION_MODE", "fernet").strip().lower()


def get_db_key() -> str:
    """Returns database encryption key or passphrase from environment."""
    return os.getenv("DB_KEY", "")


def make_engine(db_path: str) -> Engine:
    """
    Creates and returns a SQLAlchemy Engine for the SQLite database.
    - If ENCRYPTION_MODE=sqlcipher: creates the engine with sqlite+pysqlcipher dialect,
      the URL-encoded DB_KEY as the passphrase, and the absolute DB path.
    - If ENCRYPTION_MODE=fernet: creates a plain SQLite engine.
    """
    mode = get_encryption_mode()
    abs_path = Path(db_path).resolve()
    abs_path.parent.mkdir(parents=True, exist_ok=True)

    if mode == "sqlcipher":
        key = get_db_key()
        # SQLAlchemy URL for sqlite+pysqlcipher
        url = URL.create(
            drivername="sqlite+pysqlcipher",
            password=key,
            host="",
            database=str(abs_path),
        )
        return create_engine(url)

    # Default: plain SQLite engine
    return create_engine(f"sqlite:///{abs_path.as_posix()}")


def encrypt_text(value: str | None) -> str | None:
    """
    Encrypts a text string using Fernet(DB_KEY) in fernet mode.
    Passes through unchanged in sqlcipher mode.
    Returns None if value is None.
    """
    if value is None:
        return None

    mode = get_encryption_mode()
    if mode == "sqlcipher":
        return value

    # Fernet mode
    key = get_db_key()
    if not key:
        return value

    f = Fernet(key.encode("utf-8") if isinstance(key, str) else key)
    return f.encrypt(value.encode("utf-8")).decode("utf-8")


def decrypt_text(value: str | None) -> str | None:
    """
    Decrypts a text string using Fernet(DB_KEY) in fernet mode.
    Passes through unchanged in sqlcipher mode.
    Returns None if value is None.
    """
    if value is None:
        return None

    mode = get_encryption_mode()
    if mode == "sqlcipher":
        return value

    # Fernet mode
    key = get_db_key()
    if not key:
        return value

    try:
        f = Fernet(key.encode("utf-8") if isinstance(key, str) else key)
        return f.decrypt(value.encode("utf-8")).decode("utf-8")
    except (InvalidToken, Exception):
        # Fall back to raw value if not encrypted (e.g. unencrypted seed/test data)
        return value
