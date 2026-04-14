from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from ta_service.models.conversation import ConversationMessage, TaskProgress

ResolutionStatus = Literal[
    "collect_more",
    "need_confirm",
    "need_disambiguation",
    "resolved",
    "unsupported",
    "failed",
]

ResolutionAction = Literal["confirm", "select", "restart"]


class ResolutionCandidate(BaseModel):
    ticker: str
    name: str
    market: str | None = None
    exchange: str | None = None
    aliases: list[str] = Field(default_factory=list)
    score: float | None = None
    assetType: str = "stock"
    isActive: bool | None = True


class PendingResolutionSnapshot(BaseModel):
    resolutionId: str
    status: Literal["collect_more", "need_confirm", "need_disambiguation"]
    round: int
    originalMessage: str
    analysisPrompt: str
    assistantReply: str
    candidates: list[ResolutionCandidate] = Field(default_factory=list)
    resolvedStock: ResolutionCandidate | None = None
    focusPoints: list[str] = Field(default_factory=list)
    updatedAt: datetime


class ResolutionRequest(BaseModel):
    message: str

    @field_validator("message")
    @classmethod
    def validate_message(cls, value: str) -> str:
        message = value.strip()
        if not message:
            raise ValueError("message cannot be empty")
        return message


class ResolutionConfirmRequest(BaseModel):
    action: ResolutionAction
    resolutionId: str
    ticker: str | None = None

    @field_validator("resolutionId")
    @classmethod
    def validate_resolution_id(cls, value: str) -> str:
        resolution_id = value.strip()
        if not resolution_id:
            raise ValueError("resolutionId cannot be empty")
        return resolution_id

    @model_validator(mode="after")
    def validate_action_payload(self):
        if self.action == "select" and not (self.ticker or "").strip():
            raise ValueError("ticker is required when action is select")
        return self


class ResolutionResponse(BaseModel):
    resolutionId: str | None = None
    accepted: bool | None = None
    status: ResolutionStatus
    ticker: str | None = None
    name: str | None = None
    candidates: list[ResolutionCandidate] = Field(default_factory=list)
    promptMessage: str
    conversationStatus: str
    messages: list[ConversationMessage] = Field(default_factory=list)
    analysisPrompt: str | None = None
    focusPoints: list[str] = Field(default_factory=list)
    taskProgress: TaskProgress | None = None


class AgentResolutionResult(BaseModel):
    status: ResolutionStatus
    assistantReply: str
    stock: ResolutionCandidate | None = None
    candidates: list[ResolutionCandidate] = Field(default_factory=list)
    focusPoints: list[str] = Field(default_factory=list)
    shouldCreateAnalysisTask: bool = False
    terminate: bool = False


class ResolutionAgentContext(BaseModel):
    currentMessage: str
    currentRound: int
    priorResolutionSummary: str = ""
    analysisPrompt: str = ""
    pendingResolution: PendingResolutionSnapshot | None = None
