from __future__ import annotations

from pydantic import BaseModel


class AnalysisTaskStatusResponse(BaseModel):
    taskId: str
    status: str
    symbol: str | None = None
    teamId: str | None = None
    currentStep: str | None = None
    message: str | None = None
    elapsedTime: int | None = None
    remainingTime: int | None = None


class CreateAnalysisTaskRequest(BaseModel):
    conversationId: str
    ticker: str
    tradeDate: str
    prompt: str | None = None
    teamId: str | None = None
    selectedAnalysts: list[str] | None = None
