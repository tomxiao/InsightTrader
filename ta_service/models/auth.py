from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class MobileUser(BaseModel):
    id: str
    username: str
    displayName: str | None = None
    role: Literal["user", "admin"]


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    expires_in: int
    refresh_token: str | None = None
    user: MobileUser


class LogoutResponse(BaseModel):
    ok: bool = True
