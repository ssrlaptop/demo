"""FastAPI authentication/authorization dependencies."""

from __future__ import annotations

from collections.abc import Callable

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.auth.rbac import has_permission
from app.core.security import ACCESS_TOKEN_TYPE, InvalidTokenError, decode_token
from app.db.mongo import get_db
from app.models.enums import Permission
from app.models.user import User
from app.repositories.user_repo import MongoUserRepository, UserRepository

_bearer = HTTPBearer(auto_error=False)


def get_user_repo() -> UserRepository:
    return MongoUserRepository(get_db())


def _credentials_error() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    repo: UserRepository = Depends(get_user_repo),
) -> User:
    if credentials is None or not credentials.credentials:
        raise _credentials_error()

    try:
        payload = decode_token(credentials.credentials, expected_type=ACCESS_TOKEN_TYPE)
    except InvalidTokenError as exc:
        raise _credentials_error() from exc

    user = repo.get_by_id(str(payload["sub"]))
    if user is None or not user.is_active:
        raise _credentials_error()
    return user


def require_permission(permission: Permission) -> Callable[[User], User]:
    def _checker(user: User = Depends(get_current_user)) -> User:
        if not has_permission(user, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return user

    return _checker
