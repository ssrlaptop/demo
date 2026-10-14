"""Shared API dependencies for Phase 2."""

from __future__ import annotations

from app.audit.writer import AuditWriter, MongoAuditWriter
from app.db.mongo import get_db
from app.repositories.proposal_repo import (
    MongoProposalRepository,
    ProposalRepository,
)


def get_proposal_repo() -> ProposalRepository:
    return MongoProposalRepository(get_db())


def get_audit_writer() -> AuditWriter:
    return MongoAuditWriter(get_db())


__all__ = ["get_audit_writer", "get_proposal_repo"]