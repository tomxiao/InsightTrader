from __future__ import annotations

from dataclasses import dataclass

from redis import Redis

from ta_service.config.settings import Settings


@dataclass(frozen=True)
class AnalysisJob:
    taskId: str
    userId: str
    conversationId: str
    ticker: str
    tradeDate: str
    teamId: str | None = None
    prompt: str | None = None
    selectedAnalysts: list[str] | None = None


class AnalysisJobQueue:
    def __init__(self, redis_client: Redis, settings: Settings):
        self.redis = redis_client
        self.settings = settings

    def get_task_job(self, task_repo, task_id: str) -> AnalysisJob | None:
        document = task_repo.get_by_task_id(task_id)
        if not document:
            return None
        return AnalysisJob(
            taskId=document["taskId"],
            userId=document["userId"],
            conversationId=document["conversationId"],
            ticker=document["symbol"],
            tradeDate=document["tradeDate"],
            teamId=document.get("teamId"),
            prompt=document.get("prompt"),
            selectedAnalysts=document.get("selectedAnalysts"),
        )
