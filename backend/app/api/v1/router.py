from fastapi import APIRouter

from app.api.v1.routers import audit, auth, health, proposals, users

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(proposals.router)
api_router.include_router(audit.router)

__all__ = ["api_router"]
