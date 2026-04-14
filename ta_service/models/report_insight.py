from __future__ import annotations

from pydantic import BaseModel, Field


class ReportInsightContext(BaseModel):
    """传递给 ReportInsightAgent 的输入上下文。"""

    conversation_id: str = ""
    question: str
    ticker: str
    trade_date: str

    trace_dir: str | None = None
    """报告根目录绝对路径，供 Agent 按需调用工具读取章节文件。"""

    available_sections: list[str] = Field(default_factory=list)
    """当前报告可用的章节名列表，传给 LLM 作为工具调用的候选范围。"""

    report_sections: dict[str, str] = Field(default_factory=dict)
    """降级专用：无磁盘报告时使用 SUMMARY_CARD 文本填充此字段。正常路径为空。"""

    conversation_history: list[dict] = Field(default_factory=list)
    """最近 N 轮对话，格式为 [{"role": "user"/"assistant", "content": "..."}]"""


class ReportInsightResult(BaseModel):
    """ReportInsightAgent 的输出结果。"""

    answer: str
    is_answerable: bool
    """报告材料中是否有足够依据支撑回答。"""
    source_sections: list[str] = Field(default_factory=list)
    """本次回答引用了哪些章节（调试/审计用）。"""
