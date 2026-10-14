"""Hash-chain primitives for the append-only audit (NN3).

Each event's hash covers the event fields plus the previous event's hash, so any
earlier modification invalidates every later link. Verified by
scripts/verify_audit.py and the /audit/verify endpoint.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Sequence

from app.models.audit_event import AuditEvent


def _normalize_datetime(value: datetime) -> str:
    """Second-precision UTC ISO string.

    Storage round-trips (Mongo) can drop timezone info and sub-second precision,
    so the hash must use a representation stable across write and read.
    """
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat()


def sha256_hex(value: Any) -> str:
    """Stable JSON-then-hash. `value` must already be JSON-serializable."""
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def canonical_event(event: AuditEvent) -> str:
    """Serialize everything an event hash covers, EXCLUDING event_hash itself."""
    return json.dumps(
        {
            "seq": event.seq,
            "created_at": _normalize_datetime(event.created_at),
            "actor_id": event.actor_id,
            "actor_username": event.actor_username,
            "action": event.action,
            "entity_type": event.entity_type,
            "entity_id": event.entity_id,
            "proposal_version": event.proposal_version,
            "content_hash": event.content_hash,
            "outcome": event.outcome,
            "summary": event.summary,
            "prev_hash": event.prev_hash,
        },
        sort_keys=True,
        separators=(",", ":"),
    )


def compute_event_hash(event: AuditEvent) -> str:
    return hashlib.sha256(canonical_event(event).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class ChainVerdict:
    verified: bool
    checked: int
    first_bad_seq: int | None = None


def verify_chain(events: Sequence[AuditEvent], order: str = "seq") -> ChainVerdict:
    """Verify the hash chain over a full ordered event sequence.

    `order` is "seq" (ascending) or "seq_desc" (newest first, e.g. from a
    find().sort(-1)). Both are supported and give identical results.
    """
    items: list[AuditEvent] = list(events)
    if not items:
        return ChainVerdict(verified=True, checked=0)

    if order == "seq_desc":
        items = sorted(items, key=lambda e: e.seq)
    else:
        items = sorted(items, key=lambda e: e.seq)

    previous_hash: str | None = None
    for idx, event in enumerate(items):
        expected_prev = None if idx == 0 else items[idx - 1].event_hash
        if event.prev_hash != expected_prev:
            return ChainVerdict(verified=False, checked=idx + 1, first_bad_seq=event.seq)
        if compute_event_hash(event) != event.event_hash:
            return ChainVerdict(verified=False, checked=idx + 1, first_bad_seq=event.seq)
        previous_hash = event.event_hash
    return ChainVerdict(verified=True, checked=len(items))