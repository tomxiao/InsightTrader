from __future__ import annotations


def test_login_returns_token_contract(api_client) -> None:
    response = api_client.post(
        "/auth/login",
        json={"username": "tester", "password": "password123"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["access_token"] == "token-1"
    assert payload["user"]["username"] == "tester"


def test_me_returns_current_user(api_client) -> None:
    response = api_client.get("/auth/me")

    assert response.status_code == 200
    payload = response.json()
    assert payload["id"] == "user-1"
    assert payload["role"] == "admin"


def test_logout_returns_ok(api_client) -> None:
    response = api_client.post(
        "/auth/logout",
        headers={"Authorization": "Bearer token-1"},
    )

    assert response.status_code == 200
    assert response.json() == {"ok": True}

