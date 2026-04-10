from __future__ import annotations

from fastapi import APIRouter, Depends

from ta_service.api.deps import get_access_token, get_auth_service, get_current_user
from ta_service.models.auth import LoginRequest, LoginResponse, LogoutResponse, MobileUser
from ta_service.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
def login(
    payload: LoginRequest,
    auth_service: AuthService = Depends(get_auth_service),
) -> LoginResponse:
    return auth_service.login(payload)


@router.get("/me", response_model=MobileUser)
def me(current_user: MobileUser = Depends(get_current_user)) -> MobileUser:
    return current_user


@router.post("/logout", response_model=LogoutResponse)
def logout(
    token: str = Depends(get_access_token),
    auth_service: AuthService = Depends(get_auth_service),
) -> LogoutResponse:
    auth_service.logout(token)
    return LogoutResponse()
