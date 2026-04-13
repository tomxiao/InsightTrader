from __future__ import annotations

from pydantic import BaseModel


class ReportDetailResponse(BaseModel):
    id: str
    stockSymbol: str
    title: str | None = None
    summary: str | None = None
    executiveSummary: str | None = None
    contentMarkdown: str | None = None
    reportDir: str | None = None
    createdAt: str | None = None
