"""Password hashing and JWT helpers.

Passwords are hashed with Argon2id. Tokens are signed JWTs carrying the subject
(user id), role, and department so that authorization can be enforced server-side
without trusting client-supplied claims.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from app.core.config import get_settings
from app.models.enums import Role

_password_hasher = PasswordHasher()

ACCESS_TOKEN_TYPE = "access"
REFRESH_TOKEN_TYPE = "refresh"


class InvalidTokenError(Exception):
    """Raised when a token is missing, malformed, expired, or has the wrong type."""


def hash_password(plain_password: str) -> str:
    return _password_hasher.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return _password_hasher.verify(hashed_password, plain_password)
    except VerifyMismatchError:
        return False
    except Exception:
        return False


def _create_token(
    user_id: str,
    username: str,
    role: Role,
    department: str,
    token_type: str,
    expires_delta: timedelta,
) -> str:
    settings = get_settings()
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "username": username,
        "role": role.value,
        "department": department,
        "type": token_type,
        "iat": int(now.timestamp()),
        "exp": int((now + expires_delta).timestamp()),
        "jti": uuid.uuid4().hex,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def create_access_token(user_id: str, username: str, role: Role, department: str) -> str:
    settings = get_settings()
    return _create_token(
        user_id,
        username,
        role,
        department,
        ACCESS_TOKEN_TYPE,
        timedelta(minutes=settings.access_token_expire_minutes),
    )


def create_refresh_token(user_id: str, username: str, role: Role, department: str) -> str:
    settings = get_settings()
    return _create_token(
        user_id,
        username,
        role,
        department,
        REFRESH_TOKEN_TYPE,
        timedelta(days=settings.refresh_token_expire_days),
    )


def decode_token(token: str, expected_type: str) -> dict:
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except jwt.PyJWTError as exc:  # expired, bad signature, malformed
        raise InvalidTokenError("Invalid or expired token") from exc

    if payload.get("type") != expected_type:
        raise InvalidTokenError("Unexpected token type")
    if not payload.get("sub"):
        raise InvalidTokenError("Token missing subject")
    return payload
