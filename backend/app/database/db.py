"""
backend/app/database/db.py

SQLite connection helper using Python's built-in sqlite3 module.
No ORM — raw sqlite3 for now. An ORM (e.g. SQLAlchemy) can be introduced later.

Usage:
    from app.database.db import get_connection

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT 1")
    conn.close()
"""

import os
import sqlite3
from pathlib import Path


def get_db_path() -> str:
    """
    Returns the absolute path to the SQLite database file.
    Reads DATABASE_PATH from the environment (set in .env).
    Defaults to 'khata.db' in the backend/ directory.
    """
    raw = os.getenv("DATABASE_PATH", "./khata.db")
    # Resolve relative to the backend/ directory (parent of app/)
    base = Path(__file__).parent.parent.parent
    path = (base / raw).resolve()
    return str(path)


def get_connection() -> sqlite3.Connection:
    """
    Opens and returns a sqlite3 connection with WAL mode enabled
    for better concurrent read performance.

    The caller is responsible for closing the connection.
    """
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.row_factory = sqlite3.Row  # rows accessible as dicts
    return conn
