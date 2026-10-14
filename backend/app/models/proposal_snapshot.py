"""Immutable proposal version snapshot (NN2: history never overwritten).

Each lifecycle transition stores a full canonical snapshot; decisions pin to the
exact snapshot via content_hash.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone

from app.models.proposal import Proposal


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class ProposalSnapshot:
    id: str
    proposal_id: str
    version: int
    snapshot: dict
    content_hash: str
    changes: tuple[str, ...]
    actor_id: str
    actor_username: str
    action: str
    reason: str
    created_at: datetime = field(default_factory=_utcnow)

    @classmethod
    def build(
        cls,
        proposal: Proposal,
        *,
        actor_id: str,
        actor_username: str,
        action: str,
        reason: str,
        changes: tuple[str, ...] = (),
        snapshot_id: str | None = None,
    ) -> "ProposalSnapshot":
        """Create a snapshot from a proposal's canonical representation."""
        canonical = proposal.to_document(canonical=True)
        from app.audit.hash_chain import sha256_hex

        return cls(
            id=snapshot_id or uuid.uuid4().hex,
            proposal_id=proposal.id,
            version=proposal.version,
            snapshot=canonical,
            content_hash=sha256_hex(canonical),
            changes=changes,
            actor_id=actor_id,
            actor_username=actor_username,
            action=action,
            reason=reason,
        )

    def to_document(self) -> dict:
        return {
            "_id": self.id,
            "proposal_id": self.proposal_id,
            "version": self.version,
            "snapshot": self.snapshot,
            "content_hash": self.content_hash,
            "changes": list(self.changes),
            "actor_id": self.actor_id,
            "actor_username": self.actor_username,
            "action": self.action,
            "reason": self.reason,
            "created_at": self.created_at,
        }

    @classmethod
    def from_document(cls, doc: dict) -> "ProposalSnapshot":
        return cls(
            id=str(doc["_id"]),
            proposal_id=doc["proposal_id"],
            version=int(doc["version"]),
            snapshot=dict(doc.get("snapshot", {})),
            content_hash=doc.get("content_hash", ""),
            changes=tuple(doc.get("changes", [])),
            actor_id=doc.get("actor_id", ""),
            actor_username=doc.get("actor_username", ""),
            action=doc.get("action", ""),
            reason=doc.get("reason", ""),
            created_at=doc.get("created_at", _utcnow()),
        )