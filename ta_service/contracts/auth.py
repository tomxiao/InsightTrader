from __future__ import annotations

from ta_service.models.auth import LoginResponse, MobileUser


def build_mobile_user(document: dict) -> MobileUser:
    return MobileUser(
        id=document["id"],
        username=document["username"],
        displayName=document.get("displayName"),
    )


def build_login_response(document: dict, access_token: str) -> LoginResponse:
    return LoginResponse(access_token=access_token, user=build_mobile_user(document))
