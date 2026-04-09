from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from ta_service.db.mongo import MongoCollections


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class TaskEventRepository:
    def __init__(self, database):
        self.collection = database[MongoCollections().task_events]

    def create(
        self,
        *,
        task_id: str,
        event_type: str,
        stage_id: str | None = None,
        payload: dict | None = None,
    ) -> dict:
        document = {
            "id": str(uuid4()),
            "taskId": task_id,
            "eventType": event_type,
            "stageId": stage_id,
            "payload": payload or {},
            "createdAt": _utc_now_iso(),
        }
        self.collection.insert_one(document)
        return document
