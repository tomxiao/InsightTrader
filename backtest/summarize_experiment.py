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


def _read_label_counts(result_dir: Path) -> dict[str, int]:
    summary_path = result_dir / "signal_case_label_summary.json"
    if not summary_path.exists():
        return {"good_case": 0, "bad_case": 0, "unclear": 0}
    return _read_json(summary_path)["label_counts"]


def _count_actions(signals_csv: Path) -> dict[str, int]:
    counts: dict[str, int] = {}
    with signals_csv.open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            action = row["action"]
            counts[action] = counts.get(action, 0) + 1
    return counts


def _count_statuses(trades_csv: Path) -> dict[str, int]:
    counts: dict[str, int] = {}
    with trades_csv.open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            status = row["status"]
            counts[status] = counts.get(status, 0) + 1
    return counts


def main() -> int:
    args = build_parser().parse_args()
    experiment_dir = Path(args.experiment_dir)
    tickers_dir = experiment_dir / "tickers"
    if not tickers_dir.exists():
        raise FileNotFoundError(f"tickers directory not found under {experiment_dir}")

    rows: list[dict[str, object]] = []
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
    output_json.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")

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
    output_md.write_text("\n".join(lines), encoding="utf-8")

    print(output_json)
    print(output_md)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
