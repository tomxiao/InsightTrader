from __future__ import annotations

import argparse
import csv
import json
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True)
class LabelThresholds:
    buy_horizon_days: int
    sell_horizon_days: int
    hold_horizon_days: int
    sell_good_threshold_pct: float
    sell_bad_threshold_pct: float
    hold_flat_threshold_pct: float
    hold_miss_threshold_pct: float


@dataclass(frozen=True)
class SignalLabel:
    trade_date: str
    action: str
    label: str
    metric_name: str | None
    metric_value_pct: float | None
    note: str
    report_path: str | None

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        if self.metric_value_pct is not None:
            payload["metric_value_pct"] = round(self.metric_value_pct, 4)
        return payload


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Label daily backtest signals as good_case, bad_case, or unclear.")
    parser.add_argument("--result-dir", required=True, help="Directory containing signals.csv, trades.csv, summary.json, and *-ohlcv.csv.")
    parser.add_argument("--buy-horizon-days", type=int, default=3, help="Future trading days used for buy labels when realized return is unavailable.")
    parser.add_argument("--sell-horizon-days", type=int, default=3, help="Future trading days used for sell labels.")
    parser.add_argument("--hold-horizon-days", type=int, default=3, help="Future trading days used for hold labels.")
    parser.add_argument("--sell-good-threshold-pct", type=float, default=-2.0, help="sell is good when ret_Nd is at or below this threshold.")
    parser.add_argument("--sell-bad-threshold-pct", type=float, default=2.0, help="sell is bad when ret_Nd is at or above this threshold.")
    parser.add_argument("--hold-flat-threshold-pct", type=float, default=2.0, help="hold is good when abs(ret_Nd) is at or below this threshold.")
    parser.add_argument("--hold-miss-threshold-pct", type=float, default=5.0, help="hold is bad when abs(ret_Nd) is at or above this threshold.")
    return parser


def _load_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _find_ohlcv_csv(result_dir: Path) -> Path:
    matches = sorted(result_dir.glob("*-ohlcv.csv"))
    if not matches:
        raise FileNotFoundError(f"No *-ohlcv.csv file found under {result_dir}")
    return matches[0]


def _future_return_pct(
    *,
    price_by_date: dict[str, dict[str, str]],
    ordered_dates: list[str],
    date_index: dict[str, int],
    trade_date: str,
    reference_price: float,
    horizon_days: int,
) -> tuple[float | None, str | None]:
    start_index = date_index.get(trade_date)
    if start_index is None:
        return None, None
    future_dates = ordered_dates[start_index + 1 : start_index + 1 + max(horizon_days, 0)]
    if not future_dates:
        return None, None
    end_date = future_dates[-1]
    end_close = float(price_by_date[end_date]["Close"])
    return ((end_close / reference_price) - 1.0) * 100.0, end_date


def _label_signal(
    *,
    signal: dict[str, str],
    trade_row: dict[str, str] | None,
    price_by_date: dict[str, dict[str, str]],
    ordered_dates: list[str],
    date_index: dict[str, int],
    thresholds: LabelThresholds,
) -> SignalLabel:
    trade_date = signal["trade_date"]
    action = signal["action"]
    report_path = signal.get("report_path")

    if action == "buy_on_pullback" and trade_row:
        status = (trade_row.get("status") or "").strip()
        realized_return = trade_row.get("return_pct")
        if status == "triggered" and realized_return not in {"", None}:
            realized = float(realized_return)
            return SignalLabel(
                trade_date=trade_date,
                action=action,
                label="good_case" if realized > 0 else "bad_case",
                metric_name="realized_return_pct",
                metric_value_pct=realized,
                note="Triggered and exited profitable." if realized > 0 else "Triggered and lost money.",
                report_path=report_path,
            )

    raw_reference = signal.get("reference_price")
    if raw_reference in {"", None}:
        raw_reference = price_by_date[trade_date]["Close"]
    reference_price = float(raw_reference)

    if action == "buy_on_pullback":
        future_return, _ = _future_return_pct(
            price_by_date=price_by_date,
            ordered_dates=ordered_dates,
            date_index=date_index,
            trade_date=trade_date,
            reference_price=reference_price,
            horizon_days=thresholds.buy_horizon_days,
        )
        if future_return is None:
            return SignalLabel(trade_date, action, "unclear", None, None, "No future bars in test window.", report_path)
        return SignalLabel(
            trade_date=trade_date,
            action=action,
            label="good_case" if future_return > 0 else "bad_case",
            metric_name=f"ret_{thresholds.buy_horizon_days}d_pct",
            metric_value_pct=future_return,
            note="Buy signal was followed by price appreciation." if future_return > 0 else "Buy signal was followed by price weakness.",
            report_path=report_path,
        )

    if action == "sell":
        future_return, _ = _future_return_pct(
            price_by_date=price_by_date,
            ordered_dates=ordered_dates,
            date_index=date_index,
            trade_date=trade_date,
            reference_price=reference_price,
            horizon_days=thresholds.sell_horizon_days,
        )
        if future_return is None:
            return SignalLabel(trade_date, action, "unclear", None, None, "No future bars in test window.", report_path)
        if future_return <= thresholds.sell_good_threshold_pct:
            label = "good_case"
            note = "Price fell after sell signal."
        elif future_return >= thresholds.sell_bad_threshold_pct:
            label = "bad_case"
            note = "Price rose after sell signal."
        else:
            label = "unclear"
            note = "Post-signal move was too small to judge."
        return SignalLabel(
            trade_date=trade_date,
            action=action,
            label=label,
            metric_name=f"ret_{thresholds.sell_horizon_days}d_pct",
            metric_value_pct=future_return,
            note=note,
            report_path=report_path,
        )

    if action == "hold":
        future_return, _ = _future_return_pct(
            price_by_date=price_by_date,
            ordered_dates=ordered_dates,
            date_index=date_index,
            trade_date=trade_date,
            reference_price=reference_price,
            horizon_days=thresholds.hold_horizon_days,
        )
        if future_return is None:
            return SignalLabel(trade_date, action, "unclear", None, None, "No future bars in test window.", report_path)
        abs_return = abs(future_return)
        if abs_return <= thresholds.hold_flat_threshold_pct:
            label = "good_case"
            note = "Hold matched sideways price action."
        elif abs_return >= thresholds.hold_miss_threshold_pct:
            label = "bad_case"
            note = "Hold missed a meaningful move."
        else:
            label = "unclear"
            note = "Move was moderate; not a clear hold success/failure."
        return SignalLabel(
            trade_date=trade_date,
            action=action,
            label=label,
            metric_name=f"ret_{thresholds.hold_horizon_days}d_pct",
            metric_value_pct=future_return,
            note=note,
            report_path=report_path,
        )

    return SignalLabel(trade_date, action, "unclear", None, None, "Unsupported action for labeling.", report_path)


def _write_csv(path: Path, labels: list[SignalLabel]) -> None:
    if not labels:
        path.write_text("", encoding="utf-8")
        return
    rows = [item.to_dict() for item in labels]
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def _write_markdown(path: Path, labels: list[SignalLabel], thresholds: LabelThresholds, result_dir: Path) -> None:
    counts: dict[str, int] = {"good_case": 0, "bad_case": 0, "unclear": 0}
    for item in labels:
        counts[item.label] = counts.get(item.label, 0) + 1

    lines = [
        f"# {result_dir.name} Signal Case Labels",
        "",
        "## Labeling Rule",
        "",
        f"- `buy_on_pullback`: realized return if triggered; otherwise `{thresholds.buy_horizon_days}`-day future return fallback",
        f"- `sell`: `good_case` when `ret_{thresholds.sell_horizon_days}d <= {thresholds.sell_good_threshold_pct:.1f}%`, `bad_case` when `ret_{thresholds.sell_horizon_days}d >= {thresholds.sell_bad_threshold_pct:.1f}%`",
        f"- `hold`: `good_case` when `abs(ret_{thresholds.hold_horizon_days}d) <= {thresholds.hold_flat_threshold_pct:.1f}%`, `bad_case` when `abs(ret_{thresholds.hold_horizon_days}d) >= {thresholds.hold_miss_threshold_pct:.1f}%`",
        "",
        "## Summary",
        "",
        f"- `good_case`: {counts.get('good_case', 0)}",
        f"- `bad_case`: {counts.get('bad_case', 0)}",
        f"- `unclear`: {counts.get('unclear', 0)}",
        "",
        "## Daily Labels",
        "",
        "| trade_date | action | label | metric | note |",
        "| --- | --- | --- | --- | --- |",
    ]
    for item in labels:
        metric = ""
        if item.metric_name and item.metric_value_pct is not None:
            metric = f"{item.metric_name}={item.metric_value_pct:.2f}%"
        lines.append(f"| {item.trade_date} | {item.action} | {item.label} | {metric} | {item.note} |")

    bad_cases = [item for item in labels if item.label == "bad_case"]
    lines.extend(["", "## Immediate Bad Cases To Review", ""])
    if not bad_cases:
        lines.append("- None")
    else:
        for item in bad_cases:
            lines.append(f"- `{item.trade_date}` `{item.action}`")
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    args = build_parser().parse_args()
    result_dir = Path(args.result_dir)
    thresholds = LabelThresholds(
        buy_horizon_days=args.buy_horizon_days,
        sell_horizon_days=args.sell_horizon_days,
        hold_horizon_days=args.hold_horizon_days,
        sell_good_threshold_pct=args.sell_good_threshold_pct,
        sell_bad_threshold_pct=args.sell_bad_threshold_pct,
        hold_flat_threshold_pct=args.hold_flat_threshold_pct,
        hold_miss_threshold_pct=args.hold_miss_threshold_pct,
    )

    signals = _load_csv_rows(result_dir / "signals.csv")
    trades = {row["trade_date"]: row for row in _load_csv_rows(result_dir / "trades.csv")}
    ohlcv_rows = _load_csv_rows(_find_ohlcv_csv(result_dir))
    ordered_dates = [row["Date"] for row in ohlcv_rows]
    price_by_date = {row["Date"]: row for row in ohlcv_rows}
    date_index = {trade_date: index for index, trade_date in enumerate(ordered_dates)}

    labels = [
        _label_signal(
            signal=signal,
            trade_row=trades.get(signal["trade_date"]),
            price_by_date=price_by_date,
            ordered_dates=ordered_dates,
            date_index=date_index,
            thresholds=thresholds,
        )
        for signal in signals
    ]

    _write_csv(result_dir / "signal_case_labels.csv", labels)
    _write_markdown(result_dir / "signal_case_labels.md", labels, thresholds, result_dir)

    summary = {
        "result_dir": str(result_dir),
        "label_counts": {
            "good_case": sum(1 for item in labels if item.label == "good_case"),
            "bad_case": sum(1 for item in labels if item.label == "bad_case"),
            "unclear": sum(1 for item in labels if item.label == "unclear"),
        },
        "thresholds": asdict(thresholds),
    }
    (result_dir / "signal_case_label_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
