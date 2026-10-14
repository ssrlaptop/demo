"""Health/readiness endpoints. Never require authentication."""

from __future__ import annotations

from fastapi import APIRouter

from app.db import ping

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict:
    db_ok = ping()
    return {
        "status": "ok",
        "mongodb": "connected" if db_ok else "unavailable",
    }


@router.get("/ready")
def ready() -> dict:
    return {"status": "ready"}
