from __future__ import annotations

import pandas as pd

from backtest.execution_rules import simulate_trade
from backtest.models import ReportSignal


def _sample_ohlcv() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"Date": "2026-02-24", "Open": 29.0, "High": 29.5, "Low": 28.4, "Close": 28.8},
            {"Date": "2026-02-25", "Open": 26.2, "High": 26.4, "Low": 24.9, "Close": 25.4},
            {"Date": "2026-02-26", "Open": 25.8, "High": 27.6, "Low": 25.5, "Close": 27.0},
            {"Date": "2026-02-27", "Open": 27.4, "High": 28.0, "Low": 27.1, "Close": 27.8},
        ]
    )


def test_simulate_trade_enters_pullback_zone_and_exits_on_window_end() -> None:
    signal = ReportSignal(
        ticker="AXTI",
        trade_date="2026-02-23",
        action="buy_on_pullback",
        reference_price=29.68,
        reference_price_text="29.68美元",
        entry_style="等待价格回调至24.50-25.50美元关键支撑区间",
        entry_zone_low=24.5,
        entry_zone_high=25.5,
        invalidation_price=23.2,
        invalidation_texts=["股价放量跌破23.20美元支撑位"],
    )

    trade = simulate_trade(signal, _sample_ohlcv(), max_holding_days=3)

    assert trade.status == "triggered"
    assert trade.entry_date == "2026-02-25"
    assert trade.entry_price == 25.5
    assert trade.exit_date == "2026-02-27"
    assert trade.exit_reason == "window_end"
    assert trade.return_pct is not None


def test_simulate_trade_skips_hold_action() -> None:
    signal = ReportSignal(
        ticker="AXTI",
        trade_date="2026-04-17",
        action="hold",
        reference_price=81.78,
        reference_price_text="81.78美元",
        entry_style="保持观望",
        entry_zone_low=None,
        entry_zone_high=None,
        invalidation_price=None,
        invalidation_texts=[],
    )

    trade = simulate_trade(signal, _sample_ohlcv(), max_holding_days=3)

    assert trade.status == "skipped"
    assert trade.exit_reason == "action_hold"
