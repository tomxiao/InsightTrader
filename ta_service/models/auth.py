from __future__ import annotations

from pydantic import BaseModel


class MobileUser(BaseModel):
    id: str
    username: str
    displayName: str | None = None


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str | None = None
    user: MobileUser
