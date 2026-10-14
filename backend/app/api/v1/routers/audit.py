"""Audit endpoints (NN3): append-only event stream + chain verification."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.api.v1.deps import get_audit_writer
from app.audit.hash_chain import verify_chain
from app.audit.writer import AuditWriter
from app.auth.dependencies import require_permission
from app.models.enums import Permission
from app.models.user import User
from app.schemas.proposal import AuditEventOut, AuditVerifyOut

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("/events", response_model=list[AuditEventOut])
def list_events(
    limit: int = Query(100, ge=1, le=1000),
    _: User = Depends(require_permission(Permission.AUDIT_VIEW)),
    audit: AuditWriter = Depends(get_audit_writer),
) -> list[AuditEventOut]:
    return [
        AuditEventOut(
            id=e.id,
            seq=e.seq,
            actor_id=e.actor_id,
            actor_username=e.actor_username,
            action=e.action,
            entity_type=e.entity_type,
            entity_id=e.entity_id,
            proposal_version=e.proposal_version,
            content_hash=e.content_hash,
            outcome=e.outcome,
            summary=e.summary,
            prev_hash=e.prev_hash,
            event_hash=e.event_hash,
            created_at=e.created_at,
        )
        for e in audit.list_all(limit=limit)
    ]


@router.get("/verify", response_model=AuditVerifyOut)
def verify_audit(
    _: User = Depends(require_permission(Permission.AUDIT_VIEW)),
    audit: AuditWriter = Depends(get_audit_writer),
) -> AuditVerifyOut:
    events = audit.list_all(limit=10_000)
    verdict = verify_chain(list(reversed(events)))  # list_all is newest-first
    return AuditVerifyOut(
        verified=verdict.verified,
        checked=verdict.checked,
        first_bad_seq=verdict.first_bad_seq,
    )