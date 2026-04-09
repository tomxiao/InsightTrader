from __future__ import annotations

from redis import Redis

from ta_service.config.settings import Settings


def create_redis_client(settings: Settings) -> Redis:
    client = Redis.from_url(settings.redis_url, decode_responses=True)
    client.ping()
    return client
