"""Domain enums shared across models, schemas, and services."""

from __future__ import annotations

from enum import Enum


class Role(str, Enum):
    OFFICER = "officer"
    REVIEWER = "reviewer"
    APPROVER = "approver"
    AUDITOR = "auditor"
    ADMIN = "admin"


class Classification(str, Enum):
    """Sensitivity label. Describes handling requirements ONLY.

    Classification never grants or denies access on its own; authorization is a
    separate control (see app.auth.rbac.can_access).
    """

    INTERNAL = "INTERNAL"
    RESTRICTED = "RESTRICTED"
    CONFIDENTIAL = "CONFIDENTIAL"


class Permission(str, Enum):
    PROPOSAL_VIEW = "proposal:view"
    PROPOSAL_CREATE = "proposal:create"
    PROPOSAL_EDIT = "proposal:edit"
    PROPOSAL_SUBMIT = "proposal:submit"
    PROPOSAL_REVIEW = "proposal:review"
    PROPOSAL_DECIDE = "proposal:decide"
    DOCUMENT_VIEW = "document:view"
    DOCUMENT_UPLOAD = "document:upload"
    OUTCOME_RECORD = "outcome:record"
    AUDIT_VIEW = "audit:view"
    USER_MANAGE = "user:manage"


class ProposalStatus(str, Enum):
    CREATED = "created"
    SUBMITTED = "submitted"
    REVIEWED = "reviewed"
    MODIFIED = "modified"
    APPROVED = "approved"
    REJECTED = "rejected"
    RETURNED = "returned"
    IMPLEMENTED = "implemented"
    CLOSED = "closed"
