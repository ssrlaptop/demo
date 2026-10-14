from __future__ import annotations


def test_health_ok(client) -> None:
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["mongodb"] in {"connected", "unavailable"}


def test_request_id_header(client) -> None:
    response = client.get("/api/v1/health")
    assert response.headers.get("X-Request-ID")
