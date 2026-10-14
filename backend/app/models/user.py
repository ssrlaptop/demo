"""User domain model.

This is the storage-shaped representation. API-facing shapes live in app.schemas.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from app.models.enums import Role


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class User:
    id: str
    username: str
    email: str
    full_name: str
    hashed_password: str
    role: Role
    department: str
    is_active: bool = True
    created_at: datetime = field(default_factory=_utcnow)
    updated_at: datetime = field(default_factory=_utcnow)

    def to_document(self) -> dict:
        return {
            "_id": self.id,
            "username": self.username,
            "email": self.email,
            "full_name": self.full_name,
            "hashed_password": self.hashed_password,
            "role": self.role.value,
            "department": self.department,
            "is_active": self.is_active,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_document(cls, doc: dict) -> "User":
        return cls(
            id=str(doc["_id"]),
            username=doc["username"],
            email=doc["email"],
            full_name=doc["full_name"],
            hashed_password=doc["hashed_password"],
            role=Role(doc["role"]),
            department=doc["department"],
            is_active=doc.get("is_active", True),
            created_at=doc.get("created_at", _utcnow()),
            updated_at=doc.get("updated_at", _utcnow()),
        )
