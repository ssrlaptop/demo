from __future__ import annotations


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _payload(**overrides) -> dict:
    payload = {
        "subject": "Body cameras pilot",
        "purpose": "Pilot body-worn cameras in Traffic",
        "resources": ["cameras"],
        "budget": [{"item": "cameras", "amount": 50000}],
        "policies": ["Policy 44"],
    }
    payload.update(overrides)
    return payload


def _create(client, token: str, **overrides):
    return client.post("/api/v1/proposals", json=_payload(**overrides), headers=_auth(token))


def test_create_requires_auth(client) -> None:
    assert client.post("/api/v1/proposals", json=_payload()).status_code == 401


def test_auditor_cannot_create(client, login) -> None:
    response = _create(client, login("auditor"))
    assert response.status_code == 403


def test_officer_creates_proposal(client, login) -> None:
    response = _create(client, login("officer"))
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["status"] == "created"
    assert body["version"] == 1
    assert body["owner_department"] == "Traffic"
    assert body["budget"][0]["item"] == "cameras"


def test_list_is_department_scoped(client, login) -> None:
    create = _create(client, login("officer"))
    proposal_id = create.json()["id"]

    officer_ids = {p["id"] for p in client.get("/api/v1/proposals", headers=_auth(login("officer"))).json()}
    cid_ids = {p["id"] for p in client.get("/api/v1/proposals", headers=_auth(login("officer_cid"))).json()}
    admin_ids = {p["id"] for p in client.get("/api/v1/proposals", headers=_auth(login("admin"))).json()}

    assert proposal_id in officer_ids
    assert proposal_id not in cid_ids
    assert proposal_id in admin_ids


def test_get_cross_department_forbidden(client, login) -> None:
    proposal_id = _create(client, login("officer")).json()["id"]
    response = client.get(f"/api/v1/proposals/{proposal_id}", headers=_auth(login("officer_cid")))
    assert response.status_code == 403


def test_get_missing_returns_404(client, login) -> None:
    response = client.get("/api/v1/proposals/does-not-exist", headers=_auth(login("officer")))
    assert response.status_code == 404


def test_full_lifecycle_and_artifacts(client, login) -> None:
    officer = login("officer")
    reviewer = login("reviewer")
    approver = login("approver")

    proposal_id = _create(client, officer).json()["id"]

    assert client.post(f"/api/v1/proposals/{proposal_id}/submit", headers=_auth(officer)).json()["status"] == "submitted"
    reviewed = client.post(
        f"/api/v1/proposals/{proposal_id}/review", json={"comment": "Looks good"}, headers=_auth(reviewer)
    )
    assert reviewed.json()["status"] == "reviewed"

    decided = client.post(
        f"/api/v1/proposals/{proposal_id}/decide",
        json={"outcome": "approved", "reason": "Meets policy"},
        headers=_auth(approver),
    )
    body = decided.json()
    assert body["status"] == "approved"
    assert body["decisions"][-1]["snapshot_hash"]

    assert client.post(f"/api/v1/proposals/{proposal_id}/implement", headers=_auth(officer)).json()["status"] == "implemented"
    assert client.post(f"/api/v1/proposals/{proposal_id}/close", headers=_auth(approver)).json()["status"] == "closed"

    versions = client.get(f"/api/v1/proposals/{proposal_id}/versions", headers=_auth(officer)).json()
    assert len(versions) == 6
    assert [v["version"] for v in versions] == [1, 2, 3, 4, 5, 6]

    timeline = client.get(f"/api/v1/proposals/{proposal_id}/timeline", headers=_auth(officer)).json()
    kinds = {entry["kind"] for entry in timeline}
    assert kinds == {"audit", "comment"}
    assert len(timeline) >= 6


def test_modify_after_return_bumps_version(client, login) -> None:
    officer = login("officer")
    reviewer = login("reviewer")
    proposal_id = _create(client, officer).json()["id"]
    client.post(f"/api/v1/proposals/{proposal_id}/submit", headers=_auth(officer))
    client.post(f"/api/v1/proposals/{proposal_id}/return", json={"reason": "Add detail"}, headers=_auth(reviewer))

    modified = client.post(
        f"/api/v1/proposals/{proposal_id}/modify",
        json={"subject": "Body cameras pilot v2"},
        headers=_auth(officer),
    )
    body = modified.json()
    assert body["status"] == "modified"
    assert body["version"] == 4  # create, submit, return, modify


def test_illegal_transition_returns_409(client, login) -> None:
    officer = login("officer")
    approver = login("approver")
    proposal_id = _create(client, officer).json()["id"]
    response = client.post(
        f"/api/v1/proposals/{proposal_id}/decide",
        json={"outcome": "approved", "reason": "too early"},
        headers=_auth(approver),
    )
    assert response.status_code == 409


def test_role_without_permission_gets_403(client, login) -> None:
    officer = login("officer")
    proposal_id = _create(client, officer).json()["id"]
    client.post(f"/api/v1/proposals/{proposal_id}/submit", headers=_auth(officer))
    # Auditor cannot review
    response = client.post(
        f"/api/v1/proposals/{proposal_id}/review",
        json={"comment": "x"},
        headers=_auth(login("auditor")),
    )
    assert response.status_code == 403


def test_audit_endpoints_rbac_and_verification(client, login) -> None:
    officer = login("officer")
    auditor = login("auditor")
    proposal_id = _create(client, officer).json()["id"]
    client.post(f"/api/v1/proposals/{proposal_id}/submit", headers=_auth(officer))

    assert client.get("/api/v1/audit/events", headers=_auth(officer)).status_code == 403

    events = client.get("/api/v1/audit/events", headers=_auth(auditor))
    assert events.status_code == 200
    assert len(events.json()) >= 2

    verdict = client.get("/api/v1/audit/verify", headers=_auth(auditor)).json()
    assert verdict["verified"] is True
    assert verdict["checked"] >= 2


def test_audit_events_contain_no_document_content(client, login) -> None:
    officer = login("officer")
    auditor = login("auditor")
    subject = "Operation SECRET codename"
    _create(client, officer, subject=subject)
    events = client.get("/api/v1/audit/events", headers=_auth(auditor)).json()
    blob = " ".join(e["summary"] for e in events)
    assert "SECRET" not in blob
    assert subject not in blob


def test_list_status_filter(client, login) -> None:
    officer = login("officer")
    proposal_id = _create(client, officer).json()["id"]
    client.post(f"/api/v1/proposals/{proposal_id}/submit", headers=_auth(officer))
    submitted = client.get("/api/v1/proposals?status_filter=submitted", headers=_auth(officer)).json()
    assert {p["id"] for p in submitted} == {proposal_id}