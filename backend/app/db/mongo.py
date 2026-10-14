"""MongoDB client and index bootstrap.

Connection is lazy and tolerant: the API still starts (so /health reports the
situation) if Atlas is unreachable. Index creation is idempotent.
"""

from __future__ import annotations

import logging
from functools import lru_cache

from pymongo import ASCENDING, MongoClient
from pymongo.database import Database
from pymongo.errors import PyMongoError

from app.core.config import get_settings

logger = logging.getLogger(__name__)


@lru_cache
def get_client() -> MongoClient:
    settings = get_settings()
    return MongoClient(settings.mongodb_uri, serverSelectionTimeoutMS=5000, uuidRepresentation="standard")


def get_db() -> Database:
    settings = get_settings()
    return get_client()[settings.mongodb_db]


def ensure_indexes(db: Database) -> list[str]:
    """Create required indexes. Returns the list of indexes ensured."""
    ensured: list[str] = []

    db["users"].create_index([("username", ASCENDING)], unique=True, name="uniq_username")
    ensured.append("users.uniq_username")
    db["users"].create_index([("email", ASCENDING)], unique=True, name="uniq_email")
    ensured.append("users.uniq_email")

    db["document_acl"].create_index([("document_id", ASCENDING)], unique=True, name="uniq_document_id")
    ensured.append("document_acl.uniq_document_id")

    # Phase 2: proposals, version history, comments, append-only audit
    db["proposals"].create_index([("owner_id", ASCENDING)], name="idx_proposals_owner")
    ensured.append("proposals.idx_proposals_owner")
    db["proposals"].create_index([("owner_department", ASCENDING)], name="idx_proposals_dept")
    ensured.append("proposals.idx_proposals_dept")
    db["proposals"].create_index([("status", ASCENDING)], name="idx_proposals_status")
    ensured.append("proposals.idx_proposals_status")
    db["proposals"].create_index([("allowed_departments", ASCENDING)], name="idx_proposals_allowed_depts")
    ensured.append("proposals.idx_proposals_allowed_depts")
    db["proposals"].create_index([("allowed_user_ids", ASCENDING)], name="idx_proposals_allowed_users")
    ensured.append("proposals.idx_proposals_allowed_users")

    db["proposal_versions"].create_index(
        [("proposal_id", ASCENDING), ("version", ASCENDING)],
        unique=True,
        name="uniq_proposal_version",
    )
    ensured.append("proposal_versions.uniq_proposal_version")

    db["proposal_comments"].create_index(
        [("proposal_id", ASCENDING), ("created_at", ASCENDING)], name="idx_comments"
    )
    ensured.append("proposal_comments.idx_comments")

    db["audit_events"].create_index([("seq", ASCENDING)], unique=True, name="uniq_audit_seq")
    ensured.append("audit_events.uniq_audit_seq")
    db["audit_events"].create_index([("entity_id", ASCENDING)], name="idx_audit_entity")
    ensured.append("audit_events.idx_audit_entity")

    return ensured


def ping() -> bool:
    try:
        get_client().admin.command("ping")
        return True
    except PyMongoError:
        return False


def try_ensure_indexes() -> bool:
    """Best-effort index bootstrap; never raises at startup."""
    try:
        ensure_indexes(get_db())
        return True
    except PyMongoError as exc:
        logger.warning("Could not ensure MongoDB indexes: %s", exc)
        return False
