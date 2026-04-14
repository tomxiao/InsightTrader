from __future__ import annotations

import logging
from pathlib import Path

from ta_service.config.settings import Settings

logger = logging.getLogger(__name__)

# 按重要性排列的章节读取顺序（优先保留靠前的章节）
_SECTION_FILES: list[tuple[str, str]] = [
    ("decision",      "5_portfolio/decision.md"),
    ("trading_plan",  "3_trading/trader.md"),
    ("fundamentals",  "1_analysts/fundamentals.md"),
    ("market",        "1_analysts/market.md"),
    ("news",          "1_analysts/news.md"),
    ("sentiment",     "1_analysts/sentiment.md"),
    ("bull_research", "2_research/bull.md"),
    ("bear_research", "2_research/bear.md"),
    ("research_mgr",  "2_research/manager.md"),
    ("risk_aggr",     "4_risk/aggressive.md"),
    ("risk_cons",     "4_risk/conservative.md"),
    ("risk_neutral",  "4_risk/neutral.md"),
]

_SECTION_LABELS: dict[str, str] = {
    "decision":      "最终投资决策",
    "trading_plan":  "交易计划",
    "fundamentals":  "基本面分析",
    "market":        "市场与技术分析",
    "news":          "新闻事件分析",
    "sentiment":     "社交情绪分析",
    "bull_research": "多方研究",
    "bear_research": "空方研究",
    "research_mgr":  "研究经理结论",
    "risk_aggr":     "激进风险评估",
    "risk_cons":     "保守风险评估",
    "risk_neutral":  "中立风险评估",
}


class ReportContextLoader:
    """从磁盘加载各 Agent 报告文件，返回按优先级截断的结构化上下文。"""

    def __init__(self, *, settings: Settings):
        self.settings = settings

    def list_available_sections(self, *, trace_dir: str | None) -> list[str]:
        """返回当前报告目录中实际存在的章节名列表。"""
        if not trace_dir:
            return []
        report_dir = self._resolve_report_dir(trace_dir)
        if not report_dir.exists():
            return []
        available = []
        for section_key, relative_path in _SECTION_FILES:
            if (report_dir / relative_path).exists():
                available.append(section_key)
        return available

    def load_single_section(self, *, trace_dir: str | None, section: str) -> str | None:
        """按需读取单个章节内容，供 ReportInsightAgent 工具调用使用。

        Returns:
            章节文本内容；章节不存在或读取失败时返回 None。
        """
        if not trace_dir:
            return None
        relative_path = dict(_SECTION_FILES).get(section)
        if not relative_path:
            logger.warning("report_context_loader: unknown section=%s", section)
            return None
        report_dir = self._resolve_report_dir(trace_dir)
        file_path = report_dir / relative_path
        if not file_path.exists():
            return None
        try:
            content = file_path.read_text(encoding="utf-8").strip()
            logger.debug("report_context_loader: loaded single section=%s chars=%d", section, len(content))
            return content or None
        except OSError as exc:
            logger.warning("report_context_loader: failed to read section=%s error=%s", section, exc)
            return None

    def load(self, *, trace_dir: str | None) -> dict[str, str]:
        """
        根据 trace_dir 加载报告章节。

        Args:
            trace_dir: analysis_tasks.traceDir 字段值（绝对路径字符串）。
                       为 None 时返回空字典，调用方应降级到摘要文本。

        Returns:
            dict[str, str]: 章节名 → 内容。按优先级截断至 settings.followup_report_context_chars。
        """
        if not trace_dir:
            logger.debug("report_context_loader: traceDir is None, skipping disk load")
            return {}

        report_dir = self._resolve_report_dir(trace_dir)
        if not report_dir.exists():
            logger.warning("report_context_loader: report_dir not found path=%s", report_dir)
            return {}

        sections: dict[str, str] = {}
        total_chars = 0
        char_limit = self.settings.followup_report_context_chars

        for section_key, relative_path in _SECTION_FILES:
            if total_chars >= char_limit:
                break

            file_path = report_dir / relative_path
            if not file_path.exists():
                continue

            try:
                content = file_path.read_text(encoding="utf-8").strip()
            except OSError as exc:
                logger.warning("report_context_loader: failed to read file=%s error=%s", file_path, exc)
                continue

            if not content:
                continue

            remaining = char_limit - total_chars
            if len(content) > remaining:
                content = content[:remaining] + "\n…（内容已截断）"

            sections[section_key] = content
            total_chars += len(content)
            logger.debug("report_context_loader: loaded section=%s chars=%d", section_key, len(content))

        logger.info(
            "report_context_loader: loaded sections=%s total_chars=%d trace_dir=%s",
            list(sections.keys()),
            total_chars,
            trace_dir,
        )
        return sections

    def _resolve_report_dir(self, trace_dir: str) -> Path:
        """将 traceDir 绝对路径转换为对应的报告目录。

        trace_dir 是 results/ta_service/... 的绝对路径，报告文件写入的是
        reports_root / trace_dir.name，因此取最后一级目录名拼接。
        """
        trace_path = Path(trace_dir)
        return self.settings.reports_root / trace_path.name


def build_report_prompt_text(sections: dict[str, str]) -> str:
    """将章节字典拼接为 prompt 中使用的结构化文本块。"""
    if not sections:
        return ""

    parts: list[str] = []
    for key, content in sections.items():
        label = _SECTION_LABELS.get(key, key)
        parts.append(f"[{label}]\n{content}")

    return "\n\n".join(parts)
