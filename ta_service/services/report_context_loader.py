from __future__ import annotations

import logging
from pathlib import Path

from ta_service.config.settings import Settings
from ta_service.teams import (
    DEFAULT_TEAM_ID,
    ReportSectionSpec,
    get_section_labels,
    get_section_specs,
    normalize_team_id,
)

logger = logging.getLogger(__name__)

_SECTION_LABELS: dict[str, str] = get_section_labels()


class ReportContextLoader:
    """从磁盘加载各 Agent 报告文件，返回按优先级截断的结构化上下文。"""

    def __init__(self, *, settings: Settings):
        self.settings = settings

    def list_available_sections(
        self,
        *,
        trace_dir: str | None,
        team_id: str | None = DEFAULT_TEAM_ID,
    ) -> list[str]:
        """返回当前报告目录中实际存在的章节名列表。"""
        if not trace_dir:
            return []
        report_dir = self._resolve_report_dir(trace_dir)
        if not report_dir.exists():
            return []
        available = []
        for section in self._get_section_specs(team_id):
            if (report_dir / section.relative_path).exists():
                available.append(section.key)
        return available

    def load_single_section(
        self,
        *,
        trace_dir: str | None,
        section: str,
        team_id: str | None = DEFAULT_TEAM_ID,
    ) -> str | None:
        """按需读取单个章节内容，供 ReportInsightAgent 工具调用使用。

        Returns:
            章节文本内容；章节不存在或读取失败时返回 None。
        """
        if not trace_dir:
            return None
        section_spec = self._get_section_spec(team_id=team_id, section=section)
        if section_spec is None:
            logger.warning("report_context_loader: unknown section=%s", section)
            return None
        report_dir = self._resolve_report_dir(trace_dir)
        file_path = report_dir / section_spec.relative_path
        if not file_path.exists():
            return None
        try:
            content = file_path.read_text(encoding="utf-8").strip()
            logger.debug(
                "report_context_loader: loaded single section=%s chars=%d", section, len(content)
            )
            return content or None
        except OSError as exc:
            logger.warning(
                "report_context_loader: failed to read section=%s error=%s", section, exc
            )
            return None

    def load(
        self,
        *,
        trace_dir: str | None,
        team_id: str | None = DEFAULT_TEAM_ID,
    ) -> dict[str, str]:
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

        for section in self._get_section_specs(team_id):
            if total_chars >= char_limit:
                break

            file_path = report_dir / section.relative_path
            if not file_path.exists():
                continue

            try:
                content = file_path.read_text(encoding="utf-8").strip()
            except OSError as exc:
                logger.warning(
                    "report_context_loader: failed to read file=%s error=%s", file_path, exc
                )
                continue

            if not content:
                continue

            remaining = char_limit - total_chars
            if len(content) > remaining:
                content = content[:remaining] + "\n…（内容已截断）"

            sections[section.key] = content
            total_chars += len(content)
            logger.debug(
                "report_context_loader: loaded section=%s chars=%d", section.key, len(content)
            )

        logger.info(
            "report_context_loader: loaded sections=%s total_chars=%d trace_dir=%s",
            list(sections.keys()),
            total_chars,
            trace_dir,
        )
        return sections

    def _resolve_report_dir(self, trace_dir: str) -> Path:
        """将 traceDir 绝对路径转换为对应的报告目录。

        trace_dir 是 results/analysis/... 的绝对路径，报告文件写入的是
        reports_root / trace_dir.name，因此取最后一级目录名拼接。
        """
        trace_path = Path(trace_dir)
        return self.settings.reports_root / trace_path.name

    def _get_section_specs(self, team_id: str | None) -> tuple[ReportSectionSpec, ...]:
        return get_section_specs(team_id)

    def _get_section_spec(
        self, *, team_id: str | None, section: str
    ) -> ReportSectionSpec | None:
        normalized = normalize_team_id(team_id)
        for item in self._get_section_specs(normalized):
            if item.key == section:
                return item
        return None


def build_report_prompt_text(
    sections: dict[str, str], *, team_id: str | None = DEFAULT_TEAM_ID
) -> str:
    """将章节字典拼接为 prompt 中使用的结构化文本块。"""
    if not sections:
        return ""

    parts: list[str] = []
    labels = get_section_labels(team_id)
    for key, content in sections.items():
        label = labels.get(key, key)
        parts.append(f"[{label}]\n{content}")

    return "\n\n".join(parts)
