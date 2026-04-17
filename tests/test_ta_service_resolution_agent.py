from __future__ import annotations

import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage

from ta_service.models.resolution import ResolutionAgentContext
from ta_service.services.resolution_agent import ResolutionAgent


class FakeStockLookupGateway:
    def search_stock_candidates(
        self,
        *,
        query: str,
        market_hints: list[str] | None = None,
        limit: int = 5,
    ) -> list[object]:
        if query == "中国平安":
            return [
                _Candidate("2318.HK", "中国平安", "HK", "HKEX"),
                _Candidate("601318.SH", "中国平安", "CN", "SSE"),
            ]
        return []

    def get_stock_profile(self, *, ticker: str):
        profiles = {
            "2318.HK": _Candidate("2318.HK", "中国平安", "HK", "HKEX"),
            "601318.SH": _Candidate("601318.SH", "中国平安", "CN", "SSE"),
        }
        return profiles.get(ticker)


class _Candidate:
    def __init__(self, ticker: str, name: str, market: str, exchange: str):
        self.ticker = ticker
        self.name = name
        self.market = market
        self.exchange = exchange
        self.aliases: list[str] = []
        self.score = 1.0
        self.assetType = "stock"
        self.isActive = True

    def model_dump(self) -> dict:
        return {
            "ticker": self.ticker,
            "name": self.name,
            "market": self.market,
            "exchange": self.exchange,
            "aliases": self.aliases,
            "score": self.score,
            "assetType": self.assetType,
            "isActive": self.isActive,
        }


class FakeResolutionLLM:
    def __init__(self):
        self.tool_invocations: list[list[object]] = []
        self.final_invocations: list[list[object]] = []

    def bind_tools(self, tools: list[object]) -> "FakeToolBoundLLM":
        return FakeToolBoundLLM(self, tools)

    def bind(self, **kwargs) -> "FakeFinalLLM":
        return FakeFinalLLM(self)


class FakeToolBoundLLM:
    def __init__(self, parent: FakeResolutionLLM, tools: list[object]):
        self.parent = parent
        self.tools = list(tools)
        self.calls = 0

    def invoke(self, messages: list[object]) -> AIMessage:
        self.parent.tool_invocations.append(list(messages))
        self.calls += 1
        if self.calls == 1:
            return AIMessage(
                content="我来帮您分析中国平安这只股票。首先让我搜索一下相关的股票候选信息。",
                tool_calls=[
                    {
                        "id": "call-1",
                        "name": "search_stock_candidates",
                        "args": {"query": "中国平安", "limit": 5},
                    }
                ],
            )
        if self.calls == 2:
            return AIMessage(
                content="我找到了中国平安的多个候选股票。现在让我获取这些股票的标准资料来确认：",
                tool_calls=[
                    {
                        "id": "call-2",
                        "name": "get_stock_profile",
                        "args": {"ticker": "601318.SH"},
                    }
                ],
            )
        return AIMessage(content="")


class FakeFinalLLM:
    def __init__(self, parent: FakeResolutionLLM):
        self.parent = parent

    def invoke(self, messages: list[object]) -> AIMessage:
        self.parent.final_invocations.append(list(messages))
        return AIMessage(
            content=json.dumps(
                {
                    "status": "need_disambiguation",
                    "assistantReply": "我找到了两个中国平安的候选，请选择你想分析的那个。",
                    "stock": None,
                    "candidates": [
                        {
                            "ticker": "2318.HK",
                            "name": "中国平安",
                            "market": "HK",
                            "exchange": "HKEX",
                            "aliases": [],
                            "score": 0.98,
                            "assetType": "stock",
                            "isActive": True,
                        },
                        {
                            "ticker": "601318.SH",
                            "name": "中国平安",
                            "market": "CN",
                            "exchange": "SSE",
                            "aliases": [],
                            "score": 0.98,
                            "assetType": "stock",
                            "isActive": True,
                        },
                    ],
                    "focusPoints": [],
                    "shouldCreateAnalysisTask": False,
                    "terminate": False,
                },
                ensure_ascii=False,
            )
        )


def test_resolution_agent_does_not_feed_assistant_chatter_back_into_history() -> None:
    llm = FakeResolutionLLM()
    agent = ResolutionAgent(stock_lookup_gateway=FakeStockLookupGateway(), llm=llm)

    result = agent.resolve(
        context=ResolutionAgentContext(
            currentMessage="中国平安",
            currentRound=1,
            analysisPrompt="中国平安",
            priorResolutionSummary="",
            pendingResolution=None,
        )
    )

    assert result.status == "need_disambiguation"
    assert len(llm.tool_invocations) >= 2

    second_round = llm.tool_invocations[1]
    tool_messages = [message for message in second_round if isinstance(message, ToolMessage)]
    ai_messages = [
        message for message in second_round if isinstance(message, AIMessage) and not isinstance(message, (HumanMessage, SystemMessage))
    ]

    assert tool_messages, "tool result should be preserved in history"
    assert any(isinstance(message, AIMessage) and message.tool_calls for message in ai_messages)
    assert not any("我来帮您分析中国平安这只股票" in (getattr(message, "content", "") or "") for message in second_round)
