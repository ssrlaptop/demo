"""Append-only audit event (NN3).

The event carries only the fact of an operation plus integrity links; never the
content of proposals or documents.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class AuditEvent:
    actor_id: str
    actor_username: str
    action: str
    entity_type: str
    entity_id: str
    summary: str
    proposal_version: int | None = None
    content_hash: str | None = None  # pins decision to a snapshot (NN2)
    outcome: str | None = None
    prev_hash: str | None = None
    event_hash: str = ""
    seq: int = 0
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    created_at: datetime = field(default_factory=_utcnow)

    def to_document(self) -> dict:
        return {
            "_id": self.id,
            "seq": self.seq,
            "actor_id": self.actor_id,
            "actor_username": self.actor_username,
            "action": self.action,
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "proposal_version": self.proposal_version,
            "content_hash": self.content_hash,
            "outcome": self.outcome,
            "summary": self.summary,
            "prev_hash": self.prev_hash,
            "event_hash": self.event_hash,
            "created_at": self.created_at,
        }

    @classmethod
    def from_document(cls, doc: dict) -> "AuditEvent":
        return cls(
            id=str(doc["_id"]),
            seq=int(doc.get("seq", 0)),
            actor_id=doc.get("actor_id", ""),
            actor_username=doc.get("actor_username", ""),
            action=doc.get("action", ""),
            entity_type=doc.get("entity_type", ""),
            entity_id=doc.get("entity_id", ""),
            proposal_version=doc.get("proposal_version"),
            content_hash=doc.get("content_hash"),
            outcome=doc.get("outcome"),
            summary=doc.get("summary", ""),
            prev_hash=doc.get("prev_hash"),
            event_hash=doc.get("event_hash", ""),
            created_at=doc.get("created_at", _utcnow()),
        )