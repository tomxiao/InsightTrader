from __future__ import annotations

import argparse
import csv
import json
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

load_dotenv(ROOT_DIR / ".env")

from backtest.pathing import build_output_run_dir, build_report_dir_name, normalize_ticker_for_path
from backtest.run_report_backtest import _default_output_dir
from ta_service.adapters.tradingagents_runner import RunnerRequest, TradingAgentsRunner
from ta_service.config.settings import get_settings
from tradingagents.dataflows.tushare_stock import _fetch_tushare_ohlcv

DEFAULT_BACKTEST_LLM_MODEL = "deepseek-chat"


def _sample_dates_from_ohlcv(
    ticker: str,
    start_date: str,
    end_date: str,
    *,
    mode: str,
    step: int,
) -> list[str]:
    dataframe, _market, _symbol = _fetch_tushare_ohlcv(ticker, start_date, end_date)
    if dataframe.empty:
        raise RuntimeError(f"No OHLCV rows returned for {ticker} between {start_date} and {end_date}")

    frame = dataframe.copy()
    frame["Date"] = (
        __import__("pandas").to_datetime(frame["Date"], errors="coerce").dt.strftime("%Y-%m-%d")
    )
    frame = frame.dropna(subset=["Date"])
    dates = frame["Date"].tolist()

    if mode == "daily":
        return dates[::step]

    if mode == "weekly":
        sampled: list[str] = []
        seen_keys: set[str] = set()
        for trade_date in dates:
            key = datetime.strptime(trade_date, "%Y-%m-%d").strftime("%G-W%V")
            if key in seen_keys:
                continue
            seen_keys.add(key)
            sampled.append(trade_date)
        return sampled

    raise ValueError(f"Unsupported sample mode: {mode}")


def _write_manifest_json(path: Path, records: list[dict]) -> None:
    path.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_manifest_csv(path: Path, records: list[dict]) -> None:
    if not records:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(records[0].keys()))
        writer.writeheader()
        writer.writerows(records)


def _load_existing_manifest(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def _decision_path_exists(record: dict[str, Any]) -> bool:
    decision_path = record.get("decision_path")
    return bool(decision_path and Path(decision_path).exists())


def _persist_batch_state(output_dir: Path, metadata: dict[str, Any], records: list[dict[str, Any]]) -> None:
    (output_dir / "batch_metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    _write_manifest_json(output_dir / "report_manifest.json", records)
    _write_manifest_csv(output_dir / "report_manifest.csv", records)

def _run_single_report(
    *,
    ticker: str,
    trade_date: str,
    team_id: str,
    llm_model: str,
    selected_analysts: list[str],
    batch_reports_dir: Path,
) -> dict:
    report_dir = batch_reports_dir / build_report_dir_name(trade_date, ticker)
    runner = TradingAgentsRunner(
        get_settings(),
        config_overrides={
            "llm_provider": "deepseek",
            "deep_think_llm": llm_model,
            "quick_think_llm": llm_model,
        },
    )
    request = RunnerRequest(
        user_id="backtest-batch",
        username="backtest-batch",
        conversation_id=f"batch-{ticker.lower()}",
        ticker=ticker,
        trade_date=trade_date,
        selected_analysts=selected_analysts,
        team_id=team_id,
        report_output_dir=report_dir,
    )
    result = runner.run_analysis(request)
    return {
        "ticker": ticker.upper(),
        "trade_date": trade_date,
        "team_id": team_id,
        "llm_model": llm_model,
        "selected_analysts": ",".join(selected_analysts),
        "trace_dir": str(result.run_context.trace_dir),
        "source_report_dir": None,
        "report_dir": str(result.report_dir) if result.report_dir else None,
        "decision_path": (
            str(result.report_dir / "2_decision" / "summary.md") if result.report_dir else None
        ),
        "llm_calls": result.stats.get("llm_calls"),
        "tool_calls": result.stats.get("tool_calls"),
        "tokens_in": result.stats.get("tokens_in"),
        "tokens_out": result.stats.get("tokens_out"),
        "executive_summary": result.executive_summary,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate historical InsightTrader reports in batch.")
    parser.add_argument("--ticker", required=True, help="Ticker symbol, e.g. AXTI")
    parser.add_argument("--start-date", required=True, help="Start date in YYYY-MM-DD")
    parser.add_argument("--end-date", required=True, help="End date in YYYY-MM-DD")
    parser.add_argument(
        "--sample-mode",
        choices=["weekly", "daily"],
        default="weekly",
        help="Weekly uses the first trading day of each ISO week. Daily uses every nth trading day.",
    )
    parser.add_argument(
        "--step",
        type=int,
        default=1,
        help="Only used with sample-mode=daily. Select every nth trading day.",
    )
    parser.add_argument("--team-id", default="lite", help="Analysis team id. Defaults to lite.")
    parser.add_argument(
        "--llm-model",
        default=DEFAULT_BACKTEST_LLM_MODEL,
        help="LLM model used for historical report generation. Defaults to deepseek-reasoner.",
    )
    parser.add_argument(
        "--analysts",
        default="market,news,fundamentals",
        help="Comma-separated analyst list. Defaults to market,news,fundamentals.",
    )
    parser.add_argument(
        "--output-dir",
        default=str(_default_output_dir()),
        help="Base directory for batch outputs. Each run writes to MMdd-HHmm-ticker.",
    )
    parser.add_argument(
        "--resume-dir",
        help="Optional existing batch output directory for resume. When set, completed reports are skipped.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    selected_analysts = [item.strip() for item in args.analysts.split(",") if item.strip()]
    sampled_dates = _sample_dates_from_ohlcv(
        args.ticker,
        args.start_date,
        args.end_date,
        mode=args.sample_mode,
        step=max(args.step, 1),
    )

    output_dir = Path(args.resume_dir) if args.resume_dir else build_output_run_dir(args.output_dir, args.ticker)
    output_dir.mkdir(parents=True, exist_ok=True)
    batch_reports_dir = output_dir / "reports"
    batch_reports_dir.mkdir(parents=True, exist_ok=True)

    metadata = {
        "ticker": args.ticker.upper(),
        "start_date": args.start_date,
        "end_date": args.end_date,
        "sample_mode": args.sample_mode,
        "step": args.step,
        "team_id": args.team_id,
        "llm_provider": "deepseek",
        "llm_model": args.llm_model,
        "selected_analysts": selected_analysts,
        "sampled_dates": sampled_dates,
        "record_count": 0,
        "report_concurrency": 3,
        "reports_dir": str(batch_reports_dir),
        "resume_dir": str(output_dir) if args.resume_dir else None,
    }
    manifest_path = output_dir / "report_manifest.json"
    existing_records = _load_existing_manifest(manifest_path)
    records_by_date: dict[str, dict[str, Any]] = {
        str(record["trade_date"]): record for record in existing_records if record.get("trade_date")
    }
    skipped_dates: list[str] = []
    pending_dates: list[str] = []
    for trade_date in sampled_dates:
        existing = records_by_date.get(trade_date)
        if existing and _decision_path_exists(existing):
            skipped_dates.append(trade_date)
        else:
            pending_dates.append(trade_date)

    total = len(sampled_dates)
    completed_count = len(skipped_dates)
    for trade_date in skipped_dates:
        record = records_by_date[trade_date]
        print(f"[{completed_count}/{total}] SKIP {trade_date} -> {record.get('decision_path')}")

    max_workers = 3
    if pending_dates:
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_map = {}
            for trade_date in pending_dates:
                print(f"[{completed_count}/{total}] RUN  {trade_date}")
                future = executor.submit(
                    _run_single_report,
                    ticker=args.ticker,
                    trade_date=trade_date,
                    team_id=args.team_id,
                    llm_model=args.llm_model,
                    selected_analysts=selected_analysts,
                    batch_reports_dir=batch_reports_dir,
                )
                future_map[future] = trade_date
            for future in as_completed(future_map):
                trade_date = future_map[future]
                try:
                    record = future.result()
                except Exception as exc:
                    print(f"[{completed_count}/{total}] FAIL {trade_date} -> {exc}")
                    records = []
                    for index, date in enumerate(sampled_dates, start=1):
                        if date in records_by_date:
                            records.append({"sequence": index, **records_by_date[date]})
                    metadata["record_count"] = len(records)
                    _persist_batch_state(output_dir, metadata, records)
                    raise

                records_by_date[trade_date] = record
                completed_count += 1
                print(f"[{completed_count}/{total}] DONE {trade_date} -> {record['decision_path']}")
                records = []
                for index, date in enumerate(sampled_dates, start=1):
                    if date in records_by_date:
                        records.append({"sequence": index, **records_by_date[date]})
                metadata["record_count"] = len(records)
                _persist_batch_state(output_dir, metadata, records)

    records: list[dict] = []
    for index, trade_date in enumerate(sampled_dates, start=1):
        if trade_date not in records_by_date:
            continue
        record = {"sequence": index, **records_by_date[trade_date]}
        records.append(record)

    metadata["record_count"] = len(records)
    metadata["skipped_count"] = len(skipped_dates)
    metadata["pending_count"] = len(pending_dates)
    _persist_batch_state(output_dir, metadata, records)

    print(json.dumps(metadata, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
