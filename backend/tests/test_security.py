from __future__ import annotations

import pytest

from app.core.security import (
    ACCESS_TOKEN_TYPE,
    InvalidTokenError,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.enums import Role


def test_password_hash_roundtrip() -> None:
    hashed = hash_password("Passw0rd!23")
    assert hashed != "Passw0rd!23"
    assert verify_password("Passw0rd!23", hashed) is True
    assert verify_password("wrong-password", hashed) is False


def test_access_token_roundtrip() -> None:
    token = create_access_token("uid-1", "officer", Role.OFFICER, "Traffic")
    payload = decode_token(token, expected_type=ACCESS_TOKEN_TYPE)
    assert payload["sub"] == "uid-1"
    assert payload["role"] == "officer"
    assert payload["department"] == "Traffic"


def test_token_type_is_enforced() -> None:
    refresh = create_refresh_token("uid-1", "officer", Role.OFFICER, "Traffic")
    with pytest.raises(InvalidTokenError):
        decode_token(refresh, expected_type=ACCESS_TOKEN_TYPE)


def test_tampered_token_rejected() -> None:
    token = create_access_token("uid-1", "officer", Role.OFFICER, "Traffic")
    with pytest.raises(InvalidTokenError):
        decode_token(token + "x", expected_type=ACCESS_TOKEN_TYPE)
