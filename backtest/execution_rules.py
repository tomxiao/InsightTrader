from __future__ import annotations

import pandas as pd

from .models import ReportSignal, SimulatedTrade


def _normalize_ohlcv(ohlcv: pd.DataFrame) -> pd.DataFrame:
    frame = ohlcv.copy()
    if "Date" not in frame.columns:
        raise ValueError("OHLCV data must include a `Date` column")
    frame["Date"] = pd.to_datetime(frame["Date"], errors="coerce")
    frame = frame.dropna(subset=["Date"]).sort_values("Date").reset_index(drop=True)
    for column in ("Open", "High", "Low", "Close"):
        if column not in frame.columns:
            raise ValueError(f"OHLCV data must include `{column}`")
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    return frame.dropna(subset=["Open", "High", "Low", "Close"])


def _empty_trade(signal: ReportSignal, *, status: str, exit_reason: str) -> SimulatedTrade:
    return SimulatedTrade(
        ticker=signal.ticker,
        trade_date=signal.trade_date,
        action=signal.action,
        status=status,
        entry_date=None,
        entry_price=None,
        exit_date=None,
        exit_price=None,
        exit_reason=exit_reason,
        holding_days=None,
        return_pct=None,
        reference_price=signal.reference_price,
        entry_style=signal.entry_style,
        entry_zone_low=signal.entry_zone_low,
        entry_zone_high=signal.entry_zone_high,
        invalidation_price=signal.invalidation_price,
        report_path=str(signal.report_path) if signal.report_path else None,
    )


def _build_trade(
    signal: ReportSignal,
    *,
    entry_date: pd.Timestamp,
    entry_price: float,
    exit_date: pd.Timestamp,
    exit_price: float,
    exit_reason: str,
) -> SimulatedTrade:
    holding_days = max((exit_date - entry_date).days, 0)
    return_pct = ((exit_price / entry_price) - 1.0) * 100 if entry_price else None
    return SimulatedTrade(
        ticker=signal.ticker,
        trade_date=signal.trade_date,
        action=signal.action,
        status="triggered",
        entry_date=entry_date.strftime("%Y-%m-%d"),
        entry_price=round(entry_price, 4),
        exit_date=exit_date.strftime("%Y-%m-%d"),
        exit_price=round(exit_price, 4),
        exit_reason=exit_reason,
        holding_days=holding_days,
        return_pct=round(return_pct, 4) if return_pct is not None else None,
        reference_price=signal.reference_price,
        entry_style=signal.entry_style,
        entry_zone_low=signal.entry_zone_low,
        entry_zone_high=signal.entry_zone_high,
        invalidation_price=signal.invalidation_price,
        report_path=str(signal.report_path) if signal.report_path else None,
    )


def _select_entry_price(row: pd.Series, signal: ReportSignal) -> float:
    if signal.action == "buy_now":
        return float(row["Open"])
    if signal.entry_zone_low is not None and signal.entry_zone_high is not None:
        if row["Open"] < signal.entry_zone_low:
            return signal.entry_zone_low
        if row["Open"] > signal.entry_zone_high:
            return signal.entry_zone_high
        return float(row["Open"])
    return float(row["Open"])


def simulate_trade(
    signal: ReportSignal,
    ohlcv: pd.DataFrame,
    *,
    max_holding_days: int = 60,
) -> SimulatedTrade:
    if signal.action in {"hold", "sell"}:
        return _empty_trade(signal, status="skipped", exit_reason=f"action_{signal.action}")

    frame = _normalize_ohlcv(ohlcv)
    trade_date = pd.Timestamp(signal.trade_date)
    future = frame[frame["Date"] > trade_date].reset_index(drop=True)
    if future.empty:
        return _empty_trade(signal, status="no_data", exit_reason="no_future_bars")

    entry_row_index: int | None = None
    entry_price: float | None = None
    for idx, (_, row) in enumerate(future.iterrows()):
        if signal.action == "buy_now":
            entry_row_index = idx
            entry_price = _select_entry_price(row, signal)
            break

        if (
            signal.invalidation_price is not None
            and float(row["Low"]) <= signal.invalidation_price
            and signal.entry_zone_low is not None
            and float(row["Open"]) < signal.entry_zone_low
        ):
            return _empty_trade(signal, status="expired", exit_reason="pre_entry_invalidation")

        in_entry_zone = (
            signal.entry_zone_low is not None
            and signal.entry_zone_high is not None
            and float(row["Low"]) <= signal.entry_zone_high
            and float(row["High"]) >= signal.entry_zone_low
        )
        if in_entry_zone:
            entry_row_index = idx
            entry_price = _select_entry_price(row, signal)
            break

        if signal.invalidation_price is not None and float(row["Close"]) <= signal.invalidation_price:
            return _empty_trade(signal, status="expired", exit_reason="pre_entry_invalidation")

    if entry_row_index is None or entry_price is None:
        return _empty_trade(signal, status="expired", exit_reason="entry_not_triggered")

    exit_idx = min(entry_row_index + max_holding_days - 1, len(future) - 1)
    for idx in range(entry_row_index, exit_idx + 1):
        row = future.iloc[idx]
        if signal.invalidation_price is not None and float(row["Low"]) <= signal.invalidation_price:
            return _build_trade(
                signal,
                entry_date=future.iloc[entry_row_index]["Date"],
                entry_price=entry_price,
                exit_date=row["Date"],
                exit_price=signal.invalidation_price,
                exit_reason="stop_loss",
            )

    exit_row = future.iloc[exit_idx]
    exit_reason = "max_holding_period" if exit_idx < len(future) - 1 else "window_end"
    return _build_trade(
        signal,
        entry_date=future.iloc[entry_row_index]["Date"],
        entry_price=entry_price,
        exit_date=exit_row["Date"],
        exit_price=float(exit_row["Close"]),
        exit_reason=exit_reason,
    )
