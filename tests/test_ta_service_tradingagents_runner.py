from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ta_service.adapters.tradingagents_runner import TradingAgentsRunner


def _build_snapshot(state: dict) -> dict[str, str]:
    runner = TradingAgentsRunner.__new__(TradingAgentsRunner)
    return runner._build_stage_snapshot(["market", "social", "news", "fundamentals"], state)


def test_portfolio_stage_stays_in_progress_until_final_trade_decision_exists() -> None:
    snapshot = _build_snapshot(
        {
            "market_report": "done",
            "sentiment_report": "done",
            "news_report": "done",
            "fundamentals_report": "done",
            "investment_debate_state": {"judge_decision": "buy"},
            "trader_investment_plan": "plan",
            "risk_debate_state": {"judge_decision": "risk summary"},
        }
    )

    assert snapshot["risk.debate"] == "completed"
    assert snapshot["portfolio.decision"] == "in_progress"


def test_portfolio_stage_completes_after_final_trade_decision_exists() -> None:
    snapshot = _build_snapshot(
        {
            "market_report": "done",
            "sentiment_report": "done",
            "news_report": "done",
            "fundamentals_report": "done",
            "investment_debate_state": {"judge_decision": "buy"},
            "trader_investment_plan": "plan",
            "risk_debate_state": {"judge_decision": "risk summary"},
            "final_trade_decision": "sell",
        }
    )

    assert snapshot["risk.debate"] == "completed"
    assert snapshot["portfolio.decision"] == "completed"
