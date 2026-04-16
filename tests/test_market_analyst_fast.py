from __future__ import annotations

from datetime import date

from tradingagents.agents.analysts.market_analyst_fast import _parse_trade_date


def test_parse_trade_date_accepts_compact_format() -> None:
    assert _parse_trade_date("20260417") == date(2026, 4, 17)


def test_parse_trade_date_accepts_iso_format() -> None:
    assert _parse_trade_date("2026-04-17") == date(2026, 4, 17)
