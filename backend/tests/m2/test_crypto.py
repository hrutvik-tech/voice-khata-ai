"""
backend/tests/m2/test_crypto.py

Tests for Member 2 crypto module (docs/contracts.md and prompt requirements):
1. Fernet mode encrypts raw_transcript and phone into ciphertext; decrypt_text restores them.
2. SQLCipher mode passes text fields through unchanged (whole-file encryption).
3. SQLCipher mode produces a database file that standard Python sqlite3 cannot read
   (skipped if sqlcipher3 is not installed).
"""

import os
import sqlite3
import pytest
from cryptography.fernet import Fernet
from sqlalchemy import text
from app.core.crypto import make_engine, encrypt_text, decrypt_text


def test_fernet_mode_encryption_and_decryption(monkeypatch):
    """Test that fernet mode stores ciphertext for raw_transcript and phone, and decrypts accurately."""
    key = Fernet.generate_key().decode("utf-8")
    monkeypatch.setenv("ENCRYPTION_MODE", "fernet")
    monkeypatch.setenv("DB_KEY", key)

    raw_phone = "9000000001"
    raw_transcript = "Ramesh Sharma ka 340 udhaar"

    # Encrypt
    enc_phone = encrypt_text(raw_phone)
    enc_transcript = encrypt_text(raw_transcript)

    assert enc_phone is not None
    assert enc_phone != raw_phone
    assert enc_transcript is not None
    assert enc_transcript != raw_transcript

    # Decrypt
    dec_phone = decrypt_text(enc_phone)
    dec_transcript = decrypt_text(enc_transcript)

    assert dec_phone == raw_phone
    assert dec_transcript == raw_transcript

    # None handling
    assert encrypt_text(None) is None
    assert decrypt_text(None) is None


def test_sqlcipher_mode_passthrough(monkeypatch):
    """Test that sqlcipher mode passes text fields through unchanged."""
    monkeypatch.setenv("ENCRYPTION_MODE", "sqlcipher")
    monkeypatch.setenv("DB_KEY", "any-key")

    raw_phone = "9000000001"
    raw_transcript = "Suresh ka 500 jama"

    assert encrypt_text(raw_phone) == raw_phone
    assert decrypt_text(raw_phone) == raw_phone
    assert encrypt_text(raw_transcript) == raw_transcript
    assert decrypt_text(raw_transcript) == raw_transcript


def test_make_engine_fernet_mode(tmp_path, monkeypatch):
    """Test that fernet mode creates a functional plain SQLite engine."""
    db_file = tmp_path / "test_fernet.db"
    monkeypatch.setenv("ENCRYPTION_MODE", "fernet")

    engine = make_engine(str(db_file))
    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE test_tab (id INT, name TEXT)"))
        conn.execute(text("INSERT INTO test_tab VALUES (1, 'kirana')"))
        res = conn.execute(text("SELECT name FROM test_tab WHERE id = 1")).scalar()

    assert res == "kirana"
    assert db_file.exists()

    # Plain sqlite3 can read it directly
    direct_conn = sqlite3.connect(str(db_file))
    cur = direct_conn.cursor()
    cur.execute("SELECT name FROM test_tab WHERE id = 1")
    assert cur.fetchone()[0] == "kirana"
    direct_conn.close()


def test_sqlcipher_file_unreadable_by_sqlite3(tmp_path, monkeypatch):
    """
    Test that sqlcipher mode produces a database file that Python's standard sqlite3 cannot read.
    Skipped when sqlcipher3 is not installed (e.g. standard developer laptops).
    """
    try:
        import sqlcipher3  # noqa: F401
    except ImportError:
        try:
            import pysqlcipher3  # noqa: F401
        except ImportError:
            pytest.skip("sqlcipher3 is not installed; skipping SQLCipher binary test")

    db_file = tmp_path / "test_sqlcipher.db"
    monkeypatch.setenv("ENCRYPTION_MODE", "sqlcipher")
    monkeypatch.setenv("DB_KEY", "super-secret-passphrase-123")

    engine = make_engine(str(db_file))
    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE secret_tab (id INT, info TEXT)"))
        conn.execute(text("INSERT INTO secret_tab VALUES (1, 'confidential')"))

    # Attempt to read the file using standard Python sqlite3 (without SQLCipher key)
    plain_conn = sqlite3.connect(str(db_file))
    cursor = plain_conn.cursor()
    with pytest.raises(sqlite3.DatabaseError):
        cursor.execute("SELECT * FROM secret_tab")
    plain_conn.close()
