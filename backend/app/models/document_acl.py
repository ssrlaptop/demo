"""Document access-control entry.

Authorization is modelled separately from classification (see Classification in
app.models.enums). A document's sensitivity label does not by itself grant access;
these ACL fields decide it.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.models.enums import Classification


@dataclass(frozen=True)
class DocumentAcl:
    document_id: str
    owner_id: str
    owner_department: str
    classification: Classification
    allowed_user_ids: frozenset[str] = field(default_factory=frozenset)
    allowed_departments: frozenset[str] = field(default_factory=frozenset)

    def to_document(self) -> dict:
        return {
            "document_id": self.document_id,
            "owner_id": self.owner_id,
            "owner_department": self.owner_department,
            "classification": self.classification.value,
            "allowed_user_ids": sorted(self.allowed_user_ids),
            "allowed_departments": sorted(self.allowed_departments),
        }

    @classmethod
    def from_document(cls, doc: dict) -> "DocumentAcl":
        return cls(
            document_id=doc["document_id"],
            owner_id=doc["owner_id"],
            owner_department=doc["owner_department"],
            classification=Classification(doc["classification"]),
            allowed_user_ids=frozenset(doc.get("allowed_user_ids", [])),
            allowed_departments=frozenset(doc.get("allowed_departments", [])),
        )
