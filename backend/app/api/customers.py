"""
backend/app/api/customers.py

Customer management API endpoints for Bolta Khata AI:
- GET /customers?search=
- POST /customers
- GET /customers/{id}
"""

from typing import Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.core.tokens import get_current_shop
from app.database.db import get_connection
from app.services.ledger import (
    create_customer,
    customer_balance,
    decrypt_text,
    find_similar_customers,
    list_customers,
)

router = APIRouter(prefix="/customers", tags=["customers"])


class CreateCustomerRequest(BaseModel):
    name: str = Field(..., min_length=1)
    phone: str | None = None
    area: str | None = None
    confirm: bool = False


@router.get("")
def get_customers(
    search: str | None = Query(None),
    current_shop: dict = Depends(get_current_shop),
) -> list[dict[str, Any]]:
    return list_customers(shop_id=current_shop["id"], search=search)


@router.post("", status_code=status.HTTP_201_CREATED)
def add_customer(
    payload: CreateCustomerRequest,
    current_shop: dict = Depends(get_current_shop),
) -> dict[str, Any]:
    name = payload.name.strip()
    if not name:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Name cannot be empty",
        )

    # Check for similar customers unless confirm is True
    if not payload.confirm:
        similar = find_similar_customers(shop_id=current_shop["id"], name=name)
        if similar:
            sim_list = [
                {"id": s["id"], "name": s["name"], "area": s["area"]}
                for s in similar
            ]
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"detail": "similar_exists", "similar": sim_list},
            )

    customer = create_customer(
        shop_id=current_shop["id"],
        name=name,
        phone=payload.phone,
        area=payload.area,
        source="manual",
    )
    return {"customer": customer}


@router.get("/{customer_id}")
def get_customer_profile(
    customer_id: int,
    current_shop: dict = Depends(get_current_shop),
) -> dict[str, Any]:
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM customers WHERE id = ? AND shop_id = ?",
            (customer_id, current_shop["id"]),
        )
        cust_row = cursor.fetchone()
        if not cust_row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Customer not found",
            )

        customer_dict = {
            "id": cust_row["id"],
            "shop_id": cust_row["shop_id"],
            "name": cust_row["name"],
            "name_key": cust_row["name_key"],
            "phone": decrypt_text(cust_row["phone"]),
            "area": cust_row["area"],
            "source": cust_row["source"],
            "created_at": str(cust_row["created_at"]),
        }

        bal = customer_balance(customer_id)

        # Get entries newest first, including undone
        cursor.execute(
            """
            SELECT id, customer_id, amount_paise, direction, business_date,
                   recorded_at, status, source, language, idempotency_key
            FROM transactions
            WHERE customer_id = ?
            ORDER BY recorded_at DESC, id DESC
            """,
            (customer_id,),
        )
        txn_rows = cursor.fetchall()
        entries = []

        for t in txn_rows:
            txn_id = t["id"]
            cursor.execute(
                """
                SELECT action, old_amount_paise, new_amount_paise, at
                FROM correction_history
                WHERE transaction_id = ?
                ORDER BY at ASC, id ASC
                """,
                (txn_id,),
            )
            hist_rows = cursor.fetchall()
            history = [
                {
                    "action": h["action"],
                    "old_amount_paise": h["old_amount_paise"],
                    "new_amount_paise": h["new_amount_paise"],
                    "at": str(h["at"]),
                }
                for h in hist_rows
            ]

            entries.append({
                "id": t["id"],
                "customer_id": t["customer_id"],
                "customer_name": cust_row["name"],
                "amount_paise": t["amount_paise"],
                "direction": t["direction"],
                "business_date": t["business_date"],
                "recorded_at": t["recorded_at"],
                "status": t["status"],
                "source": t["source"],
                "language": t["language"],
                "history": history,
            })

        return {
            "customer": customer_dict,
            "balance_paise": bal,
            "entries": entries,
        }
    finally:
        conn.close()
