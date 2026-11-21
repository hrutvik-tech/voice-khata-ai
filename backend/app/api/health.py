"""
backend/app/api/health.py
Health-check endpoint — GET /api/health
"""

from fastapi import APIRouter

router = APIRouter()


@router.get("/health", tags=["health"])
def health_check() -> dict:
    """
    Returns a simple status payload.
    Use this to verify the backend is running before wiring up real features.
    """
    return {
        "status": "ok",
        "service": "bolta-khata-ai-backend",
        "version": "0.1.0",
    }
