"""Test configuration.

Sets a test environment BEFORE importing the app so no real MongoDB connection
is attempted, and swaps in an in-memory user repository.
"""

from __future__ import annotations

import os
import uuid

os.environ["ENVIRONMENT"] = "test"
os.environ["MONGODB_URI"] = "mongodb://localhost:27017"
os.environ["MONGODB_DB"] = "ipmprs_test"
os.environ["JWT_SECRET"] = "test-secret-key-0123456789abcdef"
os.environ["CORS_ORIGINS"] = "http://localhost:5173,http://127.0.0.1:5173"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.api.v1.deps import get_audit_writer, get_proposal_repo  # noqa: E402
from app.audit.writer import InMemoryAuditWriter  # noqa: E402
from app.auth.dependencies import get_user_repo  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.main import create_app  # noqa: E402
from app.models.enums import Role  # noqa: E402
from app.models.user import User  # noqa: E402
from app.repositories.proposal_repo import InMemoryProposalRepository  # noqa: E402
from app.repositories.user_repo import InMemoryUserRepository  # noqa: E402

DEMO_PASSWORD = "Passw0rd!23"

_USER_SPECS = [
    ("admin", Role.ADMIN, "HQ"),
    ("officer", Role.OFFICER, "Traffic"),
    ("officer_cid", Role.OFFICER, "CID"),
    ("reviewer", Role.REVIEWER, "Traffic"),
    ("approver", Role.APPROVER, "HQ"),
    ("auditor", Role.AUDITOR, "HQ"),
]


def _build_users() -> list[User]:
    hashed = hash_password(DEMO_PASSWORD)
    return [
        User(
            id=str(uuid.uuid4()),
            username=username,
            email=f"{username}@example.gov",
            full_name=username.title(),
            hashed_password=hashed,
            role=role,
            department=department,
        )
        for username, role, department in _USER_SPECS
    ]


@pytest.fixture
def repo() -> InMemoryUserRepository:
    return InMemoryUserRepository(_build_users())


@pytest.fixture
def proposal_repo() -> InMemoryProposalRepository:
    return InMemoryProposalRepository()


@pytest.fixture
def audit_writer() -> InMemoryAuditWriter:
    return InMemoryAuditWriter()


@pytest.fixture
def client(
    repo: InMemoryUserRepository,
    proposal_repo: InMemoryProposalRepository,
    audit_writer: InMemoryAuditWriter,
) -> TestClient:
    app = create_app()
    app.dependency_overrides[get_user_repo] = lambda: repo
    app.dependency_overrides[get_proposal_repo] = lambda: proposal_repo
    app.dependency_overrides[get_audit_writer] = lambda: audit_writer
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def login(client: TestClient):
    def _login(username: str, password: str = DEMO_PASSWORD) -> str:
        response = client.post("/api/v1/auth/login", json={"username": username, "password": password})
        assert response.status_code == 200, response.text
        return response.json()["access_token"]

    return _login
