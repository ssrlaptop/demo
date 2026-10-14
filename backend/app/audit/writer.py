"""Audit writers.

Only append inserts happen here — there is intentionally no update/delete path,
enforcing the NN3 append-only rule at the storage layer.
"""

from __future__ import annotations

import logging
from dataclasses import replace
from typing import Protocol

import pymongo
from pymongo.database import Database

from app.audit.hash_chain import compute_event_hash
from app.models.audit_event import AuditEvent

logger = logging.getLogger(__name__)


class AuditWriter(Protocol):
    def append(self, event: AuditEvent) -> AuditEvent: ...
    def list_all(self, limit: int = 200) -> list[AuditEvent]: ...
    def list_for_entity(self, entity_id: str, limit: int = 500) -> list[AuditEvent]: ...


def _newest_first(events: list[AuditEvent]) -> list[AuditEvent]:
    return sorted(events, key=lambda e: e.seq, reverse=True)


class MongoAuditWriter:
    def __init__(self, db: Database) -> None:
        self._collection = db["audit_events"]
        self._counter = db["audit_seq"]

    def append(self, event: AuditEvent) -> AuditEvent:
        seq = self._counter.find_one_and_update(
            {"_id": "event"},
            {"$inc": {"value": 1}},
            upsert=True,
            return_document=pymongo.ReturnDocument.AFTER,
        )["value"]

        previous = self._collection.find_one({"seq": seq - 1}, {"event_hash": 1})
        prev_hash = previous["event_hash"] if previous else None

        pending = replace(event, seq=seq, prev_hash=prev_hash, event_hash="")
        signed = replace(pending, event_hash=compute_event_hash(pending))

        self._collection.insert_one(signed.to_document())
        return signed

    def list_all(self, limit: int = 200) -> list[AuditEvent]:
        cursor = self._collection.find({}).sort("seq", -1).limit(limit)
        return _newest_first([AuditEvent.from_document(doc) for doc in cursor])

    def list_for_entity(self, entity_id: str, limit: int = 500) -> list[AuditEvent]:
        cursor = self._collection.find({"entity_id": entity_id}).sort("seq", -1).limit(limit)
        return _newest_first([AuditEvent.from_document(doc) for doc in cursor])


class InMemoryAuditWriter:
    """Test double; same semantics as MongoAuditWriter but in-process."""

    def __init__(self) -> None:
        self._events: list[AuditEvent] = []

    def append(self, event: AuditEvent) -> AuditEvent:
        seq = len(self._events) + 1
        prev_hash = self._events[-1].event_hash if self._events else None
        pending = replace(event, seq=seq, prev_hash=prev_hash, event_hash="")
        signed = replace(pending, event_hash=compute_event_hash(pending))
        self._events.append(signed)
        return signed

    def list_all(self, limit: int = 200) -> list[AuditEvent]:
        return _newest_first(list(self._events))[:limit]

    def list_for_entity(self, entity_id: str, limit: int = 500) -> list[AuditEvent]:
        matches = [e for e in self._events if e.entity_id == entity_id]
        return _newest_first(matches)[:limit]


__all__ = ["AuditWriter", "MongoAuditWriter", "InMemoryAuditWriter"]