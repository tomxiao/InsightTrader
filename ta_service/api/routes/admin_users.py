from __future__ import annotations

from fastapi import APIRouter, Depends

from ta_service.api.deps import get_admin_user_service, require_admin
from ta_service.models.admin_users import (
    CreateManagedUserRequest,
    ManagedUser,
    ResetManagedUserPasswordRequest,
    UpdateManagedUserStatusRequest,
)
from ta_service.models.auth import MobileUser
from ta_service.services.admin_user_service import AdminUserService

router = APIRouter(prefix="/admin/users", tags=["admin-users"])


@router.get("", response_model=list[ManagedUser])
def list_users(
    _: MobileUser = Depends(require_admin),
    admin_user_service: AdminUserService = Depends(get_admin_user_service),
) -> list[ManagedUser]:
    return admin_user_service.list_users()


@router.post("", response_model=ManagedUser, status_code=201)
def create_user(
    payload: CreateManagedUserRequest,
    _: MobileUser = Depends(require_admin),
    admin_user_service: AdminUserService = Depends(get_admin_user_service),
) -> ManagedUser:
    return admin_user_service.create_user(payload)


@router.patch("/{user_id}/status", response_model=ManagedUser)
def update_user_status(
    user_id: str,
    payload: UpdateManagedUserStatusRequest,
    _: MobileUser = Depends(require_admin),
    admin_user_service: AdminUserService = Depends(get_admin_user_service),
) -> ManagedUser:
    return admin_user_service.update_user_status(user_id, payload)


@router.post("/{user_id}/reset-password", response_model=ManagedUser)
def reset_password(
    user_id: str,
    payload: ResetManagedUserPasswordRequest,
    _: MobileUser = Depends(require_admin),
    admin_user_service: AdminUserService = Depends(get_admin_user_service),
) -> ManagedUser:
    return admin_user_service.reset_password(user_id, payload)
