"""Proposal persistence.

Proposals live in `proposals`; immutable version snapshots in
`proposal_versions`; comments in `proposal_comments`. Transitions use
compare-and-swap on (version, status) so lost updates are impossible (NN2).

Authorization is enforced inside the query (`list_for_user` builds an ACL
disjunction) and again via `can_access` as defense-in-depth (NN1).
"""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
from typing import Protocol

from pymongo import ReturnDocument
from pymongo.database import Database

from app.auth.rbac import can_access_proposal
from app.models.enums import ProposalStatus, Role
from app.models.proposal import Proposal
from app.models.proposal_snapshot import ProposalSnapshot
from app.models.review_comment import ReviewComment
from app.models.user import User

_OVERSIGHT_ROLES = frozenset({Role.APPROVER, Role.AUDITOR, Role.ADMIN})


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ProposalNotFound(Exception):
    pass


class ConcurrencyError(Exception):
    """Version/status no longer matches the expected value."""


class ProposalRepository(Protocol):
    def create(self, proposal: Proposal, snapshot: ProposalSnapshot) -> Proposal: ...
    def get_by_id(self, proposal_id: str) -> Proposal | None: ...
    def cas_transition(
        self,
        proposal_id: str,
        expected_version: int,
        expected_status: ProposalStatus,
        next_proposal: Proposal,
        snapshot: ProposalSnapshot,
    ) -> Proposal: ...
    def add_comment(self, comment: ReviewComment) -> ReviewComment: ...
    def list_for_user(self, user: User, status: ProposalStatus | None = None) -> list[Proposal]: ...
    def list_versions(self, proposal_id: str) -> list[ProposalSnapshot]: ...
    def list_comments(self, proposal_id: str) -> list[ReviewComment]: ...


class MongoProposalRepository:
    def __init__(self, db: Database) -> None:
        self._proposals = db["proposals"]
        self._versions = db["proposal_versions"]
        self._comments = db["proposal_comments"]

    def create(self, proposal: Proposal, snapshot: ProposalSnapshot) -> Proposal:
        self._proposals.insert_one(proposal.to_document())
        self._versions.insert_one(snapshot.to_document())
        return proposal

    def get_by_id(self, proposal_id: str) -> Proposal | None:
        doc = self._proposals.find_one({"_id": proposal_id})
        return Proposal.from_document(doc) if doc else None

    def cas_transition(
        self,
        proposal_id: str,
        expected_version: int,
        expected_status: ProposalStatus,
        next_proposal: Proposal,
        snapshot: ProposalSnapshot,
    ) -> Proposal:
        fields = [kv for kv in next_proposal.to_document().items() if kv[0] != "_id"]
        doc = self._proposals.find_one_and_update(
            {"_id": proposal_id, "version": expected_version, "status": expected_status.value},
            {"$set": dict(fields)},
            return_document=ReturnDocument.AFTER,
        )
        if doc is None:
            if self._proposals.find_one({"_id": proposal_id}) is None:
                raise ProposalNotFound(proposal_id)
            raise ConcurrencyError(f"proposal {proposal_id} changed concurrently")
        self._versions.insert_one(snapshot.to_document())
        return Proposal.from_document(doc)

    def add_comment(self, comment: ReviewComment) -> ReviewComment:
        self._comments.insert_one(comment.to_document())
        return comment

    @staticmethod
    def _acl_filter(user: User) -> dict:
        if user.role in _OVERSIGHT_ROLES:
            return {}
        return {
            "$or": [
                {"owner_id": user.id},
                {"owner_department": user.department},
                {"allowed_departments": user.department},
                {"allowed_user_ids": user.id},
            ]
        }

    def list_for_user(self, user: User, status: ProposalStatus | None = None) -> list[Proposal]:
        query = self._acl_filter(user)
        if status is not None:
            query = {**query, "status": status.value}
        docs = self._proposals.find(query).sort("updated_at", -1)
        return [p for p in (Proposal.from_document(d) for d in docs) if can_access_proposal(user, p)]

    def list_versions(self, proposal_id: str) -> list[ProposalSnapshot]:
        cursor = self._versions.find({"proposal_id": proposal_id}).sort("version", 1)
        return [ProposalSnapshot.from_document(doc) for doc in cursor]

    def list_comments(self, proposal_id: str) -> list[ReviewComment]:
        cursor = self._comments.find({"proposal_id": proposal_id}).sort("created_at", 1)
        return [ReviewComment.from_document(doc) for doc in cursor]


class InMemoryProposalRepository:
    """Test double. Proposals and snapshots are replaced, never mutated."""

    def __init__(self) -> None:
        self._proposals: dict[str, Proposal] = {}
        self._versions: list[ProposalSnapshot] = []
        self._comments: list[ReviewComment] = []

    def create(self, proposal: Proposal, snapshot: ProposalSnapshot) -> Proposal:
        self._proposals[proposal.id] = proposal
        self._versions.append(snapshot)
        return proposal

    def get_by_id(self, proposal_id: str) -> Proposal | None:
        return self._proposals.get(proposal_id)

    def cas_transition(
        self,
        proposal_id: str,
        expected_version: int,
        expected_status: ProposalStatus,
        next_proposal: Proposal,
        snapshot: ProposalSnapshot,
    ) -> Proposal:
        current = self._proposals.get(proposal_id)
        if current is None:
            raise ProposalNotFound(proposal_id)
        if current.version != expected_version or current.status != expected_status:
            raise ConcurrencyError(f"proposal {proposal_id} changed concurrently")
        self._proposals[proposal_id] = next_proposal
        self._versions.append(snapshot)
        return next_proposal

    def add_comment(self, comment: ReviewComment) -> ReviewComment:
        self._comments.append(comment)
        return comment

    def list_for_user(self, user: User, status: ProposalStatus | None = None) -> list[Proposal]:
        proposals = [
            p
            for p in self._proposals.values()
            if (status is None or p.status == status) and can_access_proposal(user, p)
        ]
        return sorted(proposals, key=lambda p: p.updated_at, reverse=True)

    def list_versions(self, proposal_id: str) -> list[ProposalSnapshot]:
        return [s for s in self._versions if s.proposal_id == proposal_id]

    def list_comments(self, proposal_id: str) -> list[ReviewComment]:
        return [c for c in self._comments if c.proposal_id == proposal_id]


__all__ = [
    "ConcurrencyError",
    "InMemoryProposalRepository",
    "MongoProposalRepository",
    "ProposalNotFound",
    "ProposalRepository",
]