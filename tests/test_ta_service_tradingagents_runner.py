from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ta_service.adapters.tradingagents_runner import TradingAgentsRunner
from ta_service.config.settings import Settings
from ta_service.runtime.run_context import build_run_context
from ta_service.teams import DEFAULT_TEAM_ID, normalize_team_id


def _build_snapshot(team_id: str, selected_analysts: list[str], state: dict) -> dict[str, str]:
    runner = TradingAgentsRunner.__new__(TradingAgentsRunner)
    return runner._build_stage_snapshot(team_id, selected_analysts, state)


def test_portfolio_stage_stays_in_progress_until_final_trade_decision_exists() -> None:
    snapshot = _build_snapshot(
        "full",
        ["market", "social", "news", "fundamentals"],
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
        "full",
        ["market", "social", "news", "fundamentals"],
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


def test_lite_team_uses_decision_finalize_stage() -> None:
    snapshot = _build_snapshot(
        "lite",
        ["market", "news", "fundamentals"],
        {
            "market_report": "done",
            "news_report": "done",
            "fundamentals_report": "done",
        },
    )

    assert snapshot["analysts.market"] == "completed"
    assert snapshot["analysts.news"] == "completed"
    assert snapshot["analysts.fundamentals"] == "completed"
    assert snapshot["decision.finalize"] == "in_progress"


def test_lite_team_completes_after_final_trade_decision_exists() -> None:
    snapshot = _build_snapshot(
        "lite",
        ["market", "news", "fundamentals"],
        {
            "market_report": "done",
            "news_report": "done",
            "fundamentals_report": "done",
            "final_trade_decision": "Hold",
        },
    )

    assert snapshot["decision.finalize"] == "completed"


def test_default_team_is_lite() -> None:
    assert DEFAULT_TEAM_ID == "lite"
    assert normalize_team_id(None) == "lite"
    assert normalize_team_id("") == "lite"


def test_build_run_context_defaults_to_results_analysis_root(tmp_path: Path) -> None:
    settings = Settings(results_root=tmp_path / "results" / "analysis")

    run_context = build_run_context(
        settings=settings,
        ticker="SNDK",
        trade_date="20260416",
    )

    assert run_context.trace_dir.parent == settings.results_root
    assert run_context.trace_dir.name.startswith("SNDK_")
