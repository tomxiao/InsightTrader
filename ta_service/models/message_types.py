from __future__ import annotations

from enum import StrEnum


class MessageType(StrEnum):
    """消息类型枚举 — 前后端通讯契约。

    每种类型对应的 content schema：
    - TEXT:              str（用户输入或系统短提示，纯文本展示）
    - TICKER_RESOLUTION: ResolutionMessageContent（见 models/resolution.py）
    - RESOLUTION_STREAM: str（标的识别过程中的临时流式回复）
    - TASK_STATUS:       {"text": str, "stageId": str | None}
    - SUMMARY_CARD:      {"text": str}（研究结果卡片，markdown 渲染）
    - INSIGHT_REPLY:     str（追问解读回答，markdown 渲染）
    - ERROR:             {"text": str}
    """

    TEXT = "text"
    TICKER_RESOLUTION = "ticker_resolution"
    RESOLUTION_STREAM = "resolution_stream"
    TASK_STATUS = "task_status"
    SUMMARY_CARD = "summary_card"
    INSIGHT_REPLY = "insight_reply"
    ERROR = "error"
