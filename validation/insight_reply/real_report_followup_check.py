from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
import re
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ta_service.config.settings import get_settings
from ta_service.models.report_insight import ReportInsightContext
from ta_service.services.insight_reply_router import InsightReplyRouter
from ta_service.services.report_context_loader import ReportContextLoader
from ta_service.services.report_insight_agent import (
    ReportInsightAgent,
    _TOOL_SYSTEM_PROMPT,
    _build_agent_input,
    _build_preloaded_section_block,
    _build_section_menu,
    _build_summary_block,
)

DEFAULT_QUESTIONS = [
    "主要风险是什么？",
    "结论是什么？",
    "现在适合买入吗？",
    "为什么偏谨慎？",
    "最值得关注的一个风险是什么？",
]


@dataclass(frozen=True)
class ResolvedReport:
    trace_dir: Path
    report_dir: Path
    ticker: str
    trade_date: str
    summary_text: str


@dataclass(frozen=True)
class ReplyRun:
    turn_index: int
    question: str
    answer: str
    routing_intent: str
    routing_primary_section: str | None
    routing_fallback_sections: list[str]
    routing_reason: str
    char_count: int
    source_sections: list[str]
    single_screen: bool
    answerable: bool
    e2e_ms: float
    history_turns: int
    system_prompt: str
    llm_input_text: str
    conversation_history: list[dict[str, str]]


def main() -> None:
    args = parse_args()
    settings = get_settings()
    resolved = resolve_report(
        settings=settings,
        trace_dir_arg=args.trace_dir,
        report_dir_arg=args.report_dir,
    )

    questions = args.question or DEFAULT_QUESTIONS
    loader = ReportContextLoader(settings=settings)
    agent = ReportInsightAgent(report_context_loader=loader)
    router = InsightReplyRouter()
    available_sections = loader.list_available_sections(trace_dir=str(resolved.trace_dir))

    print("Real report follow-up check\n")
    print(f"Trace dir : {resolved.trace_dir}")
    print(f"Report dir: {resolved.report_dir}")
    print(f"Ticker    : {resolved.ticker}")
    print(f"Trade date: {resolved.trade_date}")
    print(f"Mode      : {args.mode}")
    print(f"Sections  : {', '.join(available_sections) if available_sections else '(none)'}")
    print(f"Summary   : {resolved.summary_text[:160].strip()}")
    print("\n" + "=" * 72 + "\n")

    runs: list[ReplyRun] = []
    conversation_history: list[dict[str, str]] = []
    for index, question in enumerate(questions, start=1):
        context = ReportInsightContext(
            conversation_id=f"validation-{resolved.report_dir.name}",
            question=question,
            ticker=resolved.ticker,
            trade_date=resolved.trade_date,
            trace_dir=str(resolved.trace_dir),
            available_sections=available_sections,
            summary_text=resolved.summary_text,
            conversation_history=list(conversation_history) if args.mode == "multi_turn" else [],
        )
        started_at = time.perf_counter()
        result = agent.answer(context=context)
        elapsed_ms = (time.perf_counter() - started_at) * 1000
        routing = router.route(
            llm=agent._get_llm(),
            question=question,
            conversation_history=context.conversation_history,
            available_sections=available_sections,
        )
        run = ReplyRun(
            turn_index=index,
            question=question,
            answer=result.answer,
            routing_intent=routing.intent,
            routing_primary_section=routing.primary_section,
            routing_fallback_sections=routing.fallback_sections,
            routing_reason=routing.reason,
            char_count=len(result.answer),
            source_sections=result.source_sections,
            single_screen=len(result.answer) <= 220,
            answerable=result.is_answerable,
            e2e_ms=elapsed_ms,
            history_turns=len(context.conversation_history),
            system_prompt=_build_system_prompt(
                ticker=resolved.ticker,
                trade_date=resolved.trade_date,
                summary_text=resolved.summary_text,
                available_sections=available_sections,
                question=question,
                loader=loader,
                trace_dir=str(resolved.trace_dir),
            ),
            llm_input_text=_build_agent_input(context),
            conversation_history=list(context.conversation_history),
        )
        runs.append(run)
        print(f"[{index}] {question}")
        print(run.answer)
        print(
            f"\nMetrics: chars={run.char_count}, source_sections={run.source_sections}, "
            f"single_screen={run.single_screen}, answerable={run.answerable}, "
            f"e2e_ms={run.e2e_ms:.1f}, history_turns={run.history_turns}"
        )
        print("\n" + "=" * 72 + "\n")
        if args.mode == "multi_turn":
            conversation_history.extend(
                [
                    {"role": "user", "content": question},
                    {"role": "assistant", "content": result.answer},
                ]
            )

    output_path = _resolve_output_path(report_dir=resolved.report_dir)
    output_path.write_text(
        _render_markdown(resolved=resolved, runs=runs, command=_build_command(args, output_path)),
        encoding="utf-8",
    )
    print(f"Markdown written to: {output_path}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run follow-up reply validation against a real local report."
    )
    parser.add_argument(
        "--trace-dir",
        help="Absolute or relative trace dir under results/ta_service. Defaults to latest local run.",
    )
    parser.add_argument(
        "--report-dir",
        help="Absolute or relative report dir under reports. Overrides --trace-dir when provided.",
    )
    parser.add_argument(
        "--question",
        action="append",
        help="Follow-up question to test. Repeatable. Defaults to 5 mobile chat questions.",
    )
    parser.add_argument(
        "--mode",
        choices=("single_turn", "multi_turn"),
        default="multi_turn",
        help="Validation mode. single_turn tests each question independently; multi_turn carries forward conversation history across turns.",
    )
    return parser.parse_args()


def resolve_report(*, settings, trace_dir_arg: str | None, report_dir_arg: str | None) -> ResolvedReport:
    if report_dir_arg:
        report_dir = _resolve_existing_path(Path(report_dir_arg), base=settings.reports_root)
        trace_dir = settings.results_root / report_dir.name
    elif trace_dir_arg:
        trace_dir = _resolve_existing_path(Path(trace_dir_arg), base=settings.results_root)
        report_dir = settings.reports_root / trace_dir.name
    else:
        report_dir = _latest_report_dir(settings.reports_root)
        trace_dir = settings.results_root / report_dir.name

    if not report_dir.exists():
        raise SystemExit(f"Report directory not found: {report_dir}")
    if not trace_dir.exists():
        raise SystemExit(f"Trace directory not found: {trace_dir}")

    ticker, trade_date = _infer_ticker_and_trade_date(report_dir.name)
    summary_text = _extract_summary_text(report_dir)
    return ResolvedReport(
        trace_dir=trace_dir.resolve(),
        report_dir=report_dir.resolve(),
        ticker=ticker,
        trade_date=trade_date,
        summary_text=summary_text,
    )


def _resolve_existing_path(path: Path, *, base: Path) -> Path:
    candidate = path if path.is_absolute() else base / path
    return candidate.resolve()


def _latest_report_dir(reports_root: Path) -> Path:
    candidates = [p for p in reports_root.iterdir() if p.is_dir()]
    if not candidates:
        raise SystemExit(f"No report directories found under: {reports_root}")
    candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return candidates[0]


def _infer_ticker_and_trade_date(directory_name: str) -> tuple[str, str]:
    match = re.match(r"(?P<ticker>.+?)_(?P<year>\d{4})_(?P<month>\d{2})(?P<day>\d{2})_\d{4}$", directory_name)
    if not match:
        return directory_name, ""
    ticker = match.group("ticker")
    trade_date = f"{match.group('year')}-{match.group('month')}-{match.group('day')}"
    return ticker, trade_date


def _extract_summary_text(report_dir: Path) -> str:
    decision_path = report_dir / "5_portfolio" / "decision.md"
    manager_path = report_dir / "2_research" / "manager.md"

    if decision_path.exists():
        decision_text = decision_path.read_text(encoding="utf-8").strip()
        summary = _extract_decision_summary(decision_text)
        if summary:
            return summary
        if decision_text:
            return _trim_text(decision_text, 1200)

    if manager_path.exists():
        manager_text = manager_path.read_text(encoding="utf-8").strip()
        if manager_text:
            return _trim_text(manager_text, 1200)

    return "（未能从本地报告中提取摘要）"


def _extract_decision_summary(text: str) -> str:
    patterns = [
        r"\*\*2\.\s*Executive Summary.*?\*\*\s*(?P<body>.*?)(?:\n\s*\*\*3\.|\Z)",
        r"Executive Summary.*?\n(?P<body>.*?)(?:\n\s*#+\s|\Z)",
        r"执行摘要.*?\n(?P<body>.*?)(?:\n\s*#+\s|\Z)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE | re.DOTALL)
        if match:
            body = match.group("body").strip()
            if body:
                return _trim_text(body, 1200)
    return ""


def _trim_text(text: str, max_chars: int) -> str:
    compact = "\n".join(line.rstrip() for line in text.splitlines()).strip()
    if len(compact) <= max_chars:
        return compact
    return compact[: max_chars - 1].rstrip() + "…"


def _resolve_output_path(*, report_dir: Path) -> Path:
    filename = f"{time.strftime('%Y.%m%d.%H%M')}.md"
    return report_dir.parents[1] / "validation" / "insight_reply" / filename


def _build_command(args: argparse.Namespace, output_path: Path) -> str:
    parts = ["python validation/insight_reply/real_report_followup_check.py"]
    if args.report_dir:
        parts.extend(["--report-dir", args.report_dir])
    if args.trace_dir:
        parts.extend(["--trace-dir", args.trace_dir])
    if args.mode != "multi_turn":
        parts.extend(["--mode", args.mode])
    for question in args.question or []:
        parts.extend(["--question", question])
    return " ".join(parts)


def _render_markdown(*, resolved: ResolvedReport, runs: list[ReplyRun], command: str) -> str:
    lines = [
        "# Real Report Follow-up Check",
        "",
        f"生成时间：{time.strftime('%Y-%m-%d %H:%M:%S')}",
        f"验证脚本：`{command}`",
        "",
        "## 验证上下文",
        "",
        f"- Report dir: `{resolved.report_dir}`",
        f"- Trace dir: `{resolved.trace_dir}`",
        f"- Ticker: `{resolved.ticker}`",
        f"- Trade date: `{resolved.trade_date}`",
        f"- Mode: `{'multi_turn' if any(run.history_turns > 0 for run in runs) else 'single_turn'}`",
        "",
        "### Summary",
        "",
        "```text",
        resolved.summary_text,
        "```",
        "",
        "## 验证对话",
        "",
    ]

    for index, run in enumerate(runs, start=1):
        lines.extend(
            [
                f"### {index}. 用户输入",
                "",
                "```text",
                run.question,
                "```",
                "",
                f"### {index}. LLM Input",
                "",
                "#### Routing",
                "",
                "```text",
                f"intent={run.routing_intent}\n"
                f"primary_section={run.routing_primary_section}\n"
                f"fallback_sections={run.routing_fallback_sections}\n"
                f"reason={run.routing_reason}",
                "```",
                "",
                "#### System Prompt",
                "",
                "```text",
                run.system_prompt,
                "```",
                "",
                "#### Human Input",
                "",
                "```text",
                run.llm_input_text,
                "```",
                "",
                f"### {index}. 助手输出",
                "",
                "```text",
                run.answer,
                "```",
                "",
                "Metrics: "
                f"`chars={run.char_count}`, "
                f"`source_sections={run.source_sections}`, "
                f"`single_screen={run.single_screen}`, "
                f"`answerable={run.answerable}`, "
                f"`e2e_ms={run.e2e_ms:.1f}`, "
                f"`history_turns={run.history_turns}`",
                "",
                "#### Conversation History",
                "",
                "```json",
                _render_history_json(run.conversation_history),
                "```",
                "",
            ]
        )

    return "\n".join(lines).rstrip() + "\n"


def _render_history_json(history: list[dict[str, str]]) -> str:
    if not history:
        return "[]"
    rows = ["["]
    for index, item in enumerate(history):
        suffix = "," if index < len(history) - 1 else ""
        rows.append(
            f'  {{"role": "{item.get("role", "")}", "content": "{_escape_json_string(item.get("content", ""))}"}}{suffix}'
        )
    rows.append("]")
    return "\n".join(rows)


def _escape_json_string(value: str) -> str:
    return (
        value.replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("\n", "\\n")
        .replace("\r", "\\r")
        .replace("\t", "\\t")
    )


def _build_system_prompt(
    *,
    ticker: str,
    trade_date: str,
    summary_text: str | None,
    available_sections: list[str],
    question: str,
    loader: ReportContextLoader,
    trace_dir: str,
) -> str:
    section_menu = _build_section_menu(available_sections)
    summary_block = _build_summary_block(summary_text)
    routing = InsightReplyRouter().route(
        llm=None,
        question=question,
        conversation_history=[],
        available_sections=available_sections,
    )
    gated_section = routing.primary_section
    gated_section_content = (
        loader.load_single_section(trace_dir=trace_dir, section=gated_section)
        if gated_section
        else None
    )
    preloaded_block = _build_preloaded_section_block(
        section=gated_section,
        content=gated_section_content,
    )
    return (
        f"{_TOOL_SYSTEM_PROMPT}\n\n"
        f"本次分析标的：{ticker}，交易日期：{trade_date}\n\n"
        f"{summary_block}"
        f"{preloaded_block}"
        f"本次报告包含以下可用章节（按需调用工具读取）：\n{section_menu}"
    )


if __name__ == "__main__":
    main()
