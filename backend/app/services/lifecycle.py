"""Proposal lifecycle state machine (P2.2, NN1/NN2).

Valid transitions:

    CREATED -> SUBMITTED            (submit; owner-department officer/reviewer)
    MODIFIED -> SUBMITTED           (resubmit)
    SUBMITTED -> REVIEWED           (review; reviewer/approver)
    SUBMITTED -> RETURNED           (return for changes; reviewer/approver)
    REVIEWED -> RETURNED            (return after review; approver)
    REVIEWED -> APPROVED|REJECTED   (decide; APPROVER ONLY finalization)
    RETURNED -> MODIFIED            (modify; owner-department officer/reviewer)
    APPROVED -> IMPLEMENTED         (implement; officer/reviewer)
    IMPLEMENTED -> CLOSED           (close; approver/admin)

Every transition persists BOTH a CAS-updated proposal AND an immutable version
snapshot, and appends a sanitized audit event pinned to the version snapshot.
"""

from __future__ import annotations

import uuid
from dataclasses import replace
from datetime import datetime, timezone
from typing import Any

from app.audit.hash_chain import sha256_hex
from app.audit.writer import AuditWriter
from app.auth.rbac import can_access_proposal
from app.models.audit_event import AuditEvent
from app.models.enums import Classification, ProposalStatus, Role
from app.models.proposal import BudgetItem, Decision, Proposal
from app.models.proposal_snapshot import ProposalSnapshot
from app.models.review_comment import ReviewComment
from app.models.user import User
from app.repositories.proposal_repo import (
    ProposalNotFound,
    ProposalRepository,
)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class LifecycleError(Exception):
    pass


class NotAllowed(LifecycleError):
    pass


class IllegalTransition(LifecycleError):
    pass


ROLES_SUBMIT = frozenset({Role.OFFICER, Role.REVIEWER})
ROLES_REVIEW = frozenset({Role.REVIEWER, Role.APPROVER})
ROLES_RETURN = frozenset({Role.REVIEWER, Role.APPROVER})
ROLES_DECIDE = frozenset({Role.APPROVER})
ROLES_MODIFY = frozenset({Role.OFFICER, Role.REVIEWER})
ROLES_IMPLEMENT = frozenset({Role.OFFICER, Role.REVIEWER})
ROLES_CLOSE = frozenset({Role.APPROVER, Role.ADMIN})

_VALID_FIELDS = frozenset(
    {
        "subject",
        "purpose",
        "resources",
        "budget",
        "policies",
        "identifiers",
        "responsible_officers",
        "start_date",
        "end_date",
    }
)


def _as_budget_items(items: Any) -> tuple[BudgetItem, ...]:
    result: list[BudgetItem] = []
    for item in items or []:
        if isinstance(item, BudgetItem):
            result.append(item)
        elif isinstance(item, dict):
            result.append(BudgetItem(item=str(item["item"]), amount=float(item["amount"])))
        else:
            raise ValueError("invalid budget item")
    return tuple(result)


def _require_role(actor: User, roles: frozenset[Role], action: str) -> None:
    if actor.role not in roles:
        raise NotAllowed(f"role {actor.role.value} cannot {action}")


def _require_access(actor: User, proposal: Proposal) -> None:
    if not can_access_proposal(actor, proposal):
        raise NotAllowed("not authorized for this proposal")


def _make_comment(actor: User, proposal: Proposal, kind: str, body: str) -> ReviewComment:
    return ReviewComment(
        id=uuid.uuid4().hex,
        proposal_id=proposal.id,
        version=proposal.version,
        author_id=actor.id,
        author_username=actor.username,
        kind=kind,
        body=body,
    )


def _audit_event(
    actor: User,
    proposal: Proposal,
    action: str,
    snapshot: ProposalSnapshot,
    *,
    outcome: str | None = None,
) -> AuditEvent:
    return AuditEvent(
        actor_id=actor.id,
        actor_username=actor.username,
        action=action,
        entity_type="proposal",
        entity_id=proposal.id,
        proposal_version=snapshot.version,
        content_hash=snapshot.content_hash,
        outcome=outcome,
        summary=f"proposal.{action} v{snapshot.version}",
    )


def _snapshot_for(
    proposal: Proposal,
    actor: User,
    action: str,
    reason: str,
    previous: ProposalSnapshot | None,
) -> ProposalSnapshot:
    changes = _snapshot_changes(proposal, previous) if action == "modify" else ()
    return ProposalSnapshot.build(
        proposal,
        actor_id=actor.id,
        actor_username=actor.username,
        action=action,
        reason=reason,
        changes=changes,
    )


def _snapshot_changes(proposal: Proposal, previous: ProposalSnapshot | None) -> tuple[str, ...]:
    current = proposal.to_document(canonical=True)
    ignored = {"_id", "created_at", "updated_at", "version", "status"}
    if previous is None:
        return tuple(sorted(set(current) - ignored))
    changed = {
        key
        for key in set(current) | set(previous.snapshot)
        if key not in ignored and current.get(key) != previous.snapshot.get(key)
    }
    return tuple(sorted(changed))


def _apply_patch(proposal: Proposal, patch: dict[str, Any]) -> Proposal:
    # None means "not provided" (Pydantic model_dump emits unset optionals).
    allowed = {k: v for k, v in patch.items() if k in _VALID_FIELDS and v is not None}
    replacements: dict[str, Any] = {}

    if "subject" in allowed:
        replacements["subject"] = str(allowed["subject"]).strip()
    if "purpose" in allowed:
        replacements["purpose"] = str(allowed["purpose"]).strip()
    if "resources" in allowed:
        replacements["resources"] = tuple(allowed["resources"])
    if "budget" in allowed:
        replacements["budget"] = _as_budget_items(allowed["budget"])
    if "policies" in allowed:
        replacements["policies"] = tuple(allowed["policies"])
    if "identifiers" in allowed:
        replacements["identifiers"] = dict(allowed["identifiers"])
    if "responsible_officers" in allowed:
        replacements["responsible_officers"] = tuple(allowed["responsible_officers"])
    if "start_date" in allowed:
        replacements["start_date"] = allowed["start_date"]
    if "end_date" in allowed:
        replacements["end_date"] = allowed["end_date"]

    return replace(proposal, **replacements)


def _transition(
    actor: User,
    proposal: Proposal,
    action: str,
    target: ProposalStatus,
    repo: ProposalRepository,
    audit: AuditWriter,
    *,
    reason: str = "",
    patch: dict[str, Any] | None = None,
    decision: Decision | None = None,
    comment: ReviewComment | None = None,
    outcome: str | None = None,
) -> Proposal:
    _require_access(actor, proposal)

    versions = repo.list_versions(proposal.id)
    previous = versions[-1] if versions else None

    next_proposal = _advance(proposal, action, target, patch, decision)
    snapshot = _snapshot_for(next_proposal, actor, action, reason, previous)

    try:
        result = repo.cas_transition(
            proposal.id, proposal.version, proposal.status, next_proposal, snapshot
        )
    except ProposalNotFound:
        raise
    except Exception:
        raise IllegalTransition(f"proposal {proposal.id} changed concurrently") from None

    if comment is not None:
        repo.add_comment(comment)
    audit.append(_audit_event(actor, result, action, snapshot, outcome=outcome))
    return result


def _advance(
    proposal: Proposal,
    action: str,
    target: ProposalStatus,
    patch: dict[str, Any] | None,
    decision: Decision | None,
) -> Proposal:
    updated = _apply_patch(proposal, patch) if patch else proposal

    fields: dict[str, Any] = {"status": target, "version": updated.version + 1}
    if decision is not None:
        fields["decisions"] = updated.decisions + (decision,)
    return replace(updated, **fields)


def create_proposal(
    actor: User, payload: dict[str, Any], repo: ProposalRepository, audit: AuditWriter
) -> Proposal:
    subject = str(payload.get("subject", "")).strip()
    purpose = str(payload.get("purpose", "")).strip()
    if not subject or not purpose:
        raise ValueError("subject and purpose are required")

    department = str(payload.get("department") or actor.department)
    now = _utcnow()
    proposal = Proposal(
        id=uuid.uuid4().hex,
        subject=subject,
        purpose=purpose,
        department=department,
        resources=tuple(payload.get("resources") or []),
        budget=_as_budget_items(payload.get("budget")),
        policies=tuple(payload.get("policies") or []),
        identifiers=dict(payload.get("identifiers") or {}),
        responsible_officers=tuple(payload.get("responsible_officers") or []),
        start_date=payload.get("start_date"),
        end_date=payload.get("end_date"),
        classification=Classification(payload.get("classification") or Classification.INTERNAL),
        owner_id=actor.id,
        owner_department=department,
        allowed_user_ids=frozenset(payload.get("allowed_user_ids") or []),
        allowed_departments=frozenset(payload.get("allowed_departments") or []),
        created_by=actor.username,
        created_at=now,
        updated_at=now,
    )

    snapshot = _snapshot_for(proposal, actor, "create", payload.get("reason", ""), None)
    repo.create(proposal, snapshot)
    audit.append(_audit_event(actor, proposal, "create", snapshot))
    return proposal


def submit_proposal(
    actor: User, proposal: Proposal, repo: ProposalRepository, audit: AuditWriter
) -> Proposal:
    _require_role(actor, ROLES_SUBMIT, "submit")
    return _transition(actor, proposal, "submit", ProposalStatus.SUBMITTED, repo, audit)


def review_proposal(
    actor: User, proposal: Proposal, comment: str, repo: ProposalRepository, audit: AuditWriter
) -> Proposal:
    _require_role(actor, ROLES_REVIEW, "review")
    note = _make_comment(actor, proposal, "review", comment)
    return _transition(
        actor,
        proposal,
        "review",
        ProposalStatus.REVIEWED,
        repo,
        audit,
        reason=comment,
        comment=note,
    )


def return_proposal(
    actor: User, proposal: Proposal, reason: str, repo: ProposalRepository, audit: AuditWriter
) -> Proposal:
    _require_role(actor, ROLES_RETURN, "return")
    if proposal.status not in {ProposalStatus.SUBMITTED, ProposalStatus.REVIEWED}:
        raise IllegalTransition(f"cannot return a {proposal.status.value} proposal")
    if proposal.status == ProposalStatus.REVIEWED:
        _require_role(actor, ROLES_DECIDE, "return a reviewed proposal")
    note = _make_comment(actor, proposal, "clarification", reason)
    return _transition(
        actor,
        proposal,
        "return",
        ProposalStatus.RETURNED,
        repo,
        audit,
        reason=reason,
        comment=note,
    )


def _decision_hash(proposal: Proposal, target: ProposalStatus, version: int) -> str:
    """Hash of the proposal content at the decided moment, excluding the
    decision itself, so the pin is well-defined (no self-reference)."""
    doc = replace(proposal, status=target, decisions=(), version=version).to_document(canonical=True)
    doc.pop("decisions", None)
    return sha256_hex(doc)


def decide_proposal(
    actor: User,
    proposal: Proposal,
    decision: str,  # "approved" | "rejected"
    reason: str,
    repo: ProposalRepository,
    audit: AuditWriter,
) -> Proposal:
    _require_role(actor, ROLES_DECIDE, "decide")
    if decision not in {"approved", "rejected"}:
        raise ValueError("decision must be 'approved' or 'rejected'")
    if proposal.status != ProposalStatus.REVIEWED:
        raise IllegalTransition(f"cannot decide a {proposal.status.value} proposal")

    target = ProposalStatus.APPROVED if decision == "approved" else ProposalStatus.REJECTED
    decided_version = proposal.version + 1
    detail = Decision(
        outcome=decision,
        version=decided_version,
        reason=reason,
        decided_by=actor.username,
        decided_at=_utcnow(),
        snapshot_hash=_decision_hash(proposal, target, decided_version),
    )
    note = _make_comment(actor, proposal, "decision", reason)
    return _transition(
        actor,
        proposal,
        "decide",
        target,
        repo,
        audit,
        reason=reason,
        decision=detail,
        comment=note,
        outcome=decision,
    )


def modify_proposal(
    actor: User,
    proposal: Proposal,
    patch: dict[str, Any],
    repo: ProposalRepository,
    audit: AuditWriter,
) -> Proposal:
    _require_role(actor, ROLES_MODIFY, "modify")
    if proposal.status != ProposalStatus.RETURNED:
        raise IllegalTransition(f"cannot modify a {proposal.status.value} proposal")
    reason = str(patch.pop("reason", ""))
    return _transition(
        actor,
        proposal,
        "modify",
        ProposalStatus.MODIFIED,
        repo,
        audit,
        reason=reason,
        patch=patch,
    )


def implement_proposal(
    actor: User, proposal: Proposal, repo: ProposalRepository, audit: AuditWriter
) -> Proposal:
    _require_role(actor, ROLES_IMPLEMENT, "implement")
    return _transition(actor, proposal, "implement", ProposalStatus.IMPLEMENTED, repo, audit)


def close_proposal(
    actor: User, proposal: Proposal, repo: ProposalRepository, audit: AuditWriter
) -> Proposal:
    _require_role(actor, ROLES_CLOSE, "close")
    return _transition(actor, proposal, "close", ProposalStatus.CLOSED, repo, audit)


__all__ = [
    "IllegalTransition",
    "LifecycleError",
    "NotAllowed",
    "close_proposal",
    "create_proposal",
    "decide_proposal",
    "implement_proposal",
    "modify_proposal",
    "return_proposal",
    "review_proposal",
    "submit_proposal",
]