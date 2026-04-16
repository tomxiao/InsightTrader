from __future__ import annotations

from pathlib import Path
import sys
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ta_service.adapters.tradingagents_runner import TradingAgentsRunner
from ta_service.config.settings import Settings
from ta_service.runtime.run_context import build_run_context
from ta_service.teams import DEFAULT_TEAM_ID, normalize_team_id
from tradingagents.graph.lite_trading_graph import LiteTradingGraph


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


def test_lite_team_marks_all_pending_analysts_in_progress_for_parallel_execution() -> None:
    snapshot = _build_snapshot(
        "lite",
        ["market", "news", "fundamentals"],
        {},
    )

    assert snapshot["analysts.market"] == "in_progress"
    assert snapshot["analysts.news"] == "in_progress"
    assert snapshot["analysts.fundamentals"] == "in_progress"
    assert snapshot["decision.finalize"] == "pending"


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


def test_lite_graph_waits_for_all_clear_nodes_before_decision_manager() -> None:
    class _FakeClient:
        def get_llm(self):
            return object()

    with patch(
        "tradingagents.graph.lite_trading_graph.create_llm_client",
        return_value=_FakeClient(),
    ):
        graph = LiteTradingGraph(
            selected_analysts=["market", "news", "fundamentals"],
            config={
                "project_dir": ".",
                "llm_provider": "deepseek",
                "deep_think_llm": "fake-deep",
                "quick_think_llm": "fake-quick",
            },
        )

    try:
        assert ("Msg Clear Market", "Decision Manager") not in graph.graph.builder.edges
        assert ("Msg Clear News", "Decision Manager") not in graph.graph.builder.edges
        assert ("Msg Clear Fundamentals", "Decision Manager") not in graph.graph.builder.edges
        assert (
            ("Msg Clear Market", "Msg Clear News", "Msg Clear Fundamentals"),
            "Decision Manager",
        ) in graph.graph.builder.waiting_edges
    finally:
        graph.stop_observers()


def test_lite_graph_uses_market_analyst_fast() -> None:
    class _FakeClient:
        def get_llm(self):
            return object()

    with patch(
        "tradingagents.graph.lite_trading_graph.create_llm_client",
        return_value=_FakeClient(),
    ):
        graph = LiteTradingGraph(
            selected_analysts=["market", "news", "fundamentals"],
            config={
                "project_dir": ".",
                "llm_provider": "deepseek",
                "deep_think_llm": "fake-deep",
                "quick_think_llm": "fake-quick",
            },
        )

    try:
        market_node = graph.graph.builder.nodes["Market Analyst"].runnable.func
        branch_node = next(
            value.cell_contents
            for value in market_node.__closure__ or []
            if callable(value.cell_contents)
            and getattr(value.cell_contents, "__name__", "") == "branch_node"
        )
        analyst_node = next(
            value.cell_contents
            for value in branch_node.__closure__ or []
            if callable(value.cell_contents)
            and getattr(value.cell_contents, "__name__", "") == "market_analyst_fast_node"
        )
        assert "market_analyst_fast.py" in analyst_node.__code__.co_filename
    finally:
        graph.stop_observers()


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
