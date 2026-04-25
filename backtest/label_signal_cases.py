from __future__ import annotations

import argparse
import csv
import json
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True)
class LabelThresholds:
    buy_horizon_days: int
    buy_good_threshold_pct: float
    buy_bad_threshold_pct: float
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


LABEL_DISPLAY = {
    "good_case": "好样本",
    "bad_case": "坏样本",
    "unclear": "待判断",
}

ACTION_DISPLAY = {
    "buy_now": "确信买入",
    "buy_on_pullback": "择机买入",
    "hold": "保持观望",
    "sell": "建议卖出",
}


def _label_display(label: str) -> str:
    return LABEL_DISPLAY.get(label, label)


def _action_display(action: str) -> str:
    return ACTION_DISPLAY.get(action, action)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Label daily backtest signals as good_case, bad_case, or unclear.")
    parser.add_argument("--result-dir", required=True, help="Directory containing signals.csv, trades.csv, summary.json, and *-ohlcv.csv.")
    parser.add_argument("--buy-horizon-days", type=int, default=3, help="Future trading days used for buy labels when realized return is unavailable.")
    parser.add_argument("--buy-good-threshold-pct", type=float, default=2.0, help="buy is good when ret_Nd is at or above this threshold.")
    parser.add_argument("--buy-bad-threshold-pct", type=float, default=-2.0, help="buy is bad when ret_Nd is at or below this threshold.")
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


def _future_average_return_pct(
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
    future_closes = [float(price_by_date[future_date]["Close"]) for future_date in future_dates]
    average_close = sum(future_closes) / len(future_closes)
    end_date = future_dates[-1]
    return ((average_close / reference_price) - 1.0) * 100.0, end_date


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

    raw_reference = signal.get("reference_price")
    if raw_reference in {"", None}:
        raw_reference = price_by_date[trade_date]["Close"]
    reference_price = float(raw_reference)

    if action in {"buy_now", "buy_on_pullback"}:
        future_return, _ = _future_average_return_pct(
            price_by_date=price_by_date,
            ordered_dates=ordered_dates,
            date_index=date_index,
            trade_date=trade_date,
            reference_price=reference_price,
            horizon_days=thresholds.buy_horizon_days,
        )
        if future_return is None:
            return SignalLabel(trade_date, action, "unclear", None, None, "回测窗口内缺少足够的后续 K 线。", report_path)
        if future_return >= thresholds.buy_good_threshold_pct:
            label = "good_case"
            note = "买入信号后短期价格明显上涨。"
        elif future_return <= thresholds.buy_bad_threshold_pct:
            label = "bad_case"
            note = "买入信号后短期价格明显走弱。"
        else:
            label = "unclear"
            note = "买入信号后波动幅度较小，暂不足以下结论。"
        return SignalLabel(
            trade_date=trade_date,
            action=action,
            label=label,
            metric_name=f"avg_ret_{thresholds.buy_horizon_days}d_pct",
            metric_value_pct=future_return,
            note=note,
            report_path=report_path,
        )

    if action == "sell":
        future_return, _ = _future_average_return_pct(
            price_by_date=price_by_date,
            ordered_dates=ordered_dates,
            date_index=date_index,
            trade_date=trade_date,
            reference_price=reference_price,
            horizon_days=thresholds.sell_horizon_days,
        )
        if future_return is None:
            return SignalLabel(trade_date, action, "unclear", None, None, "回测窗口内缺少足够的后续 K 线。", report_path)
        if future_return <= thresholds.sell_good_threshold_pct:
            label = "good_case"
            note = "卖出信号后价格下跌。"
        elif future_return >= thresholds.sell_bad_threshold_pct:
            label = "bad_case"
            note = "卖出信号后价格上涨。"
        else:
            label = "unclear"
            note = "信号后波动幅度较小，暂不足以下结论。"
        return SignalLabel(
            trade_date=trade_date,
            action=action,
            label=label,
            metric_name=f"avg_ret_{thresholds.sell_horizon_days}d_pct",
            metric_value_pct=future_return,
            note=note,
            report_path=report_path,
        )

    if action == "hold":
        future_return, _ = _future_average_return_pct(
            price_by_date=price_by_date,
            ordered_dates=ordered_dates,
            date_index=date_index,
            trade_date=trade_date,
            reference_price=reference_price,
            horizon_days=thresholds.hold_horizon_days,
        )
        if future_return is None:
            return SignalLabel(trade_date, action, "unclear", None, None, "回测窗口内缺少足够的后续 K 线。", report_path)
        abs_return = abs(future_return)
        if abs_return <= thresholds.hold_flat_threshold_pct:
            label = "good_case"
            note = "观望与后续横盘走势匹配。"
        elif abs_return >= thresholds.hold_miss_threshold_pct:
            label = "bad_case"
            note = "观望错过了明显行情。"
        else:
            label = "unclear"
            note = "后续波动中等，暂不适合直接判定观望对错。"
        return SignalLabel(
            trade_date=trade_date,
            action=action,
            label=label,
            metric_name=f"avg_ret_{thresholds.hold_horizon_days}d_pct",
            metric_value_pct=future_return,
            note=note,
            report_path=report_path,
        )

    return SignalLabel(trade_date, action, "unclear", None, None, "当前动作暂不支持自动标注。", report_path)


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
        f"# {result_dir.name} 信号样本标注",
        "",
        "## 标注规则",
        "",
        f"- `确信买入` / `择机买入`：使用未来 `{thresholds.buy_horizon_days}` 个交易日收盘均价计算 `avg_ret_{thresholds.buy_horizon_days}d`；当 `avg_ret_{thresholds.buy_horizon_days}d >= {thresholds.buy_good_threshold_pct:.1f}%` 记为“好样本”；当 `avg_ret_{thresholds.buy_horizon_days}d <= {thresholds.buy_bad_threshold_pct:.1f}%` 记为“坏样本”。",
        f"- `建议卖出`：使用未来 `{thresholds.sell_horizon_days}` 个交易日收盘均价计算 `avg_ret_{thresholds.sell_horizon_days}d`；当 `avg_ret_{thresholds.sell_horizon_days}d <= {thresholds.sell_good_threshold_pct:.1f}%` 记为“好样本”；当 `avg_ret_{thresholds.sell_horizon_days}d >= {thresholds.sell_bad_threshold_pct:.1f}%` 记为“坏样本”。",
        f"- `保持观望`：使用未来 `{thresholds.hold_horizon_days}` 个交易日收盘均价计算 `avg_ret_{thresholds.hold_horizon_days}d`；当 `abs(avg_ret_{thresholds.hold_horizon_days}d) <= {thresholds.hold_flat_threshold_pct:.1f}%` 记为“好样本”；当 `abs(avg_ret_{thresholds.hold_horizon_days}d) >= {thresholds.hold_miss_threshold_pct:.1f}%` 记为“坏样本”。",
        "- 当前标签体系只判断信号方向是否与后续短期平均价格方向一致，不评估成交质量、入场区间或执行结果。",
        "",
        "## 汇总",
        "",
        f"- `好样本`：{counts.get('good_case', 0)}",
        f"- `坏样本`：{counts.get('bad_case', 0)}",
        f"- `待判断`：{counts.get('unclear', 0)}",
        "",
        "## 每日标注",
        "",
        "| 日期 | 动作 | 标签 | 指标 | 说明 |",
        "| --- | --- | --- | --- | --- |",
    ]
    for item in labels:
        metric = ""
        if item.metric_name and item.metric_value_pct is not None:
            metric = f"{item.metric_name}={item.metric_value_pct:.2f}%"
        lines.append(
            f"| {item.trade_date} | {_action_display(item.action)} | {_label_display(item.label)} | {metric} | {item.note} |"
        )

    bad_cases = [item for item in labels if item.label == "bad_case"]
    lines.extend(["", "## 优先复盘的坏样本", ""])
    if not bad_cases:
        lines.append("- 无")
    else:
        for item in bad_cases:
            lines.append(f"- `{item.trade_date}` `{_action_display(item.action)}`")
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    args = build_parser().parse_args()
    result_dir = Path(args.result_dir)
    thresholds = LabelThresholds(
        buy_horizon_days=args.buy_horizon_days,
        buy_good_threshold_pct=args.buy_good_threshold_pct,
        buy_bad_threshold_pct=args.buy_bad_threshold_pct,
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
