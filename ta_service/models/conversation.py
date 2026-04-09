from __future__ import annotations

from pydantic import BaseModel, Field


class ConversationSummary(BaseModel):
    id: str
    title: str
    status: str
    updatedAt: str
    lastReportId: str | None = None
    currentTaskId: str | None = None


class ConversationMessage(BaseModel):
    id: str
    role: str
    messageType: str = Field(default="text")
    content: dict | str
    createdAt: str


class ConversationDetail(ConversationSummary):
    messages: list[ConversationMessage] = Field(default_factory=list)


class CreateConversationRequest(BaseModel):
    title: str | None = None


class PostConversationMessageRequest(BaseModel):
    message: str


class PostConversationMessageResponse(BaseModel):
    messages: list[ConversationMessage] = Field(default_factory=list)
    reportId: str | None = None
