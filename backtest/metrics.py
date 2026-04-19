from __future__ import annotations

from statistics import median

from .models import BacktestSummary, SimulatedTrade


def _action_summary(trades: list[SimulatedTrade], action: str) -> dict[str, float | int | None]:
    subset = [trade for trade in trades if trade.action == action]
    realized = [trade.return_pct for trade in subset if trade.return_pct is not None]
    wins = sum(1 for value in realized if value > 0)
    return {
        "signal_count": len(subset),
        "trade_count": len(realized),
        "win_rate": round((wins / len(realized)) * 100, 4) if realized else None,
        "avg_return": round(sum(realized) / len(realized), 4) if realized else None,
    }


def summarize_backtest(trades: list[SimulatedTrade]) -> BacktestSummary:
    realized = [trade.return_pct for trade in trades if trade.return_pct is not None]
    wins = sum(1 for value in realized if value > 0)
    actions = sorted({trade.action for trade in trades})
    by_action = {action: _action_summary(trades, action) for action in actions}
    return BacktestSummary(
        signal_count=len(trades),
        trade_count=len(realized),
        triggered_trade_count=sum(1 for trade in trades if trade.status == "triggered"),
        win_rate=round((wins / len(realized)) * 100, 4) if realized else None,
        avg_return=round(sum(realized) / len(realized), 4) if realized else None,
        median_return=round(median(realized), 4) if realized else None,
        max_return=round(max(realized), 4) if realized else None,
        min_return=round(min(realized), 4) if realized else None,
        by_action=by_action,
    )
