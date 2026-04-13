from __future__ import annotations

from ta_service.models.report import ReportDetailResponse


def build_report_detail(document: dict) -> ReportDetailResponse:
    return ReportDetailResponse(
        id=document["id"],
        stockSymbol=document["stockSymbol"],
        title=document.get("title"),
        summary=document.get("summary"),
        executiveSummary=document.get("executiveSummary"),
        contentMarkdown=document.get("contentMarkdown"),
        reportDir=document.get("reportDir"),
        createdAt=document.get("createdAt"),
    )
