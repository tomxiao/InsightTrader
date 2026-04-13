from __future__ import annotations

from enum import StrEnum


class MessageType(StrEnum):
    """消息类型枚举 — 前后端通讯契约。

    每种类型对应的 content schema：
    - TEXT:              str
    - TICKER_RESOLUTION: ResolutionMessageContent（见 models/resolution.py）
    - TASK_STATUS:       {"text": str, "stageId": str | None}
    - SUMMARY_CARD:      {"text": str}
    - REPORT_CARD:       {"reportId": str, "title": str}
    - ERROR:             {"text": str}
    """

    TEXT = "text"
    TICKER_RESOLUTION = "ticker_resolution"
    TASK_STATUS = "task_status"
    SUMMARY_CARD = "summary_card"
    REPORT_CARD = "report_card"
    ERROR = "error"
