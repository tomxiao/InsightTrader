from __future__ import annotations

from ta_service.models.analysis import AnalysisTaskStatusResponse

MOBILE_STATUS_MAP = {
    "queued": "pending",
    "pending": "pending",
    "processing": "running",
    "running": "running",
    "completed": "completed",
    "failed": "failed",
    "cancelled": "failed",
}

STAGE_LABELS = {
    "analysts.market": "正在获取市场与技术数据",
    "analysts.social": "正在分析社交与情绪信号",
    "analysts.news": "正在整理新闻与事件影响",
    "analysts.fundamentals": "正在分析基本面与财务数据",
    "research.debate": "正在生成多智能体研究结论",
    "trader.plan": "正在整理交易计划",
    "risk.debate": "正在进行风险辩论",
    "portfolio.decision": "正在生成最终决策",
}


def normalize_mobile_status(status: str) -> str:
    return MOBILE_STATUS_MAP.get(status, status)


def resolve_stage_message(stage_id: str | None) -> str | None:
    if not stage_id:
        return None
    return STAGE_LABELS.get(stage_id, stage_id)


def build_task_status_response(document: dict) -> AnalysisTaskStatusResponse:
    return AnalysisTaskStatusResponse(
        taskId=document["taskId"],
        status=normalize_mobile_status(document["status"]),
        symbol=document.get("symbol"),
        currentStep=document.get("currentStep") or resolve_stage_message(document.get("stageId")),
        message=document.get("message") or resolve_stage_message(document.get("stageId")),
        elapsedTime=document.get("elapsedTime"),
        remainingTime=document.get("remainingTime"),
        reportId=document.get("reportId"),
    )
