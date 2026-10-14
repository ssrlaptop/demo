"""Authentication service: login and token refresh."""

from __future__ import annotations

from app.core.security import (
    REFRESH_TOKEN_TYPE,
    InvalidTokenError,
    create_access_token,
    create_refresh_token,
    decode_token,
    verify_password,
)
from app.models.user import User
from app.repositories.user_repo import UserRepository


class AuthError(Exception):
    pass


def authenticate(repo: UserRepository, username: str, password: str) -> User:
    user = repo.get_by_username(username)
    # Always run a verify-shaped check to avoid obvious timing/username enumeration.
    if user is None or not verify_password(password, user.hashed_password) or not user.is_active:
        raise AuthError("Invalid credentials")
    return user


def issue_tokens(user: User) -> tuple[str, str]:
    access = create_access_token(user.id, user.username, user.role, user.department)
    refresh = create_refresh_token(user.id, user.username, user.role, user.department)
    return access, refresh


def refresh_tokens(repo: UserRepository, refresh_token: str) -> tuple[str, str]:
    try:
        payload = decode_token(refresh_token, expected_type=REFRESH_TOKEN_TYPE)
    except InvalidTokenError as exc:
        raise AuthError("Invalid refresh token") from exc

    user = repo.get_by_id(str(payload["sub"]))
    if user is None or not user.is_active:
        raise AuthError("Invalid refresh token")
    return issue_tokens(user)
