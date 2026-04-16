from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from langchain_core.messages import AIMessage

from ta_service.services.insight_reply_router import InsightReplyRouter


class FakeLLM:
    def __init__(self, content: str):
        self.content = content
        self.invocations: list[list[object]] = []

    def invoke(self, messages: list[object]) -> AIMessage:
        self.invocations.append(list(messages))
        return AIMessage(content=self.content)


def test_router_uses_llm_json_output_for_action_question() -> None:
    router = InsightReplyRouter()
    llm = FakeLLM(
        """
        {"intent":"action","primary_section":"decision","fallback_sections":["trading_plan"],"reason":"user is asking how to act"}
        """
    )

    routing = router.route(
        llm=llm,
        question="怎么卖出呢",
        conversation_history=[],
        available_sections=["decision", "trading_plan", "risk_cons"],
    )

    assert routing.intent == "action"
    assert routing.primary_section == "decision"
    assert routing.fallback_sections == ["trading_plan"]
    assert routing.reason == "user is asking how to act"


def test_router_can_use_history_for_short_followup() -> None:
    router = InsightReplyRouter()
    llm = FakeLLM(
        """
        {"intent":"fundamental_reason","primary_section":"fundamentals","fallback_sections":["market"],"reason":"short follow-up continues prior request for concrete data"}
        """
    )

    routing = router.route(
        llm=llm,
        question="想知道",
        conversation_history=[
            {"role": "assistant", "content": "还想知道具体哪些数据支撑这个判断吗？"}
        ],
        available_sections=["fundamentals", "market", "research_mgr"],
    )

    assert routing.intent == "fundamental_reason"
    assert routing.primary_section == "fundamentals"
    assert routing.fallback_sections == ["market"]


def test_router_falls_back_to_no_preload_when_llm_unavailable() -> None:
    router = InsightReplyRouter()

    routing = router.route(
        llm=None,
        question="主要风险是什么？",
        conversation_history=[],
        available_sections=["risk_cons", "research_mgr"],
    )

    assert routing.intent == "general"
    assert routing.primary_section is None
    assert routing.fallback_sections == []
    assert routing.reason == "router unavailable"
