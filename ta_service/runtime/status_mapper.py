from __future__ import annotations

from datetime import datetime, timezone

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

NODE_LABELS = {
    "Market Analyst": "市场分析师正在获取数据",
    "Social Media Analyst": "社交媒体分析师正在获取数据",
    "News Analyst": "新闻分析师正在获取数据",
    "Fundamentals Analyst": "基本面分析师正在获取数据",
    "Bull Researcher": "多方研究员正在分析",
    "Bear Researcher": "空方研究员正在分析",
    "Research Manager": "研究经理正在汇总结论",
    "Trader": "交易员正在制定计划",
    "Aggressive Analyst": "激进分析师正在评估风险",
    "Conservative Analyst": "保守分析师正在评估风险",
    "Neutral Analyst": "中立分析师正在评估风险",
    "Portfolio Manager": "投资组合经理正在做最终决策",
}


def normalize_mobile_status(status: str) -> str:
    return MOBILE_STATUS_MAP.get(status, status)


def resolve_stage_message(stage_id: str | None) -> str | None:
    if not stage_id:
        return None
    return STAGE_LABELS.get(stage_id, stage_id)


def resolve_node_message(node_id: str | None) -> str | None:
    if not node_id:
        return None
    return NODE_LABELS.get(node_id)


def _parse_iso_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def resolve_elapsed_time(document: dict) -> int | None:
    """动态计算任务已用时间。running/pending 状态时用 now-createdAt 推算，其余直接返回字段值。"""
    status = normalize_mobile_status(document["status"])
    explicit_elapsed = document.get("elapsedTime")
    if explicit_elapsed not in (None, 0):
        return explicit_elapsed

    if status not in {"pending", "running"}:
        return explicit_elapsed

    created_at = _parse_iso_datetime(document.get("createdAt"))
    if not created_at:
        return explicit_elapsed

    now = datetime.now(timezone.utc)
    return max(int((now - created_at).total_seconds()), 0)


def resolve_remaining_time(document: dict, elapsed_time: int | None) -> int | None:
    """基于 420 秒估算总时长，推算预计剩余时间。"""
    status = normalize_mobile_status(document["status"])
    explicit_remaining = document.get("remainingTime")
    if explicit_remaining is not None:
        return explicit_remaining
    if status not in {"pending", "running"}:
        return explicit_remaining

    estimated_total = 420
    if elapsed_time is None:
        return estimated_total
    return max(estimated_total - elapsed_time, 0)


# 保持向后兼容的私有别名
_resolve_elapsed_time = resolve_elapsed_time
_resolve_remaining_time = resolve_remaining_time


def build_task_status_response(document: dict) -> AnalysisTaskStatusResponse:
    elapsed_time = resolve_elapsed_time(document)
    return AnalysisTaskStatusResponse(
        taskId=document["taskId"],
        status=normalize_mobile_status(document["status"]),
        symbol=document.get("symbol"),
        currentStep=document.get("currentStep") or resolve_stage_message(document.get("stageId")),
        message=document.get("message") or resolve_stage_message(document.get("stageId")),
        elapsedTime=elapsed_time,
        remainingTime=resolve_remaining_time(document, elapsed_time),
        reportId=document.get("reportId"),
    )
