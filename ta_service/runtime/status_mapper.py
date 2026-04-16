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
    "analysts.market": "市场分析师梳理价格走势与技术信号",
    "analysts.social": "情绪分析师整理社交舆情与市场情绪",
    "analysts.news": "新闻分析师整理近期关键事件与新闻影响",
    "analysts.fundamentals": "基本面分析师梳理财务表现、盈利与估值",
    "research.debate": "研究团队汇总多方观点并形成研究结论",
    "trader.plan": "交易分析师生成交易方案与执行思路",
    "risk.debate": "风险团队评估下行风险与仓位约束",
    "portfolio.decision": "投资总监输出最终投资决策",
    "decision.finalize": "轻量团队输出最终投资结论",
}

NODE_LABELS = {
    "Market Analyst": "市场分析师梳理价格走势与技术信号",
    "Social Analyst": "情绪分析师整理社交舆情与市场情绪",
    "Social Media Analyst": "情绪分析师整理社交舆情与市场情绪",
    "News Analyst": "新闻分析师整理近期关键事件",
    "Fundamentals Analyst": "基本面分析师梳理财务表现与估值",
    "Bull Researcher": "研究团队形成看多观点",
    "Bear Researcher": "研究团队形成看空观点",
    "Research Manager": "研究团队汇总讨论结论",
    "Trader": "交易分析师生成交易方案",
    "Aggressive Analyst": "风险团队评估积极情景",
    "Conservative Analyst": "风险团队评估保守情景",
    "Neutral Analyst": "风险团队评估中性情景",
    "Portfolio Manager": "投资总监输出最终结论",
    "Decision Manager": "轻量团队汇总分析并输出结论",
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
    if node_id.startswith("tools_"):
        return "投资团队补充数据与公开信息"
    if node_id.startswith("Msg Clear "):
        return None
    return NODE_LABELS.get(node_id)


def resolve_display_state(document: dict) -> str:
    status = normalize_mobile_status(document["status"])
    if status == "completed":
        return "done"
    if status == "failed":
        return "failed"

    updated_at = _parse_iso_datetime(document.get("updatedAt"))
    if updated_at:
        now = datetime.now(timezone.utc)
        stalled_for = (now - updated_at).total_seconds()
        if stalled_for >= 60:
            return "stalled"

    return "active" if status in {"pending", "running"} else status


def _parse_iso_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def resolve_elapsed_time(document: dict) -> int | None:
    """计算任务已用时间。

    - 运行中（pending/running）：始终用 now-createdAt 动态计算，忽略快照值，
      确保每次轮询都能反映真实耗时，不因 stage 切换间隔而静止。
    - 已结束（completed/failed/cancelled）：直接返回任务完成时写入的精确字段值。
    """
    status = normalize_mobile_status(document["status"])

    if status not in {"pending", "running"}:
        return document.get("elapsedTime")

    created_at = _parse_iso_datetime(document.get("createdAt"))
    if not created_at:
        return document.get("elapsedTime")

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
        teamId=document.get("teamId"),
        currentStep=document.get("currentStep") or resolve_stage_message(document.get("stageId")),
        message=document.get("message") or resolve_stage_message(document.get("stageId")),
        elapsedTime=elapsed_time,
        remainingTime=resolve_remaining_time(document, elapsed_time),
    )
