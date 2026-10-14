"""User persistence.

The repository is an interface so services depend on behavior, not Mongo. Tests
use InMemoryUserRepository; production uses MongoUserRepository.
"""

from __future__ import annotations

from typing import Protocol

from app.models.enums import Role
from app.models.user import User


class UserRepository(Protocol):
    def get_by_username(self, username: str) -> User | None: ...
    def get_by_id(self, user_id: str) -> User | None: ...
    def create(self, user: User) -> User: ...
    def list_all(self) -> list[User]: ...


class MongoUserRepository:
    def __init__(self, db) -> None:  # noqa: ANN001 - pymongo Database
        self._collection = db["users"]

    def get_by_username(self, username: str) -> User | None:
        doc = self._collection.find_one({"username": username})
        return User.from_document(doc) if doc else None

    def get_by_id(self, user_id: str) -> User | None:
        doc = self._collection.find_one({"_id": user_id})
        return User.from_document(doc) if doc else None

    def create(self, user: User) -> User:
        self._collection.insert_one(user.to_document())
        return user

    def list_all(self) -> list[User]:
        return [User.from_document(doc) for doc in self._collection.find({})]


class InMemoryUserRepository:
    """Test double. Stores immutable copies keyed by id and username."""

    def __init__(self, users: list[User] | None = None) -> None:
        self._by_id: dict[str, User] = {}
        self._by_username: dict[str, User] = {}
        for user in users or []:
            self.create(user)

    def get_by_username(self, username: str) -> User | None:
        return self._by_username.get(username)

    def get_by_id(self, user_id: str) -> User | None:
        return self._by_id.get(user_id)

    def create(self, user: User) -> User:
        self._by_id[user.id] = user
        self._by_username[user.username] = user
        return user

    def list_all(self) -> list[User]:
        return list(self._by_id.values())


__all__ = ["InMemoryUserRepository", "MongoUserRepository", "UserRepository"]
