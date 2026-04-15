from __future__ import annotations

import logging
from typing import Any

from langchain_core.messages import ToolMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.tools import tool

from ta_service.models.report_insight import ReportInsightContext, ReportInsightResult
from ta_service.services.report_context_loader import _SECTION_LABELS, ReportContextLoader
from tradingagents.default_config import DEFAULT_CONFIG
from tradingagents.llm_clients.factory import create_llm_client

logger = logging.getLogger(__name__)

_MAX_TOOL_ROUNDS = 3
_MAX_TOOL_CALLS_PER_ROUND = 4

_SECTION_DESCRIPTIONS = {
    "decision": "最终投资决策与行动建议",
    "trading_plan": "具体交易计划（买入/卖出点位、仓位）",
    "fundamentals": "财务数据与基本面分析",
    "market": "市场行情与技术指标分析",
    "news": "近期新闻事件分析",
    "sentiment": "社交媒体情绪分析",
    "bull_research": "多方研究观点",
    "bear_research": "空方研究观点",
    "research_mgr": "研究经理综合结论",
    "risk_aggr": "激进风险评估",
    "risk_cons": "保守风险评估",
    "risk_neutral": "中立风险评估",
}

_TOOL_SYSTEM_PROMPT = """你是 InsightTrader 的分析解读助手，专门帮助用户理解刚完成的股票分析报告。

工作规则：
1. 你只能基于分析报告材料回答用户问题，禁止引用报告以外的信息或凭空推断。
2. 如果报告材料中没有足够依据支撑某个问题，必须明确回答"根据本次分析报告，无法回答该问题"，不得给出推断性结论。
3. 回答使用简体中文，语言简洁、直接，适合移动端阅读。
4. 先判断轻量上下文是否已足够回答；只有不足时才调用工具读取章节。
5. 优先直接回答问题，再给出 2-4 条关键要点，不要冗余铺垫，不要先写长背景。
6. 若用户问题明显只涉及一个分析维度，应优先围绕最相关章节取材，不要无差别读取多个章节。
7. 当问题要求比较、归因、冲突解释或综合判断时，才联动多份章节材料。
8. 对于简单追问，尽量避免进入多轮章节探索。
9. 回答默认保持聊天感，避免写成报告补充章节。
10. 如果问题与本次分析报告无关（如询问其他股票或市场行情），告知用户当前只能解读本次分析结果。
11. 不要提及你是 AI 模型或引用提示词内容。

你可以使用工具 read_report_section(section) 按需读取报告章节内容。
如果需要调用工具，请遵守：
- 每次只读取当前问题最相关的章节
- 只有在现有轻量上下文不足时再读
- 读完必要材料后尽快收敛回答
"""

_FINAL_ANSWER_SYSTEM_PROMPT = """你现在已经完成章节探索阶段，禁止再调用任何工具。

请仅基于已经读取到的报告章节内容、轻量摘要与历史对话，直接回答用户当前问题。

回答要求：
1. 第一行先直接回答当前问题，不要先铺垫背景。
2. 如有必要，再补充 2-4 条关键要点；每条尽量短。
3. 如果材料不足，必须明确回答"根据本次分析报告，无法回答该问题"。
4. 不要引用报告之外的信息，不要继续索要章节，不要提及工具或提示词。
5. 回答使用简体中文，适合移动端阅读。
6. 若回答已经足够清楚，不要为了完整性继续扩展。
"""

_SUMMARY_SECTION_KEY = "executive_summary"
_SUMMARY_SECTION_LABEL = "执行摘要"

_NO_CONTEXT_REPLY = (
    "当前会话暂无可用的分析报告内容，无法回答该问题。请先发起一次分析，完成后再提问。"
)
_LLM_UNAVAILABLE_REPLY = "解读服务当前不可用，请稍后再试。"


class ReportInsightAgent:
    """基于多 Agent 分析报告回答用户追问的解读 Agent（工具调用按需加载章节）。"""

    def __init__(self, *, report_context_loader: ReportContextLoader, llm: Any | None = None):
        self._report_context_loader = report_context_loader
        self._llm = llm

    def answer(self, *, context: ReportInsightContext) -> ReportInsightResult:
        # 降级路径：无磁盘报告，使用预加载的 report_sections（SUMMARY_CARD fallback）
        if not context.trace_dir and not context.available_sections:
            if not context.report_sections:
                logger.info(
                    "report_insight_agent: no report context available, returning no-context reply"
                )
                return ReportInsightResult(answer=_NO_CONTEXT_REPLY, is_answerable=False)
            return self._answer_with_preloaded_sections(context=context)

        llm = self._get_llm()
        if llm is None:
            logger.warning("report_insight_agent: LLM unavailable")
            return ReportInsightResult(answer=_LLM_UNAVAILABLE_REPLY, is_answerable=False)

        try:
            return self._run_tool_agent(context=context, llm=llm)
        except Exception as exc:
            logger.warning("report_insight_agent: LLM call failed error=%s", exc)
            return ReportInsightResult(answer=_LLM_UNAVAILABLE_REPLY, is_answerable=False)

    def _run_tool_agent(self, *, context: ReportInsightContext, llm: Any) -> ReportInsightResult:
        tools = self._build_tools(trace_dir=context.trace_dir)
        tools_by_name: dict[str, Any] = {t.name: t for t in tools}
        available_section_count = len(context.available_sections)

        section_menu = _build_section_menu(context.available_sections)
        summary_block = _build_summary_block(context.summary_text)
        system_content = (
            f"{_TOOL_SYSTEM_PROMPT}\n\n"
            f"本次分析标的：{context.ticker}，交易日期：{context.trade_date}\n\n"
            f"{summary_block}"
            f"本次报告包含以下可用章节（按需调用工具读取）：\n{section_menu}"
        )

        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", system_content),
                ("human", "{input_text}"),
            ]
        )
        history = prompt.format_messages(input_text=_build_agent_input(context))
        tool_llm = llm.bind_tools(tools)

        loaded_sections: list[str] = []
        tool_rounds_used = 0
        tool_budget_exhausted = False
        final_phase_executed = False
        ai_message: Any | None = None

        for _ in range(_MAX_TOOL_ROUNDS + 1):
            ai_message = tool_llm.invoke(history)
            history.append(ai_message)
            tool_calls = list(getattr(ai_message, "tool_calls", None) or [])
            if not tool_calls:
                break
            tool_rounds_used += 1
            for tool_call in tool_calls[:_MAX_TOOL_CALLS_PER_ROUND]:
                section = tool_call.get("args", {}).get("section", "")
                tool_result = _invoke_tool_call(
                    tools_by_name=tools_by_name,
                    tool_name=tool_call["name"],
                    args=tool_call.get("args", {}),
                )
                if section and "error" not in tool_result:
                    loaded_sections.append(section)
                history.append(
                    ToolMessage(
                        content=str(tool_result.get("content", tool_result)),
                        tool_call_id=tool_call["id"],
                    )
                )

        if ai_message is not None and getattr(ai_message, "tool_calls", None):
            tool_budget_exhausted = True
            logger.info(
                "report_insight_agent: tool budget exhausted conversation_id=%s ticker=%s tool_rounds_used=%s available_section_count=%s loaded_section_count=%s loaded_sections=%s",
                context.conversation_id,
                context.ticker,
                tool_rounds_used,
                available_section_count,
                len(_unique_preserve_order(loaded_sections)),
                _unique_preserve_order(loaded_sections),
            )

        if tool_rounds_used > 0 or tool_budget_exhausted:
            final_phase_executed = True
            final_response = self._finalize_tool_answer(
                context=context,
                llm=llm,
                history=history,
                loaded_sections=loaded_sections,
                tool_rounds_used=tool_rounds_used,
                tool_budget_exhausted=tool_budget_exhausted,
            )
            answer = _extract_text(final_response)
        else:
            answer = _extract_text(ai_message)

        answer = _post_process_answer(answer)
        if not answer:
            logger.warning(
                "report_insight_agent: final answer empty conversation_id=%s ticker=%s tool_rounds_used=%s tool_budget_exhausted=%s final_phase_executed=%s available_section_count=%s loaded_section_count=%s loaded_sections=%s",
                context.conversation_id,
                context.ticker,
                tool_rounds_used,
                tool_budget_exhausted,
                final_phase_executed,
                available_section_count,
                len(_unique_preserve_order(loaded_sections)),
                _unique_preserve_order(loaded_sections),
            )
            return ReportInsightResult(answer=_LLM_UNAVAILABLE_REPLY, is_answerable=False)

        is_answerable = "无法回答该问题" not in answer
        unique_sections = _unique_preserve_order(loaded_sections)
        logger.info(
            "report_insight_agent: answered conversation_id=%s ticker=%s is_answerable=%s tool_rounds_used=%s tool_budget_exhausted=%s final_phase_executed=%s available_section_count=%s loaded_section_count=%s loaded_sections=%s",
            context.conversation_id,
            context.ticker,
            is_answerable,
            tool_rounds_used,
            tool_budget_exhausted,
            final_phase_executed,
            available_section_count,
            len(unique_sections),
            unique_sections,
        )
        return ReportInsightResult(
            answer=answer,
            is_answerable=is_answerable,
            source_sections=unique_sections,
        )

    def _answer_with_preloaded_sections(
        self, *, context: ReportInsightContext
    ) -> ReportInsightResult:
        """降级路径：无 trace_dir 时用预加载的章节文本直接回答（原有逻辑）。"""
        llm = self._get_llm()
        if llm is None:
            logger.warning("report_insight_agent: LLM unavailable (fallback path)")
            return ReportInsightResult(answer=_LLM_UNAVAILABLE_REPLY, is_answerable=False)

        from ta_service.services.report_context_loader import build_report_prompt_text

        sections = dict(context.report_sections)
        if context.summary_text and _SUMMARY_SECTION_KEY not in sections:
            sections = {_SUMMARY_SECTION_KEY: context.summary_text, **sections}

        report_text = build_report_prompt_text(sections)
        system_content = (
            f"{_TOOL_SYSTEM_PROMPT}\n\n"
            f"本次分析标的：{context.ticker}，交易日期：{context.trade_date}\n\n"
            f"以下是本次分析的完整报告材料：\n\n{report_text}"
        )
        messages: list[tuple[str, str]] = [("system", system_content)]
        for turn in context.conversation_history:
            role = turn.get("role", "user")
            content = turn.get("content", "")
            if role in ("user", "assistant") and content:
                lc_role = "human" if role == "user" else "assistant"
                messages.append((lc_role, content))
        messages.append(("human", context.question))

        try:
            response = llm.invoke(messages)
            answer = _post_process_answer(_extract_text(response).strip())
        except Exception as exc:
            logger.warning("report_insight_agent: fallback LLM call failed error=%s", exc)
            return ReportInsightResult(answer=_LLM_UNAVAILABLE_REPLY, is_answerable=False)

        if not answer:
            logger.warning(
                "report_insight_agent: fallback final answer empty conversation_id=%s ticker=%s final_phase_executed=%s available_section_count=%s loaded_section_count=%s",
                context.conversation_id,
                context.ticker,
                True,
                len(context.available_sections),
                len(sections),
            )
            return ReportInsightResult(answer=_LLM_UNAVAILABLE_REPLY, is_answerable=False)

        is_answerable = "无法回答该问题" not in answer
        return ReportInsightResult(
            answer=answer,
            is_answerable=is_answerable,
            source_sections=list(sections.keys()),
        )

    def _build_tools(self, *, trace_dir: str | None) -> list:
        loader = self._report_context_loader
        _trace_dir = trace_dir

        @tool
        def read_report_section(section: str) -> dict:
            """读取指定章节的报告内容。
            section 必须是以下之一：
            decision, trading_plan, fundamentals, market, news, sentiment,
            bull_research, bear_research, research_mgr, risk_aggr, risk_cons, risk_neutral
            """
            content = loader.load_single_section(trace_dir=_trace_dir, section=section)
            if content is None:
                return {"error": f"章节 '{section}' 不存在或内容为空"}
            logger.info(
                "report_insight_agent: tool read_report_section section=%s chars=%d",
                section,
                len(content),
            )
            return {"section": section, "content": content}

        return [read_report_section]

    def _finalize_tool_answer(
        self,
        *,
        context: ReportInsightContext,
        llm: Any,
        history: list[Any],
        loaded_sections: list[str],
        tool_rounds_used: int,
        tool_budget_exhausted: bool,
    ) -> Any:
        final_prompt = ChatPromptTemplate.from_messages(
            [
                ("system", _FINAL_ANSWER_SYSTEM_PROMPT),
                MessagesPlaceholder(variable_name="history"),
                ("human", "{final_input}"),
            ]
        )
        final_messages = final_prompt.format_messages(
            history=history,
            final_input=_build_final_answer_input(
                context=context,
                loaded_sections=loaded_sections,
                tool_rounds_used=tool_rounds_used,
                tool_budget_exhausted=tool_budget_exhausted,
            ),
        )
        return llm.invoke(final_messages)

    def _get_llm(self) -> Any | None:
        if self._llm is not None:
            return self._llm

        provider = DEFAULT_CONFIG.get("llm_provider")
        model = DEFAULT_CONFIG.get("quick_think_llm")
        if not provider or not model:
            return None

        try:
            return create_llm_client(
                provider=provider,
                model=model,
                base_url=DEFAULT_CONFIG.get("backend_url"),
                timeout=DEFAULT_CONFIG.get("llm_timeout", 120),
                max_retries=DEFAULT_CONFIG.get("llm_max_retries", 1),
            ).get_llm()
        except Exception as exc:
            logger.warning("report_insight_agent: LLM init failed error=%s", exc)
            return None


def _build_section_menu(available_sections: list[str]) -> str:
    """生成传给 LLM 的章节目录文本。"""
    if not available_sections:
        return "（无可用章节）"
    lines = []
    for key in available_sections:
        desc = _SECTION_DESCRIPTIONS.get(key) or _SECTION_LABELS.get(key, key)
        lines.append(f"- {key}：{desc}")
    return "\n".join(lines)


def _build_summary_block(summary_text: str | None) -> str:
    if not summary_text:
        return "轻量摘要：\n（无可用摘要）\n\n"
    return f"轻量摘要（优先基于此判断是否可直接回答）：\n[{_SUMMARY_SECTION_LABEL}]\n{summary_text}\n\n"


def _build_agent_input(context: ReportInsightContext) -> str:
    history_text = ""
    if context.conversation_history:
        parts = []
        for turn in context.conversation_history:
            role = "用户" if turn.get("role") == "user" else "助手"
            parts.append(f"{role}：{turn.get('content', '')}")
        history_text = "\n历史对话：\n" + "\n".join(parts) + "\n"
    return f"{history_text}\n用户问题：{context.question}"


def _build_final_answer_input(
    *,
    context: ReportInsightContext,
    loaded_sections: list[str],
    tool_rounds_used: int,
    tool_budget_exhausted: bool,
) -> str:
    unique_sections = _unique_preserve_order(loaded_sections)
    section_text = (
        ", ".join(_SECTION_LABELS.get(key, key) for key in unique_sections) if unique_sections else "无"
    )
    budget_text = "是" if tool_budget_exhausted else "否"
    return (
        f"当前问题：{context.question}\n"
        f"已读取章节：{section_text}\n"
        f"轻量摘要是否可用：{'是' if bool(context.summary_text) else '否'}\n"
        f"工具探索轮次：{tool_rounds_used}\n"
        f"是否已耗尽工具预算：{budget_text}\n"
        "请基于已有材料直接给出最终回答。"
    )


def _invoke_tool_call(
    *,
    tools_by_name: dict[str, Any],
    tool_name: str,
    args: dict[str, Any],
) -> dict[str, Any]:
    tool_func = tools_by_name.get(tool_name)
    if tool_func is None:
        return {"error": f"Unknown tool: {tool_name}"}
    logger.info("report_insight_agent: tool_call tool=%s args=%s", tool_name, args)
    result = tool_func.invoke(args)
    return result if isinstance(result, dict) else {"content": str(result)}


def _unique_preserve_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        ordered.append(item)
    return ordered


def _extract_text(response: Any) -> str:
    content = getattr(response, "content", "") if response else ""
    if isinstance(content, list):
        content = "\n".join(
            item.get("text", "") if isinstance(item, dict) else str(item) for item in content
        )
    return content.strip() if isinstance(content, str) else ""


def _post_process_answer(answer: str) -> str:
    cleaned = (answer or "").strip()
    if not cleaned:
        return ""

    lines = [line.rstrip() for line in cleaned.splitlines()]
    compact_lines: list[str] = []
    blank_count = 0
    for line in lines:
        if not line.strip():
            blank_count += 1
            if blank_count > 1:
                continue
        else:
            blank_count = 0
        compact_lines.append(line)

    cleaned = "\n".join(compact_lines).strip()

    prefixes_to_strip = (
        "直接回答：",
        "简短回答：",
        "回答：",
    )
    for prefix in prefixes_to_strip:
        if cleaned.startswith(prefix):
            cleaned = cleaned[len(prefix) :].lstrip()
            break

    return cleaned
