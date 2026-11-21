"""
backend/app/api/auth.py

Authentication API routes for Bolta Khata AI.
Handles shop registration, login, and PIN change.
"""

from typing import Any
from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, Field, field_validator
from app.database.db import get_connection
from app.core.tokens import (
    create_access_token,
    ensure_shops_table,
    format_shop,
    get_current_shop,
    hash_pin,
    verify_pin,
)

router = APIRouter(prefix="/auth", tags=["auth"])


class RegisterRequest(BaseModel):
    owner_name: str = Field(..., min_length=1, max_length=60)
    phone: str = Field(..., pattern=r"^\d{10}$")
    pin: str = Field(..., pattern=r"^\d{4,6}$")

    @field_validator("owner_name")
    @classmethod
    def validate_owner_name(cls, v: str) -> str:
        trimmed = v.strip()
        if not trimmed:
            raise ValueError("owner_name cannot be empty or whitespace only")
        if len(trimmed) > 60:
            raise ValueError("owner_name cannot exceed 60 characters")
        return trimmed


class LoginRequest(BaseModel):
    phone: str = Field(..., pattern=r"^\d{10}$")
    pin: str = Field(..., min_length=1)


class ChangePinRequest(BaseModel):
    old_pin: str = Field(..., min_length=1)
    new_pin: str = Field(..., pattern=r"^\d{4,6}$")


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest) -> dict[str, Any]:
    conn = get_connection()
    try:
        ensure_shops_table(conn)
        cursor = conn.cursor()

        cursor.execute("SELECT id FROM shops WHERE phone = ?", (payload.phone,))
        existing = cursor.fetchone()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="phone_exists",
            )

        hashed_pin = hash_pin(payload.pin)
        cursor.execute(
            """
            INSERT INTO shops (
                owner_name, shop_name, phone, pin_hash, open_time, close_time, timezone, language_mode, setup_complete
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                payload.owner_name,
                "",
                payload.phone,
                hashed_pin,
                "06:00",
                "02:00",
                "Asia/Kolkata",
                "mix",
                0,
            ),
        )
        conn.commit()
        shop_id = cursor.lastrowid

        cursor.execute("SELECT * FROM shops WHERE id = ?", (shop_id,))
        shop_row = cursor.fetchone()
        token = create_access_token(shop_id)
        return {
            "token": token,
            "shop": format_shop(shop_row),
        }
    finally:
        conn.close()


@router.post("/login")
def login(payload: LoginRequest) -> dict[str, Any]:
    conn = get_connection()
    try:
        ensure_shops_table(conn)
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM shops WHERE phone = ?", (payload.phone,))
        shop_row = cursor.fetchone()

        if not shop_row or not verify_pin(payload.pin, shop_row["pin_hash"]):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="wrong_pin",
            )

        shop_id = shop_row["id"]
        token = create_access_token(shop_id)
        return {
            "token": token,
            "shop": format_shop(shop_row),
        }
    finally:
        conn.close()


@router.put("/pin", status_code=status.HTTP_204_NO_CONTENT)
def change_pin(
    payload: ChangePinRequest,
    current_shop: dict = Depends(get_current_shop),
) -> Response:
    if not verify_pin(payload.old_pin, current_shop["pin_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="wrong_pin",
        )

    conn = get_connection()
    try:
        cursor = conn.cursor()
        new_hashed_pin = hash_pin(payload.new_pin)
        cursor.execute(
            "UPDATE shops SET pin_hash = ? WHERE id = ?",
            (new_hashed_pin, current_shop["id"]),
        )
        conn.commit()
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    finally:
        conn.close()
