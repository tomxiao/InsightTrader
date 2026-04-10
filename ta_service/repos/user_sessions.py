from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from ta_service.db.mongo import MongoCollections


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class UserSessionRepository:
    def __init__(self, database):
        self.collection = database[MongoCollections().user_sessions]

    def create(
        self,
        *,
        user_id: str,
        token_hash: str,
        client_type: str,
        ttl_seconds: int,
    ) -> dict:
        now = datetime.now(timezone.utc)
        document = {
            "id": str(uuid4()),
            "userId": user_id,
            "tokenHash": token_hash,
            "clientType": client_type,
            "createdAt": now.isoformat(),
            "expiresAt": (now.timestamp() + ttl_seconds),
            "lastSeenAt": now.isoformat(),
            "revokedAt": None,
        }
        self.collection.insert_one(document)
        return document

    def get_by_token_hash(self, token_hash: str) -> dict | None:
        return self.collection.find_one({"tokenHash": token_hash}, {"_id": 0})

    def get_active_by_token_hash(self, token_hash: str) -> dict | None:
        document = self.get_by_token_hash(token_hash)
        if not document or document.get("revokedAt"):
            return None

        expires_at = document.get("expiresAt")
        if not isinstance(expires_at, (int, float)):
            return None
        if expires_at <= datetime.now(timezone.utc).timestamp():
            return None
        return document

    def touch(self, session_id: str) -> None:
        self.collection.update_one(
            {"id": session_id},
            {"$set": {"lastSeenAt": _utc_now_iso()}},
        )

    def revoke_by_token_hash(self, token_hash: str) -> None:
        self.collection.update_one(
            {"tokenHash": token_hash, "revokedAt": None},
            {"$set": {"revokedAt": _utc_now_iso()}},
        )
