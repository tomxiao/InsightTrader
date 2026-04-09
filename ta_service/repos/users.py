from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from ta_service.db.mongo import MongoCollections


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class UserRepository:
    def __init__(self, database):
        self.collection = database[MongoCollections().users]

    def ensure_dev_user(self, username: str) -> dict:
        document = self.collection.find_one({"username": username})
        if document:
            return document

        user = {
            "id": str(uuid4()),
            "username": username,
            "displayName": username,
            "createdAt": _utc_now_iso(),
            "updatedAt": _utc_now_iso(),
        }
        self.collection.insert_one(user)
        return user

    def get_by_id(self, user_id: str) -> dict | None:
        return self.collection.find_one({"id": user_id}, {"_id": 0})

    def get_by_username(self, username: str) -> dict | None:
        return self.collection.find_one({"username": username}, {"_id": 0})
