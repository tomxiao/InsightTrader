from __future__ import annotations

from dataclasses import dataclass

from pymongo import MongoClient
from pymongo.database import Database

from ta_service.config.settings import Settings


@dataclass(frozen=True)
class MongoCollections:
    users: str = "users"
    conversations: str = "conversations"
    messages: str = "messages"
    analysis_tasks: str = "analysis_tasks"
    task_events: str = "task_events"
    reports: str = "reports"


def create_mongo_client(settings: Settings) -> MongoClient:
    client = MongoClient(settings.mongo_uri)
    client.admin.command("ping")
    return client


def get_database(client: MongoClient, settings: Settings) -> Database:
    return client[settings.mongo_db_name]
