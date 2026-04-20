from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class ReportSignal:
    ticker: str
    trade_date: str
    action: str
    reference_price: float | None
    reference_price_text: str | None
    entry_style: str | None
    entry_zone_low: float | None
    entry_zone_high: float | None
    invalidation_price: float | None
    invalidation_texts: list[str] = field(default_factory=list)
    report_path: Path | None = None

    def to_dict(self) -> dict:
        payload = asdict(self)
        payload["report_path"] = str(self.report_path) if self.report_path else None
        return payload


@dataclass(frozen=True)
class SimulatedTrade:
    ticker: str
    trade_date: str
    action: str
    status: str
    entry_date: str | None
    entry_price: float | None
    exit_date: str | None
    exit_price: float | None
    exit_reason: str
    holding_days: int | None
    return_pct: float | None
    reference_price: float | None
    entry_style: str | None
    entry_zone_low: float | None
    entry_zone_high: float | None
    invalidation_price: float | None
    quantity: int = 1
    exit_signal_date: str | None = None
    exit_signal_action: str | None = None
    report_path: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class BacktestSummary:
    signal_count: int
    trade_count: int
    triggered_trade_count: int
    win_rate: float | None
    avg_return: float | None
    median_return: float | None
    max_return: float | None
    min_return: float | None
    by_action: dict[str, dict[str, float | int | None]]

    def to_dict(self) -> dict:
        return asdict(self)
