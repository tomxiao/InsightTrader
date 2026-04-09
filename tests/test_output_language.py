import unittest

from tradingagents.agents.researchers.bear_researcher import create_bear_researcher
from tradingagents.agents.researchers.bull_researcher import create_bull_researcher
from tradingagents.agents.risk_mgmt.aggressive_debator import create_aggressive_debator
from tradingagents.agents.risk_mgmt.conservative_debator import create_conservative_debator
from tradingagents.agents.risk_mgmt.neutral_debator import create_neutral_debator
from tradingagents.agents.utils.memory import FinancialSituationMemory
from tradingagents.dataflows.config import get_config, set_config


class DummyResponse:
    def __init__(self, content: str):
        self.content = content


class CapturingLLM:
    def __init__(self):
        self.prompts = []

    def invoke(self, prompt):
        self.prompts.append(prompt)
        return DummyResponse("ok")


class OutputLanguageTests(unittest.TestCase):
    def setUp(self):
        self.original_config = get_config()
        set_config({"output_language": "Chinese"})

    def tearDown(self):
        set_config(self.original_config)

    def _sample_state(self):
        return {
            "investment_debate_state": {
                "history": "",
                "bull_history": "",
                "bear_history": "",
                "current_response": "",
                "count": 0,
            },
            "market_report": "market",
            "sentiment_report": "sentiment",
            "news_report": "news",
            "fundamentals_report": "fundamentals",
        }

    def _sample_risk_state(self):
        return {
            "risk_debate_state": {
                "history": "",
                "aggressive_history": "",
                "conservative_history": "",
                "neutral_history": "",
                "latest_speaker": "",
                "current_aggressive_response": "",
                "current_conservative_response": "",
                "current_neutral_response": "",
                "count": 0,
            },
            "market_report": "market",
            "sentiment_report": "sentiment",
            "news_report": "news",
            "fundamentals_report": "fundamentals",
            "trader_investment_plan": "plan",
        }

    def test_bull_researcher_prompt_honors_output_language(self):
        llm = CapturingLLM()
        node = create_bull_researcher(llm, FinancialSituationMemory("bull-test"))

        node(self._sample_state())

        self.assertTrue(llm.prompts)
        self.assertIn("Write your entire response in Chinese.", llm.prompts[0])

    def test_bear_researcher_prompt_honors_output_language(self):
        llm = CapturingLLM()
        node = create_bear_researcher(llm, FinancialSituationMemory("bear-test"))

        node(self._sample_state())

        self.assertTrue(llm.prompts)
        self.assertIn("Write your entire response in Chinese.", llm.prompts[0])

    def test_aggressive_risk_prompt_honors_output_language(self):
        llm = CapturingLLM()
        node = create_aggressive_debator(llm)

        node(self._sample_risk_state())

        self.assertTrue(llm.prompts)
        self.assertIn("Write your entire response in Chinese.", llm.prompts[0])

    def test_conservative_risk_prompt_honors_output_language(self):
        llm = CapturingLLM()
        node = create_conservative_debator(llm)

        node(self._sample_risk_state())

        self.assertTrue(llm.prompts)
        self.assertIn("Write your entire response in Chinese.", llm.prompts[0])

    def test_neutral_risk_prompt_honors_output_language(self):
        llm = CapturingLLM()
        node = create_neutral_debator(llm)

        node(self._sample_risk_state())

        self.assertTrue(llm.prompts)
        self.assertIn("Write your entire response in Chinese.", llm.prompts[0])


if __name__ == "__main__":
    unittest.main()
