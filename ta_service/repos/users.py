from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from pymongo import ReturnDocument

from ta_service.db.mongo import MongoCollections


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class UserRepository:
    def __init__(self, database):
        self.collection = database[MongoCollections().users]

    def create_user(
        self,
        *,
        username: str,
        display_name: str | None,
        password_hash: str,
        role: str = "user",
        status: str = "active",
    ) -> dict:
        now = _utc_now_iso()
        user = {
            "id": str(uuid4()),
            "username": username,
            "displayName": display_name or username,
            "passwordHash": password_hash,
            "role": role,
            "status": status,
            "lastLoginAt": None,
            "createdAt": now,
            "updatedAt": now,
        }
        self.collection.insert_one(user)
        return user

    def get_by_id(self, user_id: str) -> dict | None:
        return self.collection.find_one({"id": user_id}, {"_id": 0})

    def get_by_username(self, username: str) -> dict | None:
        return self.collection.find_one({"username": username}, {"_id": 0})

    def list_users(self) -> list[dict]:
        cursor = self.collection.find(
            {},
            {
                "_id": 0,
                "passwordHash": 0,
            },
        ).sort("createdAt", 1)
        return list(cursor)

    def update_status(self, user_id: str, status: str) -> dict | None:
        now = _utc_now_iso()
        return self.collection.find_one_and_update(
            {"id": user_id},
            {"$set": {"status": status, "updatedAt": now}},
            projection={"_id": 0, "passwordHash": 0},
            return_document=ReturnDocument.AFTER,
        )

    def update_password_hash(self, user_id: str, password_hash: str) -> dict | None:
        now = _utc_now_iso()
        return self.collection.find_one_and_update(
            {"id": user_id},
            {"$set": {"passwordHash": password_hash, "updatedAt": now}},
            projection={"_id": 0, "passwordHash": 0},
            return_document=ReturnDocument.AFTER,
        )

    def update_last_login(self, user_id: str) -> None:
        now = _utc_now_iso()
        self.collection.update_one(
            {"id": user_id},
            {"$set": {"lastLoginAt": now, "updatedAt": now}},
        )
