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

    def update_conversation_state(
        self,
        *,
        conversation_id: str,
        user_id: str,
        status: str,
        title: str | None = None,
        task_id: str | None = None,
        set_task_id: bool = False,
        report_id: str | None = None,
        set_report_id: bool = False,
        pending_resolution: dict | None = None,
        set_pending_resolution: bool = False,
        confirmed_stock: dict | None = None,
        set_confirmed_stock: bool = False,
        confirmed_analysis_prompt: str | None = None,
        set_confirmed_analysis_prompt: bool = False,
    ) -> None:
        """
        会话状态统一写入入口，仅由 ConversationStateMachine 调用。
        使用 set_* 标志区分"显式置 None"与"不修改"。
        """
        update: dict = {"status": status, "updatedAt": _utc_now_iso()}
        if title is not None:
            update["title"] = title
        if set_task_id:
            update["currentTaskId"] = task_id
        if set_report_id:
            update["lastReportId"] = report_id
        if set_pending_resolution:
            update["pendingResolution"] = pending_resolution
        if set_confirmed_stock:
            update["confirmedStock"] = confirmed_stock
        if set_confirmed_analysis_prompt:
            update["confirmedAnalysisPrompt"] = confirmed_analysis_prompt
        self.collection.update_one(
            {"id": conversation_id, "userId": user_id},
            {"$set": update},
        )

    def update_title(self, *, conversation_id: str, user_id: str, title: str) -> None:
        """仅更新会话标题，不触碰状态字段。"""
        self.collection.update_one(
            {"id": conversation_id, "userId": user_id},
            {"$set": {"title": title, "updatedAt": _utc_now_iso()}},
        )

    def delete(self, *, conversation_id: str, user_id: str) -> bool:
        result = self.collection.delete_one({"id": conversation_id, "userId": user_id})
        return result.deleted_count > 0
