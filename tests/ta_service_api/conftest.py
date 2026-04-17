from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
import sys

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from ta_service.api.deps import (
    get_admin_user_service,
    get_analysis_service,
    get_auth_service,
    get_conversation_service,
    get_current_user,
    get_resolution_service,
)
from ta_service.api.routes.admin_users import router as admin_users_router
from ta_service.api.routes.analysis import router as analysis_router
from ta_service.api.routes.auth import router as auth_router
from ta_service.api.routes.conversations import router as conversations_router
from ta_service.models.auth import MobileUser


class FakeAuthService:
    def login(self, payload):
        return {
            "access_token": "token-1",
            "expires_in": 3600,
            "refresh_token": None,
            "user": {
                "id": "user-1",
                "username": payload.username,
                "displayName": "Tester",
                "role": "admin",
            },
        }

    def logout(self, token: str) -> None:
        return None


class FakeAdminUserService:
    def __init__(self) -> None:
        self.user = {
            "id": "managed-1",
            "username": "alice",
            "displayName": "Alice",
            "role": "user",
            "status": "active",
            "lastLoginAt": None,
            "lastActiveAt": None,
            "createdAt": "2026-04-17T08:00:00Z",
            "updatedAt": "2026-04-17T08:00:00Z",
        }

    def list_users(self):
        return [self.user]

    def create_user(self, payload):
        return {
            **self.user,
            "username": payload.username,
            "displayName": payload.displayName,
        }

    def update_user_status(self, user_id: str, payload):
        return {
            **self.user,
            "id": user_id,
            "status": payload.status,
            "updatedAt": "2026-04-17T08:10:00Z",
        }

    def reset_password(self, user_id: str, payload):
        return {
            **self.user,
            "id": user_id,
            "updatedAt": "2026-04-17T08:11:00Z",
        }


class FakeAnalysisService:
    def __init__(self) -> None:
        self.task = {
            "taskId": "task-1",
            "status": "queued",
            "symbol": "AAPL",
            "teamId": "lite",
            "currentStep": "排队中",
            "message": "任务已创建",
            "elapsedTime": 0,
            "remainingTime": None,
        }

    def get_task_status(self, *, task_id: str, user_id: str):
        if task_id == "missing":
            return None
        return {**self.task, "taskId": task_id}

    def create_task(self, *, user_id: str, username: str, payload):
        return {
            **self.task,
            "symbol": payload.ticker,
            "teamId": payload.teamId or "lite",
        }


class FakeConversationService:
    def __init__(self) -> None:
        self.create_result = {
            "id": "conv-1",
            "title": "新会话",
            "status": "idle",
            "updatedAt": "2026-04-17T08:00:00Z",
        }
        self.list_result = [self.create_result]
        self.detail_result = {
            **self.create_result,
            "messages": [],
            "taskProgress": None,
        }
        self.post_result = {
            "messages": [
                {
                    "id": "msg-assistant-1",
                    "role": "assistant",
                    "messageType": "insight_reply",
                    "content": "这是回答",
                    "createdAt": "2026-04-17T08:01:00Z",
                }
            ]
        }
        self.stream_result = [
            {
                "event": "started",
                "userMessage": {
                    "id": "msg-user-1",
                    "role": "user",
                    "messageType": "text",
                    "content": "你好",
                    "createdAt": "2026-04-17T08:01:00Z",
                },
            },
            {"event": "delta", "text": "这是一段"},
            {
                "event": "completed",
                "assistantMessage": {
                    "id": "msg-assistant-1",
                    "role": "assistant",
                    "messageType": "insight_reply",
                    "content": "这是一段完整回答",
                    "createdAt": "2026-04-17T08:01:02Z",
                },
            },
        ]

    def create_conversation(self, *, user_id: str, title: str | None):
        return {**self.create_result, "title": title or self.create_result["title"]}

    def list_conversations(self, *, user_id: str):
        return self.list_result

    def get_conversation(self, *, user_id: str, conversation_id: str):
        if conversation_id == "missing":
            return None
        return {**self.detail_result, "id": conversation_id}

    def delete_conversation(self, *, user_id: str, conversation_id: str) -> None:
        return None

    def post_message(self, *, user_id: str, username: str, conversation_id: str, message: str):
        return self.post_result

    def stream_post_message(
        self, *, user_id: str, username: str, conversation_id: str, message: str
    ) -> Iterator[dict[str, object]]:
        yield from self.stream_result


class FakeResolutionService:
    def __init__(self) -> None:
        self.resolve_result = {
            "resolutionId": "res-1",
            "accepted": None,
            "status": "need_confirm",
            "ticker": "AAPL",
            "name": "Apple Inc.",
            "candidates": [
                {
                    "ticker": "AAPL",
                    "name": "Apple Inc.",
                    "market": "US",
                }
            ],
            "promptMessage": "你想分析的是 Apple Inc.（AAPL）吗？",
            "conversationStatus": "collecting_inputs",
            "messages": [
                {
                    "id": "msg-user-2",
                    "role": "user",
                    "messageType": "text",
                    "content": "苹果",
                    "createdAt": "2026-04-17T08:02:00Z",
                },
                {
                    "id": "msg-resolution-1",
                    "role": "assistant",
                    "messageType": "ticker_resolution",
                    "content": {
                        "text": "你想分析的是 Apple Inc.（AAPL）吗？",
                        "status": "need_confirm",
                        "resolutionId": "res-1",
                        "ticker": "AAPL",
                        "name": "Apple Inc.",
                        "candidates": [
                            {
                                "ticker": "AAPL",
                                "name": "Apple Inc.",
                                "market": "US",
                            }
                        ],
                    },
                    "createdAt": "2026-04-17T08:02:01Z",
                },
            ],
            "analysisPrompt": "苹果",
            "focusPoints": [],
            "taskProgress": None,
        }
        self.confirm_result = {
            **self.resolve_result,
            "accepted": True,
            "status": "resolved",
            "promptMessage": "已为你确认分析标的是 Apple Inc.（AAPL）。",
            "conversationStatus": "analyzing",
            "messages": [
                {
                    "id": "msg-resolution-2",
                    "role": "assistant",
                    "messageType": "ticker_resolution",
                    "content": {
                        "text": "已为你确认分析标的是 Apple Inc.（AAPL）。",
                        "status": "resolved",
                        "resolutionId": "res-1",
                        "ticker": "AAPL",
                        "name": "Apple Inc.",
                        "candidates": [],
                    },
                    "createdAt": "2026-04-17T08:02:02Z",
                }
            ],
        }
        self.stream_result = [
            {
                "event": "started",
                "userMessage": {
                    "id": "msg-user-2",
                    "role": "user",
                    "messageType": "text",
                    "content": "苹果",
                    "createdAt": "2026-04-17T08:02:00Z",
                },
            },
            {"event": "progress", "message": "正在识别标的，请稍候…"},
            {"event": "delta", "text": "你想分析的是"},
            {"event": "delta", "text": " Apple Inc.（AAPL）吗？"},
            {"event": "completed", "response": self.resolve_result},
        ]

    def resolve_message(self, *, user_id: str, username: str, conversation_id: str, message: str):
        return self.resolve_result

    def stream_resolve_message(
        self, *, user_id: str, username: str, conversation_id: str, message: str
    ) -> Iterator[dict[str, object]]:
        yield from self.stream_result

    def confirm_resolution(self, *, user_id: str, username: str, conversation_id: str, payload):
        return self.confirm_result


@pytest.fixture
def fake_auth_service() -> FakeAuthService:
    return FakeAuthService()


@pytest.fixture
def fake_admin_user_service() -> FakeAdminUserService:
    return FakeAdminUserService()


@pytest.fixture
def fake_analysis_service() -> FakeAnalysisService:
    return FakeAnalysisService()


@pytest.fixture
def fake_conversation_service() -> FakeConversationService:
    return FakeConversationService()


@pytest.fixture
def fake_resolution_service() -> FakeResolutionService:
    return FakeResolutionService()


@pytest.fixture
def api_client(
    fake_auth_service: FakeAuthService,
    fake_admin_user_service: FakeAdminUserService,
    fake_analysis_service: FakeAnalysisService,
    fake_conversation_service: FakeConversationService,
    fake_resolution_service: FakeResolutionService,
):
    app = FastAPI()
    app.include_router(auth_router)
    app.include_router(admin_users_router)
    app.include_router(analysis_router)
    app.include_router(conversations_router)
    app.dependency_overrides[get_current_user] = lambda: MobileUser(
        id="user-1",
        username="tester",
        displayName="Tester",
        role="admin",
    )
    app.dependency_overrides[get_auth_service] = lambda: fake_auth_service
    app.dependency_overrides[get_admin_user_service] = lambda: fake_admin_user_service
    app.dependency_overrides[get_analysis_service] = lambda: fake_analysis_service
    app.dependency_overrides[get_conversation_service] = lambda: fake_conversation_service
    app.dependency_overrides[get_resolution_service] = lambda: fake_resolution_service

    with TestClient(app) as client:
        yield client
