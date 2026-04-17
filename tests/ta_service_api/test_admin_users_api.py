from __future__ import annotations


def test_list_admin_users_returns_managed_users(api_client) -> None:
    response = api_client.get("/admin/users")

    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 1
    assert payload[0]["username"] == "alice"


def test_create_admin_user_returns_created_user(api_client) -> None:
    response = api_client.post(
        "/admin/users",
        json={
            "username": "bob",
            "displayName": "Bob",
            "password": "password123",
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["username"] == "bob"
    assert payload["displayName"] == "Bob"


def test_update_admin_user_status_returns_updated_user(api_client) -> None:
    response = api_client.patch(
        "/admin/users/managed-1/status",
        json={"status": "disabled"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["id"] == "managed-1"
    assert payload["status"] == "disabled"


def test_reset_admin_user_password_returns_user(api_client) -> None:
    response = api_client.post(
        "/admin/users/managed-1/reset-password",
        json={"password": "newpassword123"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["id"] == "managed-1"
    assert payload["username"] == "alice"

