from __future__ import annotations

import json
from dataclasses import asdict, dataclass

from redis import Redis

from ta_service.config.settings import Settings


@dataclass(frozen=True)
class AnalysisJob:
    taskId: str
    userId: str
    conversationId: str
    ticker: str
    tradeDate: str
    prompt: str | None = None
    selectedAnalysts: list[str] | None = None


class AnalysisJobQueue:
    def __init__(self, redis_client: Redis, settings: Settings):
        self.redis = redis_client
        self.settings = settings

    def acquire_user_lock(self, user_id: str) -> bool:
        return bool(
            self.redis.set(
                f"{self.settings.redis_lock_prefix}{user_id}",
                "1",
                ex=self.settings.redis_lock_ttl_seconds,
                nx=True,
            )
        )

    def release_user_lock(self, user_id: str) -> None:
        self.redis.delete(f"{self.settings.redis_lock_prefix}{user_id}")

    def enqueue(self, job: AnalysisJob) -> None:
        self.redis.rpush(self.settings.redis_queue_key, json.dumps(asdict(job), ensure_ascii=False))

    def dequeue(self, timeout_seconds: int = 5) -> AnalysisJob | None:
        item = self.redis.blpop(self.settings.redis_queue_key, timeout=timeout_seconds)
        if not item:
            return None
        _, payload = item
        return AnalysisJob(**json.loads(payload))

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
            prompt=document.get("prompt"),
            selectedAnalysts=document.get("selectedAnalysts"),
        )
