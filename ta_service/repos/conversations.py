from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from ta_service.db.mongo import MongoCollections


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class ConversationRepository:
    def __init__(self, database):
        self.collection = database[MongoCollections().conversations]

    def create(self, *, user_id: str, title: str) -> dict:
        now = _utc_now_iso()
        document = {
            "id": str(uuid4()),
            "userId": user_id,
            "title": title,
            "status": "idle",
            "lastReportId": None,
            "currentTaskId": None,
            "createdAt": now,
            "updatedAt": now,
        }
        self.collection.insert_one(document)
        return document

    def list_for_user(self, user_id: str) -> list[dict]:
        cursor = self.collection.find({"userId": user_id}, {"_id": 0}).sort("updatedAt", -1)
        return list(cursor)

    def get_for_user(self, *, conversation_id: str, user_id: str) -> dict | None:
        return self.collection.find_one({"id": conversation_id, "userId": user_id}, {"_id": 0})

    def update_current_task(
        self,
        *,
        conversation_id: str,
        user_id: str,
        task_id: str | None,
        status: str | None = None,
        report_id: str | None = None,
    ) -> None:
        update = {"updatedAt": _utc_now_iso(), "currentTaskId": task_id}
        if status is not None:
            update["status"] = status
        if report_id is not None:
            update["lastReportId"] = report_id
        self.collection.update_one(
            {"id": conversation_id, "userId": user_id},
            {"$set": update},
        )
