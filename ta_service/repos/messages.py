from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from ta_service.db.mongo import MongoCollections
from ta_service.models.message_types import MessageType


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class MessageRepository:
    def __init__(self, database):
        self.collection = database[MongoCollections().messages]

    def delete_for_conversation(self, *, conversation_id: str) -> None:
        self.collection.delete_many({"conversationId": conversation_id})

    def list_for_conversation(self, conversation_id: str) -> list[dict]:
        cursor = self.collection.find({"conversationId": conversation_id}, {"_id": 0}).sort(
            "createdAt", 1
        )
        return list(cursor)

    def create(
        self,
        *,
        conversation_id: str,
        role: str,
        content: dict | str,
        message_type: MessageType = MessageType.TEXT,
    ) -> dict:
        document = {
            "id": str(uuid4()),
            "conversationId": conversation_id,
            "role": role,
            "messageType": message_type,
            "content": content,
            "createdAt": _utc_now_iso(),
        }
        self.collection.insert_one(document)
        return document
