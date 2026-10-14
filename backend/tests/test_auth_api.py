from __future__ import annotations

from tests.conftest import DEMO_PASSWORD


def test_login_success(client) -> None:
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "officer", "password": DEMO_PASSWORD},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["access_token"]
    assert body["refresh_token"]
    assert body["token_type"] == "bearer"


def test_login_wrong_password(client) -> None:
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "officer", "password": "wrong-password"},
    )
    assert response.status_code == 401


def test_login_unknown_user(client) -> None:
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "ghost", "password": DEMO_PASSWORD},
    )
    assert response.status_code == 401


def test_me_requires_token(client) -> None:
    assert client.get("/api/v1/auth/me").status_code == 401


def test_me_returns_profile(client, login) -> None:
    token = login("officer")
    response = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    body = response.json()
    assert body["username"] == "officer"
    assert body["role"] == "officer"
    assert body["department"] == "Traffic"


def test_refresh_issues_new_access_token(client) -> None:
    login_response = client.post(
        "/api/v1/auth/login",
        json={"username": "officer", "password": DEMO_PASSWORD},
    )
    refresh_token = login_response.json()["refresh_token"]
    response = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert response.status_code == 200
    assert response.json()["access_token"]


def test_refresh_rejects_access_token(client, login) -> None:
    access_token = login("officer")
    response = client.post("/api/v1/auth/refresh", json={"refresh_token": access_token})
    assert response.status_code == 401


def test_users_endpoint_forbidden_for_officer(client, login) -> None:
    token = login("officer")
    response = client.get("/api/v1/users", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 403


def test_users_endpoint_allowed_for_admin(client, login) -> None:
    token = login("admin")
    response = client.get("/api/v1/users", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    usernames = {u["username"] for u in response.json()}
    assert "officer" in usernames
