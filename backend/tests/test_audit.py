from __future__ import annotations

import dataclasses

from app.audit.hash_chain import sha256_hex, verify_chain
from app.audit.writer import InMemoryAuditWriter
from app.models.audit_event import AuditEvent


def _event(**overrides) -> AuditEvent:
    base = {
        "actor_id": "u1",
        "actor_username": "officer",
        "action": "create",
        "entity_type": "proposal",
        "entity_id": "p1",
        "summary": "proposal.create v1",
        "proposal_version": 1,
        "content_hash": "abc",
    }
    base.update(overrides)
    return AuditEvent(**base)


def test_sha256_is_deterministic_and_key_order_independent() -> None:
    assert sha256_hex({"a": 1, "b": 2}) == sha256_hex({"b": 2, "a": 1})


def test_append_links_events_into_a_chain() -> None:
    writer = InMemoryAuditWriter()
    first = writer.append(_event())
    second = writer.append(_event(action="submit", proposal_version=2))

    assert first.seq == 1
    assert first.prev_hash is None
    assert first.event_hash
    assert second.seq == 2
    assert second.prev_hash == first.event_hash
    assert verify_chain([first, second]).verified


def test_verify_detects_tampering() -> None:
    writer = InMemoryAuditWriter()
    first = writer.append(_event())
    second = writer.append(_event(action="submit"))
    tampered = dataclasses.replace(second, summary="proposal.submit v999")

    verdict = verify_chain([first, tampered])
    assert verdict.verified is False
    assert verdict.first_bad_seq == second.seq


def test_verify_detects_broken_prev_link() -> None:
    writer = InMemoryAuditWriter()
    first = writer.append(_event())
    second = writer.append(_event(action="submit"))
    tampered = dataclasses.replace(second, prev_hash="deadbeef")

    verdict = verify_chain([first, tampered])
    assert verdict.verified is False
    assert verdict.first_bad_seq == second.seq


def test_verify_orders_by_sequence_number() -> None:
    writer = InMemoryAuditWriter()
    a = writer.append(_event())
    b = writer.append(_event(action="submit"))
    # Storage order is irrelevant; the chain is defined by seq.
    assert verify_chain([b, a]).verified is True


def test_empty_chain_verifies() -> None:
    assert verify_chain([]).verified is True


def test_list_all_returns_newest_first() -> None:
    writer = InMemoryAuditWriter()
    writer.append(_event())
    writer.append(_event(action="submit"))
    seqs = [event.seq for event in writer.list_all()]
    assert seqs == [2, 1]


def test_list_for_entity_filters() -> None:
    writer = InMemoryAuditWriter()
    writer.append(_event(entity_id="p1"))
    writer.append(_event(entity_id="p2"))
    assert {event.entity_id for event in writer.list_for_entity("p1")} == {"p1"}