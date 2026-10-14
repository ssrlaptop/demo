"""Auth request/response schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.models.enums import Role


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=64)
    password: str = Field(..., min_length=8, max_length=256)


class RefreshRequest(BaseModel):
    refresh_token: str = Field(..., min_length=10)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    id: str
    username: str
    email: str
    full_name: str
    role: Role
    department: str
    is_active: bool
