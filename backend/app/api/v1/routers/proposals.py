"""Proposal lifecycle endpoints (Phase 2).

Authorization pattern: every action requires (1) the role permission via
require_permission, and (2) can_access on the proposal itself (deny-by-default).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.v1.deps import get_audit_writer, get_proposal_repo
from app.audit.writer import AuditWriter
from app.auth.dependencies import require_permission
from app.auth.rbac import can_access_proposal
from app.models.enums import Permission, ProposalStatus
from app.models.proposal import Proposal as ProposalModel
from app.models.user import User
from app.repositories.proposal_repo import ProposalNotFound, ProposalRepository
from app.schemas.proposal import (
    CommentOut,
    DecideRequest,
    ProposalCreate,
    ProposalOut,
    ProposalUpdate,
    ReturnRequest,
    ReviewRequest,
    TimelineEntryOut,
    VersionOut,
)
from app.services import lifecycle

router = APIRouter(prefix="/proposals", tags=["proposals"])


def _get_accessible(proposal_id: str, user: User, repo: ProposalRepository) -> ProposalModel:
    proposal = repo.get_by_id(proposal_id)
    if proposal is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Proposal not found")
    if not can_access_proposal(user, proposal):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")
    return proposal


def _handle(exc: Exception) -> HTTPException:
    from app.services.lifecycle import IllegalTransition, NotAllowed

    if isinstance(exc, HTTPException):
        return exc
    if isinstance(exc, NotAllowed):
        return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed")
    if isinstance(exc, IllegalTransition):
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    if isinstance(exc, ProposalNotFound):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Proposal not found")
    if isinstance(exc, ValueError):
        return HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    return HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.post("", response_model=ProposalOut, status_code=status.HTTP_201_CREATED)
def create_proposal(
    payload: ProposalCreate,
    user: User = Depends(require_permission(Permission.PROPOSAL_CREATE)),
    repo: ProposalRepository = Depends(get_proposal_repo),
    audit: AuditWriter = Depends(get_audit_writer),
) -> ProposalOut:
    try:
        proposal = lifecycle.create_proposal(user, payload.model_dump(), repo, audit)
    except Exception as exc:  # noqa: BLE001
        raise _handle(exc) from exc
    return ProposalOut.from_proposal(proposal)


@router.get("", response_model=list[ProposalOut])
def list_proposals(
    status_filter: ProposalStatus | None = None,
    user: User = Depends(require_permission(Permission.PROPOSAL_VIEW)),
    repo: ProposalRepository = Depends(get_proposal_repo),
) -> list[ProposalOut]:
    proposals = repo.list_for_user(user, status=status_filter)
    return [ProposalOut.from_proposal(p) for p in proposals]


@router.get("/{proposal_id}", response_model=ProposalOut)
def get_proposal(
    proposal_id: str,
    user: User = Depends(require_permission(Permission.PROPOSAL_VIEW)),
    repo: ProposalRepository = Depends(get_proposal_repo),
) -> ProposalOut:
    return ProposalOut.from_proposal(_get_accessible(proposal_id, user, repo))


@router.post("/{proposal_id}/submit", response_model=ProposalOut)
def submit_proposal(
    proposal_id: str,
    user: User = Depends(require_permission(Permission.PROPOSAL_SUBMIT)),
    repo: ProposalRepository = Depends(get_proposal_repo),
    audit: AuditWriter = Depends(get_audit_writer),
) -> ProposalOut:
    try:
        proposal = lifecycle.submit_proposal(user, _get_accessible(proposal_id, user, repo), repo, audit)
    except Exception as exc:  # noqa: BLE001
        raise _handle(exc) from exc
    return ProposalOut.from_proposal(proposal)


@router.post("/{proposal_id}/review", response_model=ProposalOut)
def review_proposal(
    proposal_id: str,
    payload: ReviewRequest,
    user: User = Depends(require_permission(Permission.PROPOSAL_REVIEW)),
    repo: ProposalRepository = Depends(get_proposal_repo),
    audit: AuditWriter = Depends(get_audit_writer),
) -> ProposalOut:
    try:
        proposal = lifecycle.review_proposal(
            user, _get_accessible(proposal_id, user, repo), payload.comment, repo, audit
        )
    except Exception as exc:  # noqa: BLE001
        raise _handle(exc) from exc
    return ProposalOut.from_proposal(proposal)


@router.post("/{proposal_id}/return", response_model=ProposalOut)
def return_proposal(
    proposal_id: str,
    payload: ReturnRequest,
    user: User = Depends(require_permission(Permission.PROPOSAL_REVIEW)),
    repo: ProposalRepository = Depends(get_proposal_repo),
    audit: AuditWriter = Depends(get_audit_writer),
) -> ProposalOut:
    try:
        proposal = lifecycle.return_proposal(
            user, _get_accessible(proposal_id, user, repo), payload.reason, repo, audit
        )
    except Exception as exc:  # noqa: BLE001
        raise _handle(exc) from exc
    return ProposalOut.from_proposal(proposal)


@router.post("/{proposal_id}/decide", response_model=ProposalOut)
def decide_proposal(
    proposal_id: str,
    payload: DecideRequest,
    user: User = Depends(require_permission(Permission.PROPOSAL_DECIDE)),
    repo: ProposalRepository = Depends(get_proposal_repo),
    audit: AuditWriter = Depends(get_audit_writer),
) -> ProposalOut:
    try:
        proposal = lifecycle.decide_proposal(
            user, _get_accessible(proposal_id, user, repo), payload.outcome, payload.reason, repo, audit
        )
    except Exception as exc:  # noqa: BLE001
        raise _handle(exc) from exc
    return ProposalOut.from_proposal(proposal)


@router.post("/{proposal_id}/modify", response_model=ProposalOut)
def modify_proposal(
    proposal_id: str,
    payload: ProposalUpdate,
    user: User = Depends(require_permission(Permission.PROPOSAL_EDIT)),
    repo: ProposalRepository = Depends(get_proposal_repo),
    audit: AuditWriter = Depends(get_audit_writer),
) -> ProposalOut:
    try:
        proposal = lifecycle.modify_proposal(
            user, _get_accessible(proposal_id, user, repo), payload.model_dump(), repo, audit
        )
    except Exception as exc:  # noqa: BLE001
        raise _handle(exc) from exc
    return ProposalOut.from_proposal(proposal)


@router.post("/{proposal_id}/implement", response_model=ProposalOut)
def implement_proposal(
    proposal_id: str,
    user: User = Depends(require_permission(Permission.OUTCOME_RECORD)),
    repo: ProposalRepository = Depends(get_proposal_repo),
    audit: AuditWriter = Depends(get_audit_writer),
) -> ProposalOut:
    try:
        proposal = lifecycle.implement_proposal(
            user, _get_accessible(proposal_id, user, repo), repo, audit
        )
    except Exception as exc:  # noqa: BLE001
        raise _handle(exc) from exc
    return ProposalOut.from_proposal(proposal)


@router.post("/{proposal_id}/close", response_model=ProposalOut)
def close_proposal(
    proposal_id: str,
    user: User = Depends(require_permission(Permission.PROPOSAL_DECIDE)),
    repo: ProposalRepository = Depends(get_proposal_repo),
    audit: AuditWriter = Depends(get_audit_writer),
) -> ProposalOut:
    try:
        proposal = lifecycle.close_proposal(
            user, _get_accessible(proposal_id, user, repo), repo, audit
        )
    except Exception as exc:  # noqa: BLE001
        raise _handle(exc) from exc
    return ProposalOut.from_proposal(proposal)


@router.get("/{proposal_id}/versions", response_model=list[VersionOut])
def list_versions(
    proposal_id: str,
    user: User = Depends(require_permission(Permission.PROPOSAL_VIEW)),
    repo: ProposalRepository = Depends(get_proposal_repo),
) -> list[VersionOut]:
    _get_accessible(proposal_id, user, repo)
    return [
        VersionOut(
            version=s.version,
            content_hash=s.content_hash,
            changes=list(s.changes),
            action=s.action,
            actor_username=s.actor_username,
            reason=s.reason,
            created_at=s.created_at,
        )
        for s in repo.list_versions(proposal_id)
    ]


@router.get("/{proposal_id}/comments", response_model=list[CommentOut])
def list_comments(
    proposal_id: str,
    user: User = Depends(require_permission(Permission.PROPOSAL_VIEW)),
    repo: ProposalRepository = Depends(get_proposal_repo),
) -> list[CommentOut]:
    _get_accessible(proposal_id, user, repo)
    return [
        CommentOut(
            id=c.id,
            kind=c.kind,
            author_username=c.author_username,
            body=c.body,
            version=c.version,
            created_at=c.created_at,
        )
        for c in repo.list_comments(proposal_id)
    ]


@router.get("/{proposal_id}/timeline", response_model=list[TimelineEntryOut])
def proposal_timeline(
    proposal_id: str,
    user: User = Depends(require_permission(Permission.PROPOSAL_VIEW)),
    repo: ProposalRepository = Depends(get_proposal_repo),
    audit: AuditWriter = Depends(get_audit_writer),
) -> list[TimelineEntryOut]:
    _get_accessible(proposal_id, user, repo)
    entries: list[TimelineEntryOut] = []

    for event in audit.list_for_entity(proposal_id):
        entries.append(
            TimelineEntryOut(
                at=event.created_at,
                kind="audit",
                source=event.action,
                actor_username=event.actor_username,
                version=event.proposal_version,
                message=event.summary,
            )
        )

    for comment in repo.list_comments(proposal_id):
        entries.append(
            TimelineEntryOut(
                at=comment.created_at,
                kind="comment",
                source=comment.kind,
                actor_username=comment.author_username,
                version=comment.version,
                message=comment.body,
            )
        )

    entries.sort(key=lambda entry: entry.at)
    return entries