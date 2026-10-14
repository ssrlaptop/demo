from __future__ import annotations

import uuid

import pytest

from app.audit.writer import InMemoryAuditWriter
from app.models.enums import ProposalStatus, Role
from app.models.user import User
from app.repositories.proposal_repo import InMemoryProposalRepository
from app.services import lifecycle

PAYLOAD = {
    "subject": "Body cameras pilot",
    "purpose": "Pilot body-worn cameras in Traffic",
    "resources": ["cameras", "docks"],
    "budget": [{"item": "cameras", "amount": 50000.0}],
    "policies": ["Policy 44"],
    "identifiers": {"ref": "TP-2026-1"},
}


def _user(role: Role, department: str, username: str | None = None) -> User:
    return User(
        id=uuid.uuid4().hex,
        username=username or f"{role.value}_{department.lower()}",
        email="u@example.gov",
        full_name="U",
        hashed_password="x",
        role=role,
        department=department,
    )


@pytest.fixture
def repo() -> InMemoryProposalRepository:
    return InMemoryProposalRepository()


@pytest.fixture
def audit() -> InMemoryAuditWriter:
    return InMemoryAuditWriter()


def _created(repo, audit, actor=None):
    actor = actor or _user(Role.OFFICER, "Traffic", "officer")
    return actor, lifecycle.create_proposal(actor, PAYLOAD, repo, audit)


def test_create_sets_owner_status_and_snapshot(repo, audit) -> None:
    actor, proposal = _created(repo, audit)
    assert proposal.status is ProposalStatus.CREATED
    assert proposal.version == 1
    assert proposal.owner_id == actor.id
    assert proposal.owner_department == "Traffic"
    assert proposal.budget[0].item == "cameras"
    assert len(repo.list_versions(proposal.id)) == 1
    assert len(audit.list_all()) == 1


def test_create_requires_subject_and_purpose(repo, audit) -> None:
    actor = _user(Role.OFFICER, "Traffic")
    with pytest.raises(ValueError):
        lifecycle.create_proposal(actor, {"subject": "", "purpose": ""}, repo, audit)


def test_submit_review_decide_approve_flow(repo, audit) -> None:
    officer, proposal = _created(repo, audit)
    reviewer = _user(Role.REVIEWER, "Traffic")
    approver = _user(Role.APPROVER, "HQ")

    proposal = lifecycle.submit_proposal(officer, proposal, repo, audit)
    assert proposal.status is ProposalStatus.SUBMITTED

    proposal = lifecycle.review_proposal(reviewer, proposal, "Looks good", repo, audit)
    assert proposal.status is ProposalStatus.REVIEWED

    proposal = lifecycle.decide_proposal(approver, proposal, "approved", "Approved", repo, audit)
    assert proposal.status is ProposalStatus.APPROVED
    decision = proposal.decisions[-1]
    assert decision.outcome == "approved"
    assert decision.version == proposal.version
    assert decision.snapshot_hash

    proposal = lifecycle.implement_proposal(officer, proposal, repo, audit)
    assert proposal.status is ProposalStatus.IMPLEMENTED

    proposal = lifecycle.close_proposal(approver, proposal, repo, audit)
    assert proposal.status is ProposalStatus.CLOSED

    assert len(repo.list_versions(proposal.id)) == 6  # create, submit, review, decide, implement, close
    assert {event.action for event in audit.list_all()} == {
        "create",
        "submit",
        "review",
        "decide",
        "implement",
        "close",
    }


def test_return_then_modify_bumps_version(repo, audit) -> None:
    officer, proposal = _created(repo, audit)
    reviewer = _user(Role.REVIEWER, "Traffic")

    proposal = lifecycle.submit_proposal(officer, proposal, repo, audit)
    proposal = lifecycle.return_proposal(reviewer, proposal, "Add budget detail", repo, audit)
    assert proposal.status is ProposalStatus.RETURNED

    proposal = lifecycle.modify_proposal(
        officer, proposal, {"subject": "Body cameras pilot v2", "reason": "addressed"}, repo, audit
    )
    assert proposal.status is ProposalStatus.MODIFIED
    assert proposal.version == 4  # create, submit, return, modify
    snapshot = repo.list_versions(proposal.id)[-1]
    assert "subject" in snapshot.changes
    assert proposal.subject == "Body cameras pilot v2"

    proposal = lifecycle.submit_proposal(officer, proposal, repo, audit)
    assert proposal.status is ProposalStatus.SUBMITTED


def test_reject_path(repo, audit) -> None:
    officer, proposal = _created(repo, audit)
    reviewer = _user(Role.REVIEWER, "Traffic")
    approver = _user(Role.APPROVER, "HQ")

    proposal = lifecycle.submit_proposal(officer, proposal, repo, audit)
    proposal = lifecycle.review_proposal(reviewer, proposal, "Review", repo, audit)
    proposal = lifecycle.decide_proposal(approver, proposal, "rejected", "Insufficient budget", repo, audit)
    assert proposal.status is ProposalStatus.REJECTED
    assert proposal.decisions[-1].outcome == "rejected"


def test_only_approver_can_decide(repo, audit) -> None:
    officer, proposal = _created(repo, audit)
    reviewer = _user(Role.REVIEWER, "Traffic")

    proposal = lifecycle.submit_proposal(officer, proposal, repo, audit)
    proposal = lifecycle.review_proposal(reviewer, proposal, "Review", repo, audit)
    with pytest.raises(lifecycle.NotAllowed):
        lifecycle.decide_proposal(officer, proposal, "approved", "self-approve", repo, audit)


def test_illegal_transition_decide_before_review(repo, audit) -> None:
    officer, proposal = _created(repo, audit)
    approver = _user(Role.APPROVER, "HQ")
    proposal = lifecycle.submit_proposal(officer, proposal, repo, audit)
    with pytest.raises(lifecycle.IllegalTransition):
        lifecycle.decide_proposal(approver, proposal, "approved", "too early", repo, audit)


def test_illegal_transition_modify_before_return(repo, audit) -> None:
    officer, proposal = _created(repo, audit)
    with pytest.raises(lifecycle.IllegalTransition):
        lifecycle.modify_proposal(officer, proposal, {"subject": "nope"}, repo, audit)


def test_cross_department_actor_is_denied(repo, audit) -> None:
    officer, proposal = _created(repo, audit)
    outsider = _user(Role.OFFICER, "CID")
    with pytest.raises(lifecycle.NotAllowed):
        lifecycle.submit_proposal(outsider, proposal, repo, audit)


def test_stale_write_is_rejected(repo, audit) -> None:
    officer, proposal = _created(repo, audit)
    stale = proposal
    lifecycle.submit_proposal(officer, proposal, repo, audit)
    with pytest.raises(lifecycle.IllegalTransition):
        lifecycle.submit_proposal(officer, stale, repo, audit)


def test_review_comment_is_recorded(repo, audit) -> None:
    officer, proposal = _created(repo, audit)
    reviewer = _user(Role.REVIEWER, "Traffic")
    proposal = lifecycle.submit_proposal(officer, proposal, repo, audit)
    lifecycle.review_proposal(reviewer, proposal, "Please clarify scope", repo, audit)
    comments = repo.list_comments(proposal.id)
    assert comments[-1].kind == "review"
    assert comments[-1].body == "Please clarify scope"