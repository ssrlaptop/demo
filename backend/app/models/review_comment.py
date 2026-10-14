"""Review/clarification/decision comments attached to a proposal version.

Comment bodies are NOT written to the audit trail (NN3: audit events contain no
sensitive document content); the audit records that a comment/action happened,
never its text.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone

COMMENT_KINDS = ("review", "clarification", "decision", "note")


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class ReviewComment:
    id: str
    proposal_id: str
    version: int
    author_id: str
    author_username: str
    kind: str
    body: str
    created_at: datetime = field(default_factory=_utcnow)

    def to_document(self) -> dict:
        return {
            "_id": self.id,
            "proposal_id": self.proposal_id,
            "version": self.version,
            "author_id": self.author_id,
            "author_username": self.author_username,
            "kind": self.kind,
            "body": self.body,
            "created_at": self.created_at,
        }

    @classmethod
    def from_document(cls, doc: dict) -> "ReviewComment":
        assert doc.get("kind") in COMMENT_KINDS, f"unknown comment kind: {doc.get('kind')}"
        return cls(
            id=str(doc["_id"]),
            proposal_id=doc["proposal_id"],
            version=int(doc.get("version", 1)),
            author_id=doc.get("author_id", ""),
            author_username=doc.get("author_username", ""),
            kind=doc["kind"],
            body=doc.get("body", ""),
            created_at=doc.get("created_at", _utcnow()),
        )