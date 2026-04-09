from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from ta_service.db.mongo import MongoCollections


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class ReportRepository:
    def __init__(self, database):
        self.collection = database[MongoCollections().reports]

    def create(
        self,
        *,
        task_id: str,
        conversation_id: str,
        user_id: str,
        stock_symbol: str,
        title: str,
        summary: str | None,
        executive_summary: str | None,
        content_markdown: str | None,
        trace_dir: str | None,
    ) -> dict:
        document = {
            "id": str(uuid4()),
            "taskId": task_id,
            "conversationId": conversation_id,
            "userId": user_id,
            "stockSymbol": stock_symbol,
            "title": title,
            "summary": summary,
            "executiveSummary": executive_summary,
            "contentMarkdown": content_markdown,
            "traceDir": trace_dir,
            "createdAt": _utc_now_iso(),
        }
        self.collection.insert_one(document)
        return document

    def get_for_user(self, *, report_id: str, user_id: str) -> dict | None:
        return self.collection.find_one({"id": report_id, "userId": user_id}, {"_id": 0})

    def get_by_id(self, report_id: str) -> dict | None:
        return self.collection.find_one({"id": report_id}, {"_id": 0})

    def get_latest_for_conversation(self, *, conversation_id: str, user_id: str) -> dict | None:
        return self.collection.find_one(
            {"conversationId": conversation_id, "userId": user_id},
            {"_id": 0},
            sort=[("createdAt", -1)],
        )
