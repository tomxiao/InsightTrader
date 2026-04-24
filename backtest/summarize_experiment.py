from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Summarize one experiment across multiple ticker result directories.")
    parser.add_argument("--experiment-dir", required=True, help="Experiment directory containing tickers/<ticker>/result subdirectories.")
    return parser


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _read_label_counts(result_dir: Path) -> dict[str, int]:
    summary_path = result_dir / "signal_case_label_summary.json"
    if not summary_path.exists():
        return {"good_case": 0, "bad_case": 0, "unclear": 0}
    return _read_json(summary_path)["label_counts"]


def _count_actions(signals_csv: Path) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in _read_csv_rows(signals_csv):
        action = row["action"]
        counts[action] = counts.get(action, 0) + 1
    return counts


def _count_statuses(trades_csv: Path) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in _read_csv_rows(trades_csv):
        status = row["status"]
        counts[status] = counts.get(status, 0) + 1
    return counts


def _load_label_rows(result_dir: Path) -> dict[str, dict[str, str]]:
    labels_csv = result_dir / "signal_case_labels.csv"
    if not labels_csv.exists():
        return {}
    return {row["trade_date"]: row for row in _read_csv_rows(labels_csv)}


def _safe_accuracy(good: int, bad: int) -> float | None:
    denominator = good + bad
    if denominator <= 0:
        return None
    return good / denominator


def _bucket_value(row: dict[str, str], field_name: str, *, default: str = "未标注") -> str:
    value = (row.get(field_name) or "").strip()
    return value or default


def _build_bucket_summary(signal_rows: list[dict[str, str]], *, field_name: str) -> list[dict[str, object]]:
    buckets: dict[str, dict[str, object]] = {}
    for signal in signal_rows:
        key = _bucket_value(signal, field_name)
        bucket = buckets.setdefault(
            key,
            {
                "bucket": key,
                "signal_count": 0,
                "good_case": 0,
                "bad_case": 0,
                "unclear": 0,
                "actions": {},
            },
        )
        bucket["signal_count"] = int(bucket["signal_count"]) + 1
        action = signal.get("action") or "unknown"
        actions = bucket["actions"]
        actions[action] = actions.get(action, 0) + 1

        label = signal.get("label")
        if label in {"good_case", "bad_case", "unclear"}:
            bucket[label] = int(bucket[label]) + 1

    rows: list[dict[str, object]] = []
    for bucket in buckets.values():
        good = int(bucket["good_case"])
        bad = int(bucket["bad_case"])
        row = dict(bucket)
        row["accuracy"] = _safe_accuracy(good, bad)
        rows.append(row)
    rows.sort(
        key=lambda item: (
            -int(item["signal_count"]),
            str(item["bucket"]),
        )
    )
    return rows


def _format_accuracy(value: float | None) -> str:
    if value is None:
        return "-"
    return f"{value * 100:.1f}%"


def main() -> int:
    args = build_parser().parse_args()
    experiment_dir = Path(args.experiment_dir)
    tickers_dir = experiment_dir / "tickers"
    if not tickers_dir.exists():
        raise FileNotFoundError(f"tickers directory not found under {experiment_dir}")

    rows: list[dict[str, object]] = []
    all_signal_rows: list[dict[str, str]] = []
    all_labels_by_trade_date: dict[tuple[str, str], dict[str, str]] = {}
    for ticker_dir in sorted(path for path in tickers_dir.iterdir() if path.is_dir()):
        result_dir = ticker_dir / "result"
        summary_path = result_dir / "summary.json"
        signals_path = result_dir / "signals.csv"
        trades_path = result_dir / "trades.csv"
        if not (summary_path.exists() and signals_path.exists() and trades_path.exists()):
            continue

        summary = _read_json(summary_path)
        label_counts = _read_label_counts(result_dir)
        action_counts = _count_actions(signals_path)
        status_counts = _count_statuses(trades_path)
        signal_rows = _read_csv_rows(signals_path)
        label_rows = _load_label_rows(result_dir)
        all_signal_rows.extend(signal_rows)
        for trade_date, row in label_rows.items():
            all_labels_by_trade_date[(ticker_dir.name, trade_date)] = row
        rows.append(
            {
                "ticker": ticker_dir.name,
                "signal_count": summary.get("signal_count"),
                "trade_count": summary.get("trade_count"),
                "triggered_trade_count": summary.get("triggered_trade_count"),
                "win_rate": summary.get("win_rate"),
                "avg_return": summary.get("avg_return"),
                "buy_signals": action_counts.get("buy_on_pullback", 0),
                "hold_signals": action_counts.get("hold", 0),
                "sell_signals": action_counts.get("sell", 0),
                "good_case": label_counts.get("good_case", 0),
                "bad_case": label_counts.get("bad_case", 0),
                "unclear": label_counts.get("unclear", 0),
                "triggered": status_counts.get("triggered", 0),
                "triggered_exit": status_counts.get("triggered_exit", 0),
                "skipped": status_counts.get("skipped", 0),
                "expired": status_counts.get("expired", 0),
                "no_data": status_counts.get("no_data", 0),
            }
        )

    output_json = experiment_dir / "compare_summary.json"
    output_md = experiment_dir / "compare_summary.md"
    scenario_json = experiment_dir / "scenario_summary.json"
    output_json.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")

    scenario_input_rows = []
    for signal in all_signal_rows:
        ticker = signal.get("ticker") or ""
        trade_date = signal.get("trade_date") or ""
        label_row = all_labels_by_trade_date.get((ticker, trade_date), {})
        merged = dict(signal)
        if label_row:
            merged["label"] = label_row.get("label", "")
        scenario_input_rows.append(merged)

    scenario_rows = _build_bucket_summary(scenario_input_rows, field_name="scenario_type")
    trend_rows = _build_bucket_summary(scenario_input_rows, field_name="trend_judgment")
    scenario_json.write_text(
        json.dumps(
            {
                "by_scenario_type": scenario_rows,
                "by_trend_judgment": trend_rows,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    lines = [
        f"# {experiment_dir.name} 跨标的汇总",
        "",
        "| 标的 | 信号数 | 交易数 | 实际成交 | 胜率 | 平均收益 | 择机买入 | 保持观望 | 建议卖出 | 好样本 | 坏样本 | 待判断 | 跳过 | 过期未成交 | 无后续数据 |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            "| {ticker} | {signal_count} | {trade_count} | {triggered_trade_count} | {win_rate} | {avg_return} | {buy_signals} | {hold_signals} | {sell_signals} | {good_case} | {bad_case} | {unclear} | {skipped} | {expired} | {no_data} |".format(
                **row
            )
        )

    lines.extend(["", "## 样本分型归因", ""])
    lines.extend(
        [
            "| 样本分型 | 信号数 | 好样本 | 坏样本 | 待判断 | 准确率 | 择机买入 | 保持观望 | 建议卖出 |",
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
        ]
    )
    for row in scenario_rows:
        actions = row.get("actions", {})
        lines.append(
            "| {bucket} | {signal_count} | {good_case} | {bad_case} | {unclear} | {accuracy} | {buy} | {hold} | {sell} |".format(
                bucket=row["bucket"],
                signal_count=row["signal_count"],
                good_case=row["good_case"],
                bad_case=row["bad_case"],
                unclear=row["unclear"],
                accuracy=_format_accuracy(row["accuracy"]),
                buy=actions.get("buy_on_pullback", 0),
                hold=actions.get("hold", 0),
                sell=actions.get("sell", 0),
            )
        )

    lines.extend(["", "## 趋势判断归因", ""])
    lines.extend(
        [
            "| 趋势判断 | 信号数 | 好样本 | 坏样本 | 待判断 | 准确率 | 择机买入 | 保持观望 | 建议卖出 |",
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
        ]
    )
    for row in trend_rows:
        actions = row.get("actions", {})
        lines.append(
            "| {bucket} | {signal_count} | {good_case} | {bad_case} | {unclear} | {accuracy} | {buy} | {hold} | {sell} |".format(
                bucket=row["bucket"],
                signal_count=row["signal_count"],
                good_case=row["good_case"],
                bad_case=row["bad_case"],
                unclear=row["unclear"],
                accuracy=_format_accuracy(row["accuracy"]),
                buy=actions.get("buy_on_pullback", 0),
                hold=actions.get("hold", 0),
                sell=actions.get("sell", 0),
            )
        )

    output_md.write_text("\n".join(lines), encoding="utf-8")

    print(output_json)
    print(output_md)
    print(scenario_json)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
