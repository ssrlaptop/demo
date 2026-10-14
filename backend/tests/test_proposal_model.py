from __future__ import annotations

from datetime import date

from app.models.enums import Classification, ProposalStatus
from app.models.proposal import BudgetItem, Proposal


def _proposal(**overrides) -> Proposal:
    base = {
        "id": "p1",
        "subject": "Body cameras pilot",
        "purpose": "Pilot body-worn cameras in Traffic",
        "department": "Traffic",
        "resources": ("cameras", "docks"),
        "budget": (BudgetItem("cameras", 50000.0),),
        "policies": ("Policy 44",),
        "identifiers": {"ref": "TP-2026-1"},
        "responsible_officers": ("officer",),
        "start_date": date(2026, 1, 1),
        "end_date": date(2026, 6, 30),
        "classification": Classification.RESTRICTED,
        "owner_id": "u1",
        "owner_department": "Traffic",
        "created_by": "officer",
    }
    base.update(overrides)
    return Proposal(**base)


def test_defaults_are_created_v1() -> None:
    proposal = Proposal(id="p2", subject="S", purpose="P", department="Traffic")
    assert proposal.status is ProposalStatus.CREATED
    assert proposal.version == 1


def test_document_roundtrip_preserves_values() -> None:
    original = _proposal()
    restored = Proposal.from_document(original.to_document())
    assert restored == original


def test_canonical_document_is_deterministic() -> None:
    proposal = _proposal()
    assert proposal.to_document(canonical=True) == proposal.to_document(canonical=True)


def test_canonical_document_serializes_dates_as_iso() -> None:
    doc = _proposal().to_document(canonical=True)
    assert doc["status"] == "created"
    assert isinstance(doc["created_at"], str)
    assert doc["start_date"] == "2026-01-01"


def test_budget_item_roundtrip() -> None:
    item = BudgetItem("radios", 1200.5)
    assert BudgetItem.from_document(item.to_document()) == item