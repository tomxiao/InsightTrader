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
            "pendingResolution": None,
            "confirmedStock": None,
            "confirmedAnalysisPrompt": None,
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

    def update_metadata(
        self,
        *,
        conversation_id: str,
        user_id: str,
        title: str | None = None,
        status: str | None = None,
    ) -> None:
        update = {"updatedAt": _utc_now_iso()}
        if title is not None:
            update["title"] = title
        if status is not None:
            update["status"] = status
        self.collection.update_one(
            {"id": conversation_id, "userId": user_id},
            {"$set": update},
        )

    def delete(self, *, conversation_id: str, user_id: str) -> bool:
        result = self.collection.delete_one({"id": conversation_id, "userId": user_id})
        return result.deleted_count > 0

    def update_resolution_state(
        self,
        *,
        conversation_id: str,
        user_id: str,
        status: str,
        pending_resolution: dict | None,
        confirmed_stock: dict | None = None,
        confirmed_analysis_prompt: str | None = None,
    ) -> None:
        update = {
            "status": status,
            "pendingResolution": pending_resolution,
            "confirmedStock": confirmed_stock,
            "confirmedAnalysisPrompt": confirmed_analysis_prompt,
            "updatedAt": _utc_now_iso(),
        }
        self.collection.update_one(
            {"id": conversation_id, "userId": user_id},
            {"$set": update},
        )
