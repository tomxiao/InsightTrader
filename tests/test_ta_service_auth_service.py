import unittest

from fastapi import HTTPException

from ta_service.config.settings import Settings
from ta_service.models.auth import LoginRequest
from ta_service.services.auth_security import hash_password, hash_session_token
from ta_service.services.auth_service import AuthService


class FakeUserRepo:
    def __init__(self, users=None):
        self.users = {user["id"]: dict(user) for user in (users or [])}

    def get_by_username(self, username: str):
        for user in self.users.values():
            if user["username"] == username:
                return dict(user)
        return None

    def get_by_id(self, user_id: str):
        user = self.users.get(user_id)
        return dict(user) if user else None

    def update_last_login(self, user_id: str) -> None:
        if user_id in self.users:
            self.users[user_id]["lastLoginAt"] = "2026-04-10T12:00:00+00:00"


class FakeSessionRepo:
    def __init__(self):
        self.sessions = {}

    def create(self, *, user_id: str, token_hash: str, client_type: str, ttl_seconds: int):
        document = {
            "id": f"session-{len(self.sessions) + 1}",
            "userId": user_id,
            "tokenHash": token_hash,
            "clientType": client_type,
            "expiresAt": 9999999999,
            "revokedAt": None,
            "lastSeenAt": None,
        }
        self.sessions[token_hash] = document
        return dict(document)

    def get_active_by_token_hash(self, token_hash: str):
        document = self.sessions.get(token_hash)
        if not document or document["revokedAt"] is not None:
            return None
        return dict(document)

    def touch(self, session_id: str) -> None:
        for session in self.sessions.values():
            if session["id"] == session_id:
                session["lastSeenAt"] = "2026-04-10T12:01:00+00:00"

    def revoke_by_token_hash(self, token_hash: str) -> None:
        if token_hash in self.sessions:
            self.sessions[token_hash]["revokedAt"] = "2026-04-10T12:02:00+00:00"


class AuthServiceTests(unittest.TestCase):
    def setUp(self):
        self.user = {
            "id": "user-1",
            "username": "alice",
            "displayName": "Alice",
            "passwordHash": hash_password("secret-pass"),
            "role": "admin",
            "status": "active",
            "createdAt": "2026-04-10T12:00:00+00:00",
            "updatedAt": "2026-04-10T12:00:00+00:00",
            "lastLoginAt": None,
        }
        self.user_repo = FakeUserRepo([self.user])
        self.session_repo = FakeSessionRepo()
        self.service = AuthService(
            user_repo=self.user_repo,
            session_repo=self.session_repo,
            settings=Settings(auth_session_ttl_seconds=3600),
        )

    def test_login_creates_session_and_returns_role(self):
        response = self.service.login(LoginRequest(username="alice", password="secret-pass"))

        self.assertTrue(response.access_token)
        self.assertEqual(response.expires_in, 3600)
        self.assertEqual(response.user.role, "admin")
        self.assertIsNotNone(self.user_repo.get_by_id("user-1")["lastLoginAt"])
        self.assertIn(hash_session_token(response.access_token), self.session_repo.sessions)

    def test_login_rejects_wrong_password(self):
        with self.assertRaises(HTTPException) as context:
            self.service.login(LoginRequest(username="alice", password="wrong-pass"))

        self.assertEqual(context.exception.status_code, 401)

    def test_get_current_user_and_logout_use_session_token(self):
        response = self.service.login(LoginRequest(username="alice", password="secret-pass"))

        current_user = self.service.get_current_user(response.access_token)
        self.assertIsNotNone(current_user)
        self.assertEqual(current_user.role, "admin")

        self.service.logout(response.access_token)
        self.assertIsNone(self.service.get_current_user(response.access_token))


if __name__ == "__main__":
    unittest.main()
