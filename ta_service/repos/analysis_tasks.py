from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

from ta_service.db.mongo import MongoCollections


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class AnalysisTaskRepository:
    def __init__(self, database):
        self.collection = database[MongoCollections().analysis_tasks]

    def create(
        self,
        *,
        user_id: str,
        conversation_id: str,
        ticker: str,
        trade_date: str,
        prompt: str | None = None,
        selected_analysts: list[str] | None = None,
    ) -> dict:
        now = _utc_now_iso()
        document = {
            "taskId": str(uuid4()),
            "userId": user_id,
            "conversationId": conversation_id,
            "symbol": ticker,
            "tradeDate": trade_date,
            "prompt": prompt,
            "selectedAnalysts": selected_analysts or ["market", "social", "news", "fundamentals"],
            "status": "queued",
            "stageId": None,
            "currentStep": "任务已进入队列",
            "message": "任务已进入队列",
            "elapsedTime": 0,
            "remainingTime": None,
            "runId": None,
            "traceDir": None,
            "createdAt": now,
            "updatedAt": now,
        }
        self.collection.insert_one(document)
        return document

    def get_for_user(self, *, task_id: str, user_id: str) -> dict | None:
        return self.collection.find_one({"taskId": task_id, "userId": user_id}, {"_id": 0})

    def get_by_task_id(self, task_id: str) -> dict | None:
        return self.collection.find_one({"taskId": task_id}, {"_id": 0})

    def get_active_for_user(self, user_id: str, ttl_seconds: int = 7200) -> dict | None:
        cutoff = (datetime.now(timezone.utc) - timedelta(seconds=ttl_seconds)).isoformat()
        return self.collection.find_one(
            {
                "userId": user_id,
                "status": {"$in": ["queued", "pending", "running", "processing"]},
                "updatedAt": {"$gt": cutoff},
            },
            {"_id": 0},
        )

    def update_status(self, task_id: str, **fields) -> None:
        fields["updatedAt"] = _utc_now_iso()
        self.collection.update_one({"taskId": task_id}, {"$set": fields})
