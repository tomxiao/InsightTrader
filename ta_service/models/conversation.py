from __future__ import annotations

from pydantic import BaseModel, Field

from ta_service.models.message_types import MessageType


class TaskProgress(BaseModel):
    """分析任务进度信息，仅在会话状态为 analyzing 时由后端填充。"""

    currentStep: str | None = None
    message: str | None = None
    elapsedTime: int | None = None
    remainingTime: int | None = None


class ConversationSummary(BaseModel):
    id: str
    title: str
    status: str
    updatedAt: str


class ConversationMessage(BaseModel):
    id: str
    role: str
    messageType: MessageType = Field(default=MessageType.TEXT)
    content: dict | str
    createdAt: str


class ConversationDetail(ConversationSummary):
    messages: list[ConversationMessage] = Field(default_factory=list)
    taskProgress: TaskProgress | None = None


class CreateConversationRequest(BaseModel):
    title: str | None = None


class PostConversationMessageRequest(BaseModel):
    message: str


class PostConversationMessageResponse(BaseModel):
    messages: list[ConversationMessage] = Field(default_factory=list)
