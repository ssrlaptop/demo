"""Admin user-management endpoints (RBAC-gated)."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.auth.dependencies import get_user_repo, require_permission
from app.models.enums import Permission
from app.models.user import User
from app.repositories.user_repo import UserRepository
from app.schemas.auth import UserOut

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=list[UserOut])
def list_users(
    _: User = Depends(require_permission(Permission.USER_MANAGE)),
    repo: UserRepository = Depends(get_user_repo),
) -> list[UserOut]:
    return [
        UserOut(
            id=user.id,
            username=user.username,
            email=user.email,
            full_name=user.full_name,
            role=user.role,
            department=user.department,
            is_active=user.is_active,
        )
        for user in repo.list_all()
    ]
