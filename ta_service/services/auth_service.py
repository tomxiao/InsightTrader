from __future__ import annotations

from ta_service.config.settings import Settings
from ta_service.contracts.auth import build_login_response
from ta_service.models.auth import LoginRequest, LoginResponse, MobileUser
from ta_service.repos.users import UserRepository


class AuthService:
    def __init__(self, *, user_repo: UserRepository, settings: Settings):
        self.user_repo = user_repo
        self.settings = settings

    def login(self, payload: LoginRequest) -> LoginResponse:
        user = self.user_repo.ensure_dev_user(payload.username.strip())
        token = self._build_token(user["id"])
        return build_login_response(user, token)

    def get_current_user(self, token: str) -> MobileUser | None:
        user_id = self._parse_token(token)
        if not user_id:
            return None

        document = self.user_repo.get_by_id(user_id)
        if not document:
            return None
        return MobileUser(**document)

    def _build_token(self, user_id: str) -> str:
        return f"{self.settings.auth_token_prefix}:{user_id}"

    def _parse_token(self, token: str) -> str | None:
        prefix = f"{self.settings.auth_token_prefix}:"
        if not token.startswith(prefix):
            return None
        return token.removeprefix(prefix).strip() or None
