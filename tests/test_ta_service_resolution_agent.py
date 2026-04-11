import unittest
from types import SimpleNamespace
from unittest.mock import patch

from langchain_core.messages import AIMessage

from ta_service.models.resolution import ResolutionAgentContext
from ta_service.services.resolution_agent import ResolutionAgent


class FakeStockLookupGateway:
    def search_stock_candidates(self, *, query: str, market_hints=None, limit: int = 5):
        return []

    def get_stock_profile(self, *, ticker: str):
        return None


class FakeFinalLLM:
    def __init__(self, content: str):
        self.content = content
        self.invocations = []

    def invoke(self, messages):
        self.invocations.append(messages)
        return SimpleNamespace(content=self.content)


class FakeLLM:
    def __init__(self, final_content: str):
        self.final_content = final_content
        self.bound_kwargs = None
        self.tool_invocations = []
        self.final_runner = FakeFinalLLM(final_content)

    def bind_tools(self, tools):
        return self

    def invoke(self, messages):
        self.tool_invocations.append(messages)
        return AIMessage(content="done", tool_calls=[])

    def bind(self, **kwargs):
        self.bound_kwargs = kwargs
        return self.final_runner


class ResolutionAgentTests(unittest.TestCase):
    def setUp(self):
        self.context = ResolutionAgentContext(
            currentMessage="分析苹果，重点看估值",
            currentRound=1,
            analysisPrompt="分析苹果，重点看估值",
        )

    def test_returns_failed_when_llm_unavailable(self):
        agent = ResolutionAgent(stock_lookup_gateway=FakeStockLookupGateway(), llm=None)

        with patch.object(agent, "_get_llm", return_value=None):
            result = agent.resolve(context=self.context)

        self.assertEqual(result.status, "failed")
        self.assertTrue(result.terminate)
        self.assertEqual(result.candidates, [])

    def test_uses_json_object_for_final_output_and_parses_valid_json(self):
        fake_llm = FakeLLM(
            """
            {
              "status": "resolved",
              "assistantReply": "已为你确认分析标的是 Apple Inc.（AAPL）。",
              "stock": {
                "ticker": "AAPL",
                "name": "Apple Inc.",
                "market": "US",
                "exchange": "NASDAQ",
                "aliases": [],
                "score": 1.0,
                "assetType": "stock",
                "isActive": true
              },
              "candidates": [],
              "focusPoints": ["估值"],
              "shouldCreateAnalysisTask": true,
              "terminate": true
            }
            """
        )
        agent = ResolutionAgent(stock_lookup_gateway=FakeStockLookupGateway(), llm=fake_llm)

        result = agent.resolve(context=self.context)

        self.assertEqual(fake_llm.bound_kwargs, {"response_format": {"type": "json_object"}})
        self.assertEqual(result.status, "resolved")
        self.assertEqual(result.stock.ticker, "AAPL")
        self.assertTrue(result.shouldCreateAnalysisTask)


if __name__ == "__main__":
    unittest.main()
