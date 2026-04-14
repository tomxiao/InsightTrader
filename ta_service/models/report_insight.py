from __future__ import annotations

from pydantic import BaseModel, Field


class ReportInsightContext(BaseModel):
    """传递给 ReportInsightAgent 的输入上下文。"""

    question: str
    ticker: str
    trade_date: str
    report_sections: dict[str, str] = Field(default_factory=dict)
    """按章节名索引的报告内容，如 {"decision": "...", "market": "..."}"""
    conversation_history: list[dict] = Field(default_factory=list)
    """最近 N 轮对话，格式为 [{"role": "user"/"assistant", "content": "..."}]"""


class ReportInsightResult(BaseModel):
    """ReportInsightAgent 的输出结果。"""

    answer: str
    is_answerable: bool
    """报告材料中是否有足够依据支撑回答。"""
    source_sections: list[str] = Field(default_factory=list)
    """本次回答引用了哪些章节（调试/审计用）。"""
