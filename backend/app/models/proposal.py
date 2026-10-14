"""Proposal domain model and related value objects.

Immutable storage-shaped representation (see app.models.user for convention).
Authorization fields (owner/department/ACL) are separate from classification
per NN1; classification is a handling label only.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timezone

from app.models.enums import Classification, ProposalStatus


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _as_date(value: object) -> date | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    raise TypeError(f"expected date, got {type(value).__name__}")


@dataclass(frozen=True)
class BudgetItem:
    item: str
    amount: float

    def to_document(self) -> dict:
        return {"item": self.item, "amount": self.amount}

    @classmethod
    def from_document(cls, doc: dict) -> "BudgetItem":
        return cls(item=str(doc["item"]), amount=float(doc["amount"]))


@dataclass(frozen=True)
class Decision:
    """A final disposition, pinned to an exact proposal version (NN2)."""

    outcome: str  # approved | rejected
    version: int
    reason: str
    decided_by: str
    decided_at: datetime
    snapshot_hash: str

    def to_document(self) -> dict:
        return {
            "outcome": self.outcome,
            "version": self.version,
            "reason": self.reason,
            "decided_by": self.decided_by,
            "decided_at": self.decided_at,
            "snapshot_hash": self.snapshot_hash,
        }

    @classmethod
    def from_document(cls, doc: dict) -> "Decision":
        return cls(
            outcome=doc["outcome"],
            version=int(doc["version"]),
            reason=doc.get("reason", ""),
            decided_by=doc.get("decided_by", ""),
            decided_at=doc.get("decided_at", _utcnow()),
            snapshot_hash=doc.get("snapshot_hash", ""),
        )


@dataclass(frozen=True)
class Proposal:
    id: str
    subject: str
    purpose: str
    department: str
    status: ProposalStatus = ProposalStatus.CREATED
    version: int = 1
    resources: tuple[str, ...] = field(default_factory=tuple)
    budget: tuple[BudgetItem, ...] = field(default_factory=tuple)
    policies: tuple[str, ...] = field(default_factory=tuple)
    identifiers: dict[str, str] = field(default_factory=dict)
    responsible_officers: tuple[str, ...] = field(default_factory=tuple)
    start_date: date | None = None
    end_date: date | None = None
    decisions: tuple[Decision, ...] = field(default_factory=tuple)
    classification: Classification = Classification.INTERNAL
    owner_id: str = ""
    owner_department: str = ""
    allowed_user_ids: frozenset[str] = field(default_factory=frozenset)
    allowed_departments: frozenset[str] = field(default_factory=frozenset)
    created_by: str = ""
    created_at: datetime = field(default_factory=_utcnow)
    updated_at: datetime = field(default_factory=_utcnow)

    def to_document(self, *, canonical: bool = False) -> dict:
        doc: dict = {
            "_id": self.id,
            "subject": self.subject,
            "purpose": self.purpose,
            "department": self.department,
            "status": self.status.value,
            "version": self.version,
            "resources": list(self.resources),
            "budget": [item.to_document() for item in self.budget],
            "policies": list(self.policies),
            "identifiers": dict(self.identifiers),
            "responsible_officers": list(self.responsible_officers),
            "classification": self.classification.value,
            "owner_id": self.owner_id,
            "owner_department": self.owner_department,
            "allowed_user_ids": sorted(self.allowed_user_ids),
            "allowed_departments": sorted(self.allowed_departments),
            "created_by": self.created_by,
        }
        if canonical:
            doc["start_date"] = self.start_date.isoformat() if self.start_date else None
            doc["end_date"] = self.end_date.isoformat() if self.end_date else None
            doc["decisions"] = [
                {
                    **decision.to_document(),
                    "decided_at": decision.decided_at.isoformat(),
                }
                for decision in self.decisions
            ]
            doc["created_at"] = self.created_at.isoformat()
            doc["updated_at"] = self.updated_at.isoformat()
        else:
            doc["start_date"] = self.start_date
            doc["end_date"] = self.end_date
            doc["decisions"] = [decision.to_document() for decision in self.decisions]
            doc["created_at"] = self.created_at
            doc["updated_at"] = self.updated_at
        return doc

    @classmethod
    def from_document(cls, doc: dict) -> "Proposal":
        return cls(
            id=str(doc["_id"]),
            subject=doc["subject"],
            purpose=doc["purpose"],
            department=doc["department"],
            status=ProposalStatus(doc["status"]),
            version=int(doc.get("version", 1)),
            resources=tuple(doc.get("resources", [])),
            budget=tuple(BudgetItem.from_document(item) for item in doc.get("budget", [])),
            policies=tuple(doc.get("policies", [])),
            identifiers=dict(doc.get("identifiers", {})),
            responsible_officers=tuple(doc.get("responsible_officers", [])),
            start_date=_as_date(doc.get("start_date")),
            end_date=_as_date(doc.get("end_date")),
            decisions=tuple(Decision.from_document(item) for item in doc.get("decisions", [])),
            classification=Classification(doc["classification"]),
            owner_id=doc.get("owner_id", ""),
            owner_department=doc.get("owner_department", ""),
            allowed_user_ids=frozenset(doc.get("allowed_user_ids", [])),
            allowed_departments=frozenset(doc.get("allowed_departments", [])),
            created_by=doc.get("created_by", ""),
            created_at=doc.get("created_at", _utcnow()),
            updated_at=doc.get("updated_at", _utcnow()),
        )