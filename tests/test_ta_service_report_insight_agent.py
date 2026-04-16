from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from langchain_core.messages import AIMessage

from ta_service.models.report_insight import ReportInsightContext
from ta_service.services.report_insight_agent import (
    ReportInsightAgent,
    _CHAT_STYLE_EXAMPLES,
    _FINAL_ANSWER_SYSTEM_PROMPT,
    _TOOL_SYSTEM_PROMPT,
    _iter_text_delta_events,
    _post_process_answer,
)


class FakeLoader:
    def __init__(self, sections: dict[str, str] | None = None):
        self.sections = sections or {}
        self.requested_sections: list[str] = []

    def load_single_section(self, *, trace_dir: str | None, section: str) -> str | None:
        self.requested_sections.append(section)
        return self.sections.get(section)


class FakeToolAwareLLM:
    def __init__(self, responses: list[AIMessage]):
        self._responses = list(responses)
        self.invocations: list[list[object]] = []
        self.stream_invocations: list[list[object]] = []
        self.bound_tools: list[object] = []

    def bind_tools(self, tools: list[object]) -> "FakeToolAwareLLM":
        self.bound_tools = list(tools)
        return self

    def invoke(self, messages: list[object]) -> AIMessage:
        self.invocations.append(list(messages))
        if not self._responses:
            raise AssertionError("No fake response left for invoke()")
        return self._responses.pop(0)

    def stream(self, messages: list[object]):
        self.stream_invocations.append(list(messages))
        if not self._responses:
            raise AssertionError("No fake response left for stream()")
        response = self._responses.pop(0)
        content = response.content if isinstance(response.content, str) else ""
        midpoint = max(1, len(content) // 2)
        for part in (content[:midpoint], content[midpoint:]):
            if part:
                yield AIMessage(content=part)


def test_post_process_answer_only_trims_whitespace() -> None:
    answer = "\n\n回答：现在不适合买入。\n"

    result = _post_process_answer(answer)

    assert result == "回答：现在不适合买入。"


def test_prompts_include_chat_style_examples() -> None:
    assert "风格示例" in _CHAT_STYLE_EXAMPLES
    assert "差：" in _CHAT_STYLE_EXAMPLES
    assert "好：" in _CHAT_STYLE_EXAMPLES
    assert _CHAT_STYLE_EXAMPLES in _TOOL_SYSTEM_PROMPT
    assert _CHAT_STYLE_EXAMPLES in _FINAL_ANSWER_SYSTEM_PROMPT
    assert "不要使用“根据本次分析报告" in _TOOL_SYSTEM_PROMPT


def test_agent_uses_summary_for_simple_question_without_tool_reads() -> None:
    loader = FakeLoader(
        {
            "decision": "最终决策：当前更偏卖出，不建议继续加仓。",
            "risk_cons": "保守风险章节：估值偏高、盈利兑现仍需观察。",
        }
    )
    llm = FakeToolAwareLLM(
        [
            AIMessage(
                content='{"intent":"action","primary_section":"decision","fallback_sections":[],"reason":"simple action follow-up"}'
            ),
            AIMessage(
                content="现在不太适合，更偏向先等等。主要是估值不低，兑现还需要观察。如果你愿意，我可以继续说为什么。",
            ),
            AIMessage(
                content="现在不太适合，更偏向先等等。主要是估值不低，兑现还需要观察。如果你愿意，我可以继续说为什么。",
            )
        ]
    )
    agent = ReportInsightAgent(report_context_loader=loader, llm=llm)
    context = ReportInsightContext(
        conversation_id="conv-1",
        question="现在适合买入吗？",
        ticker="TSLA",
        trade_date="2026-04-16",
        trace_dir="D:/trace/mock",
        available_sections=["decision", "risk_cons"],
        summary_text="执行摘要：整体偏谨慎，主要因为估值不低、后续兑现还需要观察。",
        conversation_history=[
            {"role": "assistant", "content": "要不要我继续说现在适不适合买入？"}
        ],
    )

    result = agent.answer(context=context)

    assert loader.requested_sections == ["decision"]
    assert result.source_sections == ["executive_summary", "decision"]
    assert result.routing_intent == "action"
    assert result.routing_primary_section == "decision"
    assert result.routing_fallback_sections == []
    assert result.routing_reason == "simple action follow-up"
    assert isinstance(result.llm_router_ms, float)
    assert isinstance(result.llm_reply_ms, float)
    assert result.is_answerable is True
    assert result.answer.startswith("现在不太适合，更偏向先等等。")
    assert "如果你愿意，我可以继续说为什么。" in result.answer
    assert len(llm.invocations) == 2


def test_agent_reads_single_section_and_preserves_model_style_output() -> None:
    loader = FakeLoader(
        {
            "risk_cons": "保守风险评估：主要风险在于增长放缓、估值压力、资本开支偏高。",
        }
    )
    llm = FakeToolAwareLLM(
        [
            AIMessage(
                content='{"intent":"risk","primary_section":"risk_cons","fallback_sections":[],"reason":"needs one risk section"}'
            ),
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "id": "call-1",
                        "name": "read_report_section",
                        "args": {"section": "risk_cons"},
                    }
                ],
            ),
            AIMessage(content="我已经看完了相关章节。"),
            AIMessage(
                content=(
                    "主要是增长放缓、估值压力和资本开支偏高。"
                    "增长一旦慢下来，回撤会很快放大。"
                    "如果你愿意，我可以继续说哪个风险更致命。"
                )
            ),
        ]
    )
    agent = ReportInsightAgent(report_context_loader=loader, llm=llm)
    context = ReportInsightContext(
        conversation_id="conv-2",
        question="主要风险是什么？",
        ticker="TSLA",
        trade_date="2026-04-16",
        trace_dir="D:/trace/mock",
        available_sections=["decision", "risk_cons", "risk_neutral"],
        summary_text="执行摘要：整体偏谨慎，但摘要未展开具体风险排序。",
        conversation_history=[
            {"role": "assistant", "content": "要不要我继续说主要风险是什么？"}
        ],
    )

    result = agent.answer(context=context)

    assert loader.requested_sections == ["risk_cons"]
    assert result.source_sections == ["executive_summary", "risk_cons"]
    assert result.routing_intent == "risk"
    assert result.routing_primary_section == "risk_cons"
    assert result.routing_fallback_sections == []
    assert result.routing_reason == "needs one risk section"
    assert isinstance(result.llm_router_ms, float)
    assert isinstance(result.llm_reply_ms, float)
    assert result.is_answerable is True
    assert result.answer.startswith("主要是增长放缓、估值压力和资本开支偏高。")
    assert "如果你愿意，我可以继续说哪个风险更致命。" in result.answer
    assert len(llm.invocations) == 4


def test_iter_text_delta_events_splits_long_text() -> None:
    text = "这是一条会被拆成多段输出的回复，用来验证浏览器里能够看到逐段追加的效果。"

    events = list(_iter_text_delta_events(text))

    assert len(events) >= 2
    assert "".join(event["text"] for event in events) == text


def test_answer_events_emits_multiple_delta_events_for_direct_reply() -> None:
    loader = FakeLoader({"decision": "最终决策：当前更偏卖出，不建议继续加仓。"})
    llm = FakeToolAwareLLM(
        [
            AIMessage(
                content='{"intent":"action","primary_section":"decision","fallback_sections":[],"reason":"simple action follow-up"}'
            ),
            AIMessage(
                content="现在不太适合，更偏向先等等。主要是估值不低，兑现还需要观察，所以更像先控制风险，再等更清楚的信号。",
            ),
            AIMessage(
                content="现在不太适合，更偏向先等等。主要是估值不低，兑现还需要观察，所以更像先控制风险，再等更清楚的信号。",
            ),
        ]
    )
    agent = ReportInsightAgent(report_context_loader=loader, llm=llm)
    context = ReportInsightContext(
        conversation_id="conv-stream-1",
        question="现在适合买入吗？",
        ticker="TSLA",
        trade_date="2026-04-16",
        trace_dir="D:/trace/mock",
        available_sections=["decision"],
        summary_text="执行摘要：整体偏谨慎。",
    )

    stream = agent.answer_events(context=context)
    events: list[dict] = []
    while True:
        try:
            events.append(next(stream))
        except StopIteration as stop:
            result = stop.value
            break

    delta_events = [event for event in events if event.get("event") == "delta"]
    assert len(delta_events) >= 2
    assert "".join(event["text"] for event in delta_events) == result.answer
    assert len(llm.stream_invocations) == 1
