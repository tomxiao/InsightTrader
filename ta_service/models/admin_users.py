from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class ManagedUser(BaseModel):
    id: str
    username: str
    displayName: str | None = None
    role: Literal["user", "admin"]
    status: Literal["active", "disabled"]
    lastLoginAt: str | None = None
    createdAt: str
    updatedAt: str


class CreateManagedUserRequest(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    displayName: str | None = Field(default=None, max_length=64)
    password: str = Field(min_length=8, max_length=128)


class UpdateManagedUserStatusRequest(BaseModel):
    status: Literal["active", "disabled"]


class ResetManagedUserPasswordRequest(BaseModel):
    password: str = Field(min_length=8, max_length=128)
