from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from ta_service.adapters.result_mapper import (
    extract_executive_summary,
    save_report_to_disk,
)
from ta_service.callbacks.stats_handler import StatsCallbackHandler
from ta_service.config.settings import Settings
from ta_service.runtime.run_context import RunContext, build_run_context
from ta_service.runtime.status_mapper import resolve_stage_message
from tradingagents.dataflows.config import clear_runtime_context, set_runtime_context
from tradingagents.default_config import DEFAULT_CONFIG
from tradingagents.graph.trading_graph import TradingAgentsGraph
from tradingagents.observability import StageEventTracker

ANALYST_ORDER = ["market", "social", "news", "fundamentals"]
ANALYST_STAGE_MAP = {
    "market": ("analysts.market", "market_report"),
    "social": ("analysts.social", "sentiment_report"),
    "news": ("analysts.news", "news_report"),
    "fundamentals": ("analysts.fundamentals", "fundamentals_report"),
}

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class RunnerRequest:
    ticker: str
    trade_date: str
    selected_analysts: list[str]
    on_stage_change: Callable[[str], None] | None = field(default=None, compare=False, hash=False)
    on_node_change: Callable[[str, str], None] | None = field(
        default=None, compare=False, hash=False
    )


@dataclass(frozen=True)
class RunnerResult:
    run_context: RunContext
    final_state: dict
    executive_summary: str | None
    stats: dict
    report_dir: Path | None = None


class TradingAgentsRunner:
    def __init__(self, settings: Settings):
        self.settings = settings

    def build_runtime_diagnostics(self, payload: RunnerRequest) -> dict:
        config = self._build_config(Path(__file__).resolve())
        return {
            "request": {
                "ticker": payload.ticker,
                "tradeDate": payload.trade_date,
                "selectedAnalysts": payload.selected_analysts or ANALYST_ORDER,
            },
            "effectiveConfig": {
                "llm_provider": config.get("llm_provider"),
                "deep_think_llm": config.get("deep_think_llm"),
                "quick_think_llm": config.get("quick_think_llm"),
                "backend_url": config.get("backend_url"),
                "output_language": config.get("output_language"),
                "market_routing_enabled": config.get("market_routing_enabled"),
                "data_vendors": config.get("data_vendors"),
                "tool_vendors": config.get("tool_vendors"),
                "results_dir": config.get("results_dir"),
                "project_dir": config.get("project_dir"),
            },
            "envPresence": {
                "DEEPSEEK_API_KEY": bool(os.getenv("DEEPSEEK_API_KEY")),
                "OPENAI_API_KEY": bool(os.getenv("OPENAI_API_KEY")),
                "GOOGLE_API_KEY": bool(os.getenv("GOOGLE_API_KEY")),
                "ANTHROPIC_API_KEY": bool(os.getenv("ANTHROPIC_API_KEY")),
                "OPENROUTER_API_KEY": bool(os.getenv("OPENROUTER_API_KEY")),
                "XAI_API_KEY": bool(os.getenv("XAI_API_KEY")),
                "TUSHARE_TOKEN": bool(os.getenv("TUSHARE_TOKEN")),
                "FINNHUB_TOKEN": bool(os.getenv("FINNHUB_TOKEN")),
                "ALPHA_VANTAGE_API_KEY": bool(os.getenv("ALPHA_VANTAGE_API_KEY")),
                "FUTU_OPEND_HOST": bool(os.getenv("FUTU_OPEND_HOST")),
                "FUTU_OPEND_PORT": bool(os.getenv("FUTU_OPEND_PORT")),
            },
        }

    def run_analysis(self, payload: RunnerRequest) -> RunnerResult:
        run_context = build_run_context(
            settings=self.settings,
            ticker=payload.ticker,
            trade_date=payload.trade_date,
        )
        config = self._build_config(run_context.trace_dir)
        LOGGER.info(
            "starting TradingAgents run run_id=%s ticker=%s provider=%s deep_model=%s quick_model=%s backend_url=%s market_routing=%s",
            run_context.run_id,
            payload.ticker,
            config.get("llm_provider"),
            config.get("deep_think_llm"),
            config.get("quick_think_llm"),
            config.get("backend_url"),
            config.get("market_routing_enabled"),
        )
        stats_handler = StatsCallbackHandler()
        graph = TradingAgentsGraph(
            payload.selected_analysts or ANALYST_ORDER,
            config=config,
            debug=True,
            callbacks=[stats_handler],
        )
        if payload.on_node_change is not None:
            graph.node_tracker.on_node_started = payload.on_node_change
        stage_tracker = StageEventTracker(
            config=config,
            runtime_context={
                "run_id": run_context.run_id,
                "trace_dir": str(run_context.trace_dir),
                "ticker": payload.ticker,
                "trade_date": payload.trade_date,
                "run_started_at_iso": run_context.started_at.isoformat(),
                "run_dir_name": run_context.trace_dir.name,
            },
        )
        stage_tracker.start_watchdog()

        clear_runtime_context()
        set_runtime_context(
            run_id=run_context.run_id,
            trace_dir=str(run_context.trace_dir),
            ticker=payload.ticker,
            trade_date=payload.trade_date,
            run_started_at_iso=run_context.started_at.isoformat(),
            run_dir_name=run_context.trace_dir.name,
        )

        final_state: dict | None = None
        selected = payload.selected_analysts or ANALYST_ORDER
        last_stage_id: str | None = None

        def _notify_stage_change() -> None:
            nonlocal last_stage_id
            current = stage_tracker.current_stage_id
            if current and current != last_stage_id:
                last_stage_id = current
                if payload.on_stage_change:
                    try:
                        payload.on_stage_change(current)
                    except Exception:
                        pass

        stage_tracker.sync(self._build_stage_snapshot(selected, {}))
        _notify_stage_change()

        try:
            init_state = graph.propagator.create_initial_state(payload.ticker, payload.trade_date)
            args = graph.propagator.get_graph_args(callbacks=[stats_handler])
            accumulated: dict = {}

            for chunk in graph.graph.stream(init_state, **args):
                accumulated.update({key: value for key, value in chunk.items() if value})
                stage_tracker.sync(self._build_stage_snapshot(selected, accumulated))
                _notify_stage_change()
                final_state = chunk

            if final_state is None:
                raise RuntimeError("TradingAgents did not produce a final state")

            report_dir = save_report_to_disk(
                final_state,
                self.settings.reports_root / run_context.trace_dir.name,
            )
            return RunnerResult(
                run_context=run_context,
                final_state=final_state,
                executive_summary=extract_executive_summary(final_state),
                stats=stats_handler.get_stats(),
                report_dir=report_dir,
            )
        except Exception as exc:
            stage_tracker.mark_failed(exc)
            raise
        finally:
            stage_tracker.stop_watchdog()
            graph.stop_observers()
            clear_runtime_context()

    def _build_config(self, trace_dir: Path) -> dict:
        config = DEFAULT_CONFIG.copy()
        config["results_dir"] = str(self.settings.results_root)
        config["output_language"] = self.settings.default_output_language
        config["project_dir"] = str(Path(os.getcwd()))
        return config

    def _build_stage_snapshot(self, selected_analysts: list[str], state: dict) -> dict[str, str]:
        snapshot: dict[str, str] = {}
        active_set = [item for item in ANALYST_ORDER if item in selected_analysts]
        found_in_progress = False

        for analyst_key in active_set:
            stage_id, report_key = ANALYST_STAGE_MAP[analyst_key]
            if state.get(report_key):
                snapshot[stage_id] = "completed"
            elif not found_in_progress:
                snapshot[stage_id] = "in_progress"
                found_in_progress = True
            else:
                snapshot[stage_id] = "pending"

        if active_set and all(
            snapshot.get(ANALYST_STAGE_MAP[key][0]) == "completed" for key in active_set
        ):
            research_done = bool(state.get("investment_debate_state", {}).get("judge_decision"))
            snapshot["research.debate"] = "completed" if research_done else "in_progress"
            trader_done = bool(state.get("trader_investment_plan"))
            snapshot["trader.plan"] = (
                "completed" if trader_done else ("in_progress" if research_done else "pending")
            )
            risk_done = bool(state.get("risk_debate_state", {}).get("judge_decision"))
            snapshot["risk.debate"] = (
                "completed" if risk_done else ("in_progress" if trader_done else "pending")
            )
            portfolio_done = bool(state.get("final_trade_decision"))
            snapshot["portfolio.decision"] = (
                "completed"
                if portfolio_done
                else ("in_progress" if risk_done else "pending")
            )
        else:
            snapshot["research.debate"] = "pending"
            snapshot["trader.plan"] = "pending"
            snapshot["risk.debate"] = "pending"
            snapshot["portfolio.decision"] = "pending"

        return snapshot


def describe_stage(stage_id: str | None) -> str | None:
    return resolve_stage_message(stage_id)
