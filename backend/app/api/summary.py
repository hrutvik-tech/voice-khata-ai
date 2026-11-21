"""
backend/app/api/summary.py

Daily summary API endpoint for Bolta Khata AI:
- GET /summary/today
"""

from typing import Any
from fastapi import APIRouter, Depends
from app.core.tokens import get_current_shop
from app.services.ledger import day_summary, get_shop_business_date

router = APIRouter(prefix="/summary", tags=["summary"])


@router.get("/today")
def get_today_summary(current_shop: dict = Depends(get_current_shop)) -> dict[str, Any]:
    b_date = get_shop_business_date(current_shop)
    return day_summary(shop_id=current_shop["id"], business_date=b_date)
