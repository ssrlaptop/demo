"""Role-based access control and document-level authorization.

Two independent controls (per NN1):
  * classification  -> sensitivity / handling requirements (informational)
  * authorization   -> whether a specific user may access a specific record

`can_access` is the single decision point for document access and is
deny-by-default. It is exercised by the retrieval pipeline (Phase 4) as well.
"""

from __future__ import annotations

from app.models.document_acl import DocumentAcl
from app.models.enums import Permission, Role
from app.models.proposal import Proposal
from app.models.user import User

ROLE_PERMISSIONS: dict[Role, frozenset[Permission]] = {
    Role.OFFICER: frozenset(
        {
            Permission.PROPOSAL_VIEW,
            Permission.PROPOSAL_CREATE,
            Permission.PROPOSAL_EDIT,
            Permission.PROPOSAL_SUBMIT,
            Permission.DOCUMENT_VIEW,
            Permission.DOCUMENT_UPLOAD,
            Permission.OUTCOME_RECORD,
        }
    ),
    Role.REVIEWER: frozenset(
        {
            Permission.PROPOSAL_VIEW,
            Permission.PROPOSAL_CREATE,
            Permission.PROPOSAL_EDIT,
            Permission.PROPOSAL_SUBMIT,
            Permission.PROPOSAL_REVIEW,
            Permission.DOCUMENT_VIEW,
            Permission.DOCUMENT_UPLOAD,
            Permission.OUTCOME_RECORD,
        }
    ),
    Role.APPROVER: frozenset(
        {
            Permission.PROPOSAL_VIEW,
            Permission.PROPOSAL_REVIEW,
            Permission.PROPOSAL_DECIDE,
            Permission.DOCUMENT_VIEW,
            Permission.OUTCOME_RECORD,
        }
    ),
    Role.AUDITOR: frozenset(
        {
            Permission.PROPOSAL_VIEW,
            Permission.DOCUMENT_VIEW,
            Permission.AUDIT_VIEW,
        }
    ),
    Role.ADMIN: frozenset(Permission),
}


def permissions_for_role(role: Role) -> frozenset[Permission]:
    return ROLE_PERMISSIONS.get(role, frozenset())


def has_permission(user: User, permission: Permission) -> bool:
    if not user.is_active:
        return False
    return permission in permissions_for_role(user.role)


def can_access(user: User, acl: DocumentAcl) -> bool:
    """Deny-by-default document authorization.

    Classification is intentionally NOT consulted here; it cannot grant access.
    """
    if not user.is_active:
        return False
    if user.role == Role.ADMIN:
        return True
    if user.id in acl.allowed_user_ids:
        return True
    if user.department in acl.allowed_departments:
        return True
    if user.department == acl.owner_department:
        return True
    if user.id == acl.owner_id:
        return True
    return False


def can_access_proposal(user: User, proposal: Proposal) -> bool:
    """Proposal authorization.

    Department/officer scoping comes from the same deny-by-default ACL used for
    documents. Oversight roles (approver, auditor, admin) additionally have
    cross-department visibility so they can decide and audit — a role policy
    that is independent of a proposal's classification (NN1)."""
    if not user.is_active:
        return False
    if user.role in {Role.APPROVER, Role.AUDITOR, Role.ADMIN}:
        return True
    acl = DocumentAcl(
        document_id=proposal.id,
        owner_id=proposal.owner_id,
        owner_department=proposal.owner_department,
        classification=proposal.classification,
        allowed_user_ids=proposal.allowed_user_ids,
        allowed_departments=proposal.allowed_departments,
    )
    return can_access(user, acl)
