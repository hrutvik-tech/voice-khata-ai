"""
backend/app/api/me.py

Account deletion endpoint for Bolta Khata AI:
- DELETE /me
Deletes the current shop and all associated data, invalidating all issued tokens.
"""

from fastapi import APIRouter, Depends, Response, status
from app.core.tokens import get_current_shop
from app.services.ledger import delete_shop_data

router = APIRouter(tags=["me"])


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
def delete_account(current_shop: dict = Depends(get_current_shop)) -> Response:
    delete_shop_data(current_shop["id"])
    return Response(status_code=status.HTTP_204_NO_CONTENT)
