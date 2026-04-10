from __future__ import annotations

from fastapi import HTTPException, status

from ta_service.config.settings import Settings
from ta_service.contracts.auth import build_login_response, build_mobile_user
from ta_service.models.auth import LoginRequest, LoginResponse, MobileUser
from ta_service.repos.user_sessions import UserSessionRepository
from ta_service.repos.users import UserRepository
from ta_service.services.auth_security import (
    generate_session_token,
    hash_session_token,
    verify_password,
)


class AuthService:
    def __init__(
        self,
        *,
        user_repo: UserRepository,
        session_repo: UserSessionRepository,
        settings: Settings,
    ):
        self.user_repo = user_repo
        self.session_repo = session_repo
        self.settings = settings

    def login(self, payload: LoginRequest) -> LoginResponse:
        username = payload.username.strip()
        user = self.user_repo.get_by_username(username)
        if not user or not verify_password(payload.password, user.get("passwordHash")):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="用户名或密码错误",
            )
        if user.get("status", "active") != "active":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="账号不可用，请联系管理员",
            )

        token = generate_session_token()
        self.session_repo.create(
            user_id=user["id"],
            token_hash=hash_session_token(token),
            client_type="mobile_h5",
            ttl_seconds=self.settings.auth_session_ttl_seconds,
        )
        self.user_repo.update_last_login(user["id"])
        refreshed_user = self.user_repo.get_by_id(user["id"]) or user
        return build_login_response(
            refreshed_user,
            token,
            self.settings.auth_session_ttl_seconds,
        )

    def get_current_user(self, token: str) -> MobileUser | None:
        session = self.session_repo.get_active_by_token_hash(hash_session_token(token))
        if not session:
            return None

        document = self.user_repo.get_by_id(session["userId"])
        if not document or document.get("status", "active") != "active":
            return None

        self.session_repo.touch(session["id"])
        return build_mobile_user(document)

    def logout(self, token: str) -> None:
        self.session_repo.revoke_by_token_hash(hash_session_token(token))
