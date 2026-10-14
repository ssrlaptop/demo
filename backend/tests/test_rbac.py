from __future__ import annotations

import uuid

from app.auth.rbac import can_access, has_permission, permissions_for_role
from app.models.document_acl import DocumentAcl
from app.models.enums import Classification, Permission, Role
from app.models.user import User


def _user(role: Role, department: str, *, active: bool = True, user_id: str | None = None) -> User:
    return User(
        id=user_id or str(uuid.uuid4()),
        username=f"{role.value}_{department}".lower(),
        email="u@example.gov",
        full_name="U",
        hashed_password="x",
        role=role,
        department=department,
        is_active=active,
    )


def test_officer_cannot_decide() -> None:
    officer = _user(Role.OFFICER, "Traffic")
    assert has_permission(officer, Permission.PROPOSAL_CREATE)
    assert not has_permission(officer, Permission.PROPOSAL_DECIDE)


def test_approver_can_decide() -> None:
    approver = _user(Role.APPROVER, "HQ")
    assert has_permission(approver, Permission.PROPOSAL_DECIDE)


def test_auditor_cannot_create() -> None:
    auditor = _user(Role.AUDITOR, "HQ")
    assert has_permission(auditor, Permission.AUDIT_VIEW)
    assert not has_permission(auditor, Permission.PROPOSAL_CREATE)


def test_admin_has_all_permissions() -> None:
    admin = _user(Role.ADMIN, "HQ")
    assert permissions_for_role(Role.ADMIN) == frozenset(Permission)
    assert all(has_permission(admin, p) for p in Permission)


def test_inactive_user_has_no_permissions() -> None:
    officer = _user(Role.OFFICER, "Traffic", active=False)
    assert not has_permission(officer, Permission.PROPOSAL_VIEW)


def _acl(*, owner_id: str, department: str, classification: Classification, **kwargs) -> DocumentAcl:
    return DocumentAcl(
        document_id="doc-1",
        owner_id=owner_id,
        owner_department=department,
        classification=classification,
        **kwargs,
    )


def test_can_access_deny_by_default() -> None:
    outsider = _user(Role.OFFICER, "CID")
    acl = _acl(owner_id="someone-else", department="Traffic", classification=Classification.INTERNAL)
    assert can_access(outsider, acl) is False


def test_can_access_owner_allowed() -> None:
    owner = _user(Role.OFFICER, "Traffic")
    acl = _acl(owner_id=owner.id, department="Traffic", classification=Classification.CONFIDENTIAL)
    assert can_access(owner, acl) is True


def test_can_access_department_allowed() -> None:
    peer = _user(Role.OFFICER, "Traffic")
    acl = _acl(owner_id="other", department="Traffic", classification=Classification.INTERNAL)
    assert can_access(peer, acl) is True


def test_can_access_explicit_user_allowed() -> None:
    granted = _user(Role.OFFICER, "CID")
    acl = _acl(
        owner_id="other",
        department="Traffic",
        classification=Classification.RESTRICTED,
        allowed_user_ids=frozenset({granted.id}),
    )
    assert can_access(granted, acl) is True


def test_classification_does_not_grant_access() -> None:
    outsider = _user(Role.OFFICER, "CID")
    low = _acl(owner_id="other", department="Traffic", classification=Classification.INTERNAL)
    high = _acl(owner_id="other", department="Traffic", classification=Classification.CONFIDENTIAL)
    # Both denied regardless of label: classification is not an authorization control.
    assert can_access(outsider, low) is False
    assert can_access(outsider, high) is False


def test_admin_bypasses_acl() -> None:
    admin = _user(Role.ADMIN, "HQ")
    acl = _acl(owner_id="other", department="Traffic", classification=Classification.CONFIDENTIAL)
    assert can_access(admin, acl) is True


def test_inactive_user_denied_even_as_owner() -> None:
    owner = _user(Role.OFFICER, "Traffic", active=False)
    acl = _acl(owner_id=owner.id, department="Traffic", classification=Classification.INTERNAL)
    assert can_access(owner, acl) is False
