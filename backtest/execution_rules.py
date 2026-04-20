from __future__ import annotations

from dataclasses import replace

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
    exit_signal_date: str | None = None,
    exit_signal_action: str | None = None,
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
        exit_signal_date=exit_signal_date,
        exit_signal_action=exit_signal_action,
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


def _find_next_bar_index(frame: pd.DataFrame, trade_date: pd.Timestamp) -> int | None:
    future = frame.index[frame["Date"] > trade_date]
    if len(future) == 0:
        return None
    return int(future[0])


def _plan_buy_signal(
    signal: ReportSignal,
    frame: pd.DataFrame,
    *,
    max_holding_days: int,
) -> tuple[SimulatedTrade, dict | None]:
    trade_date = pd.Timestamp(signal.trade_date)
    future = frame[frame["Date"] > trade_date].reset_index()
    if future.empty:
        return _empty_trade(signal, status="no_data", exit_reason="no_future_bars"), None

    entry_row_index: int | None = None
    entry_price: float | None = None
    for _, row in future.iterrows():
        frame_index = int(row["index"])
        if signal.action == "buy_now":
            entry_row_index = frame_index
            entry_price = _select_entry_price(row, signal)
            break

        if (
            signal.invalidation_price is not None
            and float(row["Low"]) <= signal.invalidation_price
            and signal.entry_zone_low is not None
            and float(row["Open"]) < signal.entry_zone_low
        ):
            return (
                _empty_trade(signal, status="expired", exit_reason="pre_entry_invalidation"),
                None,
            )

        in_entry_zone = (
            signal.entry_zone_low is not None
            and signal.entry_zone_high is not None
            and float(row["Low"]) <= signal.entry_zone_high
            and float(row["High"]) >= signal.entry_zone_low
        )
        if in_entry_zone:
            entry_row_index = frame_index
            entry_price = _select_entry_price(row, signal)
            break

        if signal.invalidation_price is not None and float(row["Close"]) <= signal.invalidation_price:
            return (
                _empty_trade(signal, status="expired", exit_reason="pre_entry_invalidation"),
                None,
            )

    if entry_row_index is None or entry_price is None:
        return _empty_trade(signal, status="expired", exit_reason="entry_not_triggered"), None

    entry_row = frame.iloc[entry_row_index]
    placeholder = SimulatedTrade(
        ticker=signal.ticker,
        trade_date=signal.trade_date,
        action=signal.action,
        status="open",
        entry_date=entry_row["Date"].strftime("%Y-%m-%d"),
        entry_price=round(entry_price, 4),
        exit_date=None,
        exit_price=None,
        exit_reason="position_open",
        holding_days=None,
        return_pct=None,
        reference_price=signal.reference_price,
        entry_style=signal.entry_style,
        entry_zone_low=signal.entry_zone_low,
        entry_zone_high=signal.entry_zone_high,
        invalidation_price=signal.invalidation_price,
        report_path=str(signal.report_path) if signal.report_path else None,
    )
    return placeholder, {
        "signal": signal,
        "entry_idx": entry_row_index,
        "entry_date": entry_row["Date"],
        "entry_price": float(entry_price),
        "stop_price": signal.invalidation_price,
        "max_exit_idx": min(entry_row_index + max_holding_days - 1, len(frame) - 1),
    }


def _plan_sell_signal(signal: ReportSignal, frame: pd.DataFrame) -> tuple[SimulatedTrade, dict | None]:
    next_bar_index = _find_next_bar_index(frame, pd.Timestamp(signal.trade_date))
    if next_bar_index is None:
        return _empty_trade(signal, status="no_data", exit_reason="no_future_bars"), None

    row = frame.iloc[next_bar_index]
    placeholder = SimulatedTrade(
        ticker=signal.ticker,
        trade_date=signal.trade_date,
        action=signal.action,
        status="pending",
        entry_date=None,
        entry_price=None,
        exit_date=row["Date"].strftime("%Y-%m-%d"),
        exit_price=round(float(row["Open"]), 4),
        exit_reason="awaiting_position",
        holding_days=None,
        return_pct=None,
        reference_price=signal.reference_price,
        entry_style=signal.entry_style,
        entry_zone_low=signal.entry_zone_low,
        entry_zone_high=signal.entry_zone_high,
        invalidation_price=signal.invalidation_price,
        report_path=str(signal.report_path) if signal.report_path else None,
    )
    return placeholder, {
        "signal": signal,
        "sell_idx": next_bar_index,
        "sell_date": row["Date"],
        "sell_price": float(row["Open"]),
    }


def simulate_signals(
    signals: list[ReportSignal],
    ohlcv: pd.DataFrame,
    *,
    max_holding_days: int = 60,
) -> list[SimulatedTrade]:
    frame = _normalize_ohlcv(ohlcv)
    ordered = sorted(enumerate(signals), key=lambda item: (item[1].trade_date, item[0]))
    trade_rows: list[SimulatedTrade | None] = [None] * len(signals)
    buy_plans: list[dict] = []
    sell_plans: list[dict] = []

    for original_index, signal in ordered:
        if signal.action == "hold":
            trade_rows[original_index] = _empty_trade(signal, status="skipped", exit_reason="action_hold")
            continue

        if signal.action == "sell":
            placeholder, plan = _plan_sell_signal(signal, frame)
            trade_rows[original_index] = placeholder
            if plan is not None:
                plan["row_index"] = original_index
                sell_plans.append(plan)
            continue

        placeholder, plan = _plan_buy_signal(signal, frame, max_holding_days=max_holding_days)
        trade_rows[original_index] = placeholder
        if plan is not None:
            plan["row_index"] = original_index
            buy_plans.append(plan)

    buys_by_entry: dict[int, list[dict]] = {}
    for plan in buy_plans:
        buys_by_entry.setdefault(plan["entry_idx"], []).append(plan)

    sells_by_day: dict[int, list[dict]] = {}
    for plan in sell_plans:
        sells_by_day.setdefault(plan["sell_idx"], []).append(plan)

    open_positions: list[dict] = []

    for day_idx in range(len(frame)):
        row = frame.iloc[day_idx]

        for sell_plan in sells_by_day.get(day_idx, []):
            sell_signal = sell_plan["signal"]
            if not open_positions:
                trade_rows[sell_plan["row_index"]] = _empty_trade(
                    sell_signal,
                    status="skipped",
                    exit_reason="action_sell_no_position",
                )
                continue

            position = open_positions.pop(0)
            entry_signal = position["signal"]
            trade_rows[position["row_index"]] = _build_trade(
                entry_signal,
                entry_date=position["entry_date"],
                entry_price=position["entry_price"],
                exit_date=sell_plan["sell_date"],
                exit_price=sell_plan["sell_price"],
                exit_reason="sell_signal",
                exit_signal_date=sell_signal.trade_date,
                exit_signal_action=sell_signal.action,
            )
            trade_rows[sell_plan["row_index"]] = replace(
                trade_rows[sell_plan["row_index"]],
                status="triggered_exit",
                entry_date=position["entry_date"].strftime("%Y-%m-%d"),
                entry_price=round(position["entry_price"], 4),
                exit_reason="closed_position_fifo",
                holding_days=max((sell_plan["sell_date"] - position["entry_date"]).days, 0),
            )

        for buy_plan in buys_by_entry.get(day_idx, []):
            open_positions.append(buy_plan)

        still_open: list[dict] = []
        for position in open_positions:
            signal = position["signal"]
            if (
                position["stop_price"] is not None
                and float(row["Low"]) <= position["stop_price"]
                and day_idx >= position["entry_idx"]
            ):
                trade_rows[position["row_index"]] = _build_trade(
                    signal,
                    entry_date=position["entry_date"],
                    entry_price=position["entry_price"],
                    exit_date=row["Date"],
                    exit_price=position["stop_price"],
                    exit_reason="stop_loss",
                )
                continue

            if day_idx >= position["max_exit_idx"]:
                exit_reason = "max_holding_period" if day_idx < len(frame) - 1 else "window_end"
                trade_rows[position["row_index"]] = _build_trade(
                    signal,
                    entry_date=position["entry_date"],
                    entry_price=position["entry_price"],
                    exit_date=row["Date"],
                    exit_price=float(row["Close"]),
                    exit_reason=exit_reason,
                )
                continue

            still_open.append(position)

        open_positions = still_open

    for position in open_positions:
        row = frame.iloc[-1]
        trade_rows[position["row_index"]] = _build_trade(
            position["signal"],
            entry_date=position["entry_date"],
            entry_price=position["entry_price"],
            exit_date=row["Date"],
            exit_price=float(row["Close"]),
            exit_reason="window_end",
        )

    unresolved = [idx for idx, trade in enumerate(trade_rows) if trade is None]
    if unresolved:
        raise RuntimeError(f"Missing simulated trades for rows: {unresolved}")

    return [trade for trade in trade_rows if trade is not None]


def simulate_trade(
    signal: ReportSignal,
    ohlcv: pd.DataFrame,
    *,
    max_holding_days: int = 60,
) -> SimulatedTrade:
    return simulate_signals([signal], ohlcv, max_holding_days=max_holding_days)[0]
