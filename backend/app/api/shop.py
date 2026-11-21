"""
backend/app/api/shop.py

Shop profile API routes for Bolta Khata AI.
Handles retrieving and updating shop settings.
"""

from typing import Any, Literal
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, field_validator, model_validator
from app.database.db import get_connection
from app.core.tokens import (
    ensure_shops_table,
    format_shop,
    get_current_shop,
)

router = APIRouter(prefix="/shop", tags=["shop"])

TIME_PATTERN = r"^(?:[01]\d|2[0-3]):[0-5]\d$"


class UpdateShopRequest(BaseModel):
    shop_name: str = Field(..., min_length=1, max_length=80)
    open_time: str = Field(..., pattern=TIME_PATTERN)
    close_time: str = Field(..., pattern=TIME_PATTERN)
    language_mode: Literal["hi", "kn", "en", "mix"]

    @field_validator("shop_name")
    @classmethod
    def validate_shop_name(cls, v: str) -> str:
        trimmed = v.strip()
        if not trimmed:
            raise ValueError("shop_name cannot be empty or whitespace only")
        if len(trimmed) > 80:
            raise ValueError("shop_name cannot exceed 80 characters")
        return trimmed

    @model_validator(mode="after")
    def validate_open_and_close_different(self) -> "UpdateShopRequest":
        if self.open_time == self.close_time:
            raise ValueError("open_time and close_time must not be equal")
        return self


@router.get("", response_model=None)
@router.get("/", response_model=None, include_in_schema=False)
def get_shop(current_shop: dict = Depends(get_current_shop)) -> dict[str, Any]:
    return format_shop(current_shop)


@router.put("", response_model=None)
@router.put("/", response_model=None, include_in_schema=False)
def update_shop(
    payload: UpdateShopRequest,
    current_shop: dict = Depends(get_current_shop),
) -> dict[str, Any]:
    conn = get_connection()
    try:
        ensure_shops_table(conn)
        cursor = conn.cursor()

        cursor.execute(
            """
            UPDATE shops
            SET shop_name = ?,
                open_time = ?,
                close_time = ?,
                language_mode = ?,
                setup_complete = 1
            WHERE id = ?
            """,
            (
                payload.shop_name,
                payload.open_time,
                payload.close_time,
                payload.language_mode,
                current_shop["id"],
            ),
        )
        conn.commit()

        cursor.execute("SELECT * FROM shops WHERE id = ?", (current_shop["id"],))
        updated_row = cursor.fetchone()
        return format_shop(updated_row)
    finally:
        conn.close()
