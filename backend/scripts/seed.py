"""Seed demo users and proposals into MongoDB. Idempotent.

Usage:  python -m scripts.seed
"""

from __future__ import annotations

import uuid

from app.audit.writer import MongoAuditWriter
from app.core.security import hash_password
from app.db import get_db, try_ensure_indexes
from app.models.enums import Role
from app.models.user import User
from app.repositories.proposal_repo import MongoProposalRepository
from app.repositories.user_repo import MongoUserRepository
from app.services import lifecycle

DEMO_PASSWORD = "Passw0rd!23"

SEED_USERS: list[dict] = [
    {"username": "admin", "full_name": "Ada Admin", "role": Role.ADMIN, "department": "HQ"},
    {"username": "officer", "full_name": "Omar Officer", "role": Role.OFFICER, "department": "Traffic"},
    {"username": "reviewer", "full_name": "Rita Reviewer", "role": Role.REVIEWER, "department": "Traffic"},
    {"username": "approver", "full_name": "Aman Approver", "role": Role.APPROVER, "department": "HQ"},
    {"username": "auditor", "full_name": "Alia Auditor", "role": Role.AUDITOR, "department": "HQ"},
]


def seed_users() -> None:
    collection = get_db()["users"]
    hashed = hash_password(DEMO_PASSWORD)
    for spec in SEED_USERS:
        user = User(
            id=str(uuid.uuid4()),
            username=spec["username"],
            email=f"{spec['username']}@example.gov",
            full_name=spec["full_name"],
            hashed_password=hashed,
            role=spec["role"],
            department=spec["department"],
        )
        collection.update_one(
            {"username": user.username},
            {"$setOnInsert": user.to_document()},
            upsert=True,
        )
        print(f"seeded user {user.username} ({user.role.value}, {user.department})")


def _payload(subject: str, purpose: str, *, amount: float) -> dict:
    return {
        "subject": subject,
        "purpose": purpose,
        "resources": ["personnel", "equipment"],
        "budget": [{"item": "equipment", "amount": amount}],
        "policies": ["Policy 44"],
    }


def seed_proposals() -> None:
    db = get_db()
    if db["proposals"].count_documents({}) > 0:
        print("proposals already present — skipping demo proposals")
        return

    users = MongoUserRepository(db)
    officer = users.get_by_username("officer")
    reviewer = users.get_by_username("reviewer")
    approver = users.get_by_username("approver")
    if not (officer and reviewer and approver):
        print("missing seed users — run user seeding first")
        return

    repo = MongoProposalRepository(db)
    audit = MongoAuditWriter(db)

    lifecycle.create_proposal(
        officer,
        _payload("Body-worn camera pilot", "Equip Traffic patrol with body cameras", amount=50000),
        repo,
        audit,
    )
    print("seeded proposal: created")

    reviewed = lifecycle.create_proposal(
        officer,
        _payload("School-zone traffic calming", "Install calming measures near schools", amount=120000),
        repo,
        audit,
    )
    reviewed = lifecycle.submit_proposal(officer, reviewed, repo, audit)
    lifecycle.review_proposal(reviewer, reviewed, "Budget and scope look reasonable", repo, audit)
    print("seeded proposal: reviewed")

    approved = lifecycle.create_proposal(
        officer,
        _payload("Automated traffic signal upgrade", "Upgrade signals to adaptive control", amount=250000),
        repo,
        audit,
    )
    approved = lifecycle.submit_proposal(officer, approved, repo, audit)
    approved = lifecycle.review_proposal(reviewer, approved, "Meets policy and budget", repo, audit)
    approved = lifecycle.decide_proposal(approver, approved, "approved", "Approved for implementation", repo, audit)
    approved = lifecycle.implement_proposal(officer, approved, repo, audit)
    print("seeded proposal: implemented")


def seed() -> None:
    try_ensure_indexes()
    seed_users()
    seed_proposals()
    print(f"\nAll demo users use password: {DEMO_PASSWORD}")


if __name__ == "__main__":
    seed()
