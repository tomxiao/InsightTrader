from __future__ import annotations

from fastapi import HTTPException, status

from ta_service.contracts.admin_users import build_managed_user
from ta_service.models.admin_users import (
    CreateManagedUserRequest,
    ManagedUser,
    ResetManagedUserPasswordRequest,
    UpdateManagedUserStatusRequest,
)
from ta_service.repos.user_sessions import UserSessionRepository
from ta_service.repos.users import UserRepository
from ta_service.services.auth_security import hash_password


class AdminUserService:
    def __init__(
        self,
        *,
        user_repo: UserRepository,
        session_repo: UserSessionRepository,
    ):
        self.user_repo = user_repo
        self.session_repo = session_repo

    def list_users(self) -> list[ManagedUser]:
        documents = self.user_repo.list_users()
        last_seen_map = self.session_repo.get_last_seen_map([item["id"] for item in documents])
        for item in documents:
            item["lastActiveAt"] = last_seen_map.get(item["id"])
        documents.sort(
            key=lambda item: (
                0 if item.get("role") == "admin" else 1,
                item.get("createdAt", ""),
                item.get("username", ""),
            )
        )
        return [build_managed_user(item) for item in documents]

    def create_user(self, payload: CreateManagedUserRequest) -> ManagedUser:
        username = payload.username.strip()
        if not username:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="用户名不能为空",
            )

        if self.user_repo.get_by_username(username):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="用户名已存在",
            )

        display_name = payload.displayName.strip() if payload.displayName else None
        document = self.user_repo.create_user(
            username=username,
            display_name=display_name,
            password_hash=hash_password(payload.password),
            role="user",
            status="active",
        )
        return build_managed_user(document)

    def update_user_status(
        self, user_id: str, payload: UpdateManagedUserStatusRequest
    ) -> ManagedUser:
        existing = self.user_repo.get_by_id(user_id)
        if not existing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="用户不存在",
            )

        if existing.get("role") == "admin":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="管理员账号状态不可修改",
            )

        updated = self.user_repo.update_status(user_id, payload.status)
        if not updated:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="更新用户状态失败",
            )
        return build_managed_user(updated)

    def reset_password(
        self,
        user_id: str,
        payload: ResetManagedUserPasswordRequest,
    ) -> ManagedUser:
        existing = self.user_repo.get_by_id(user_id)
        if not existing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="用户不存在",
            )

        updated = self.user_repo.update_password_hash(
            user_id,
            hash_password(payload.password),
        )
        if not updated:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="重置密码失败",
            )
        return build_managed_user(updated)
