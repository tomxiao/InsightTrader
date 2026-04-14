from __future__ import annotations

from ta_service.models.admin_users import ManagedUser


def build_managed_user(document: dict) -> ManagedUser:
    return ManagedUser(
        id=document["id"],
        username=document["username"],
        displayName=document.get("displayName"),
        role=document.get("role", "user"),
        status=document.get("status", "active"),
        lastLoginAt=document.get("lastLoginAt"),
        createdAt=document["createdAt"],
        updatedAt=document["updatedAt"],
    )
