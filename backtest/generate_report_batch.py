from __future__ import annotations

import argparse
import csv
import json
import shutil
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

from backtest.pathing import build_output_run_dir, build_report_dir_name, is_round_batch_dir, is_round_reports_ticker_dir
from ta_service.adapters.tradingagents_runner import RunnerRequest, TradingAgentsRunner
from ta_service.config.settings import get_settings
from tradingagents.agents.managers.decision_manager import generate_decision_report
from tradingagents.dataflows.tushare_stock import _fetch_tushare_ohlcv
from tradingagents.default_config import DEFAULT_CONFIG
from tradingagents.llm_clients.factory import create_llm_client

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


def _build_decision_only_llm(llm_model: str):
    config = DEFAULT_CONFIG.copy()
    config["project_dir"] = str(ROOT_DIR)
    config["results_dir"] = str(get_settings().results_root)
    config["output_language"] = get_settings().default_output_language
    config.update(
        {
            "llm_provider": "deepseek",
            "deep_think_llm": llm_model,
            "quick_think_llm": llm_model,
        }
    )
    client = create_llm_client(
        provider=config["llm_provider"],
        model=config["deep_think_llm"],
        base_url=config.get("backend_url"),
        timeout=config.get("llm_timeout"),
        max_retries=config.get("llm_max_retries"),
    )
    return client.get_llm()


def _load_text(path: Path) -> str:
    return path.read_text(encoding="utf-8").strip()


def _copy_analyst_reports(source_report_dir: Path, target_report_dir: Path) -> Path:
    source_analysts_dir = source_report_dir / "1_analysts"
    if not source_analysts_dir.exists():
        raise FileNotFoundError(f"Baseline analyst directory not found: {source_analysts_dir}")
    target_analysts_dir = target_report_dir / "1_analysts"
    if target_analysts_dir.exists():
        shutil.rmtree(target_analysts_dir)
    shutil.copytree(source_analysts_dir, target_analysts_dir)
    return target_analysts_dir


def _resolve_baseline_report_dir(baseline_batch_dir: Path, ticker: str, trade_date: str) -> Path:
    report_dir = baseline_batch_dir / "reports" / build_report_dir_name(trade_date, ticker)
    if not report_dir.exists():
        raise FileNotFoundError(f"Baseline report directory not found: {report_dir}")
    return report_dir


def _run_single_decision_only_report(
    *,
    ticker: str,
    trade_date: str,
    llm_model: str,
    baseline_batch_dir: Path,
    batch_reports_dir: Path,
) -> dict:
    report_dir = batch_reports_dir / build_report_dir_name(trade_date, ticker)
    report_dir.mkdir(parents=True, exist_ok=True)

    baseline_report_dir = _resolve_baseline_report_dir(baseline_batch_dir, ticker, trade_date)
    analysts_dir = _copy_analyst_reports(baseline_report_dir, report_dir)

    market_report = _load_text(analysts_dir / "market.md")
    news_report = _load_text(analysts_dir / "news.md")
    fundamentals_report = _load_text(analysts_dir / "fundamentals.md")

    llm = _build_decision_only_llm(llm_model)
    decision_text = generate_decision_report(
        llm,
        instrument=ticker,
        trade_date=trade_date,
        market_report=market_report,
        news_report=news_report,
        fundamentals_report=fundamentals_report,
    )

    decision_dir = report_dir / "2_decision"
    decision_dir.mkdir(exist_ok=True)
    decision_path = decision_dir / "summary.md"
    decision_path.write_text(decision_text, encoding="utf-8")

    return {
        "ticker": ticker.upper(),
        "trade_date": trade_date,
        "team_id": "lite",
        "llm_model": llm_model,
        "selected_analysts": "market,news,fundamentals",
        "trace_dir": None,
        "source_report_dir": str(baseline_report_dir),
        "report_dir": str(report_dir),
        "decision_path": str(decision_path),
        "llm_calls": None,
        "tool_calls": 0,
        "tokens_in": None,
        "tokens_out": None,
        "executive_summary": decision_text,
    }

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
        username="backtest",
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
        help="Required when not using --resume-dir. Must be the round reports ticker directory, e.g. backtest/experiments/<theme>/rounds/round05/reports/MU",
    )
    parser.add_argument(
        "--resume-dir",
        help="Optional existing batch output directory for resume. When set, completed reports are skipped.",
    )
    parser.add_argument(
        "--decision-only",
        action="store_true",
        help="Reuse existing 1_analysts reports and only regenerate 2_decision/summary.md.",
    )
    parser.add_argument(
        "--reuse-analyst-from",
        help="Baseline batch directory whose reports/<date>/1_analysts will be reused in decision-only mode.",
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
    baseline_batch_dir = Path(args.reuse_analyst_from) if args.reuse_analyst_from else None
    if args.decision_only and baseline_batch_dir is None:
        raise ValueError("--decision-only requires --reuse-analyst-from")
    if args.resume_dir:
        output_dir = Path(args.resume_dir)
        if not is_round_batch_dir(output_dir):
            raise ValueError("--resume-dir must point to a round batch directory under rounds/<round>/reports/<ticker>/<batch>")
    else:
        if not args.output_dir:
            raise ValueError("--output-dir is required and must point to rounds/<round>/reports/<ticker>")
        reports_ticker_dir = Path(args.output_dir)
        if not is_round_reports_ticker_dir(reports_ticker_dir):
            raise ValueError("--output-dir must point to a round reports ticker directory under rounds/<round>/reports/<ticker>")
        output_dir = build_output_run_dir(reports_ticker_dir, args.ticker)
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
        "report_concurrency": 5,
        "reports_dir": str(batch_reports_dir),
        "resume_dir": str(output_dir) if args.resume_dir else None,
        "generation_mode": "decision_only" if args.decision_only else "full_round",
        "analyst_source_batch": str(baseline_batch_dir) if baseline_batch_dir else None,
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

    max_workers = 5
    if pending_dates:
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_map = {}
            for trade_date in pending_dates:
                print(f"[{completed_count}/{total}] RUN  {trade_date}")
                future = executor.submit(
                    _run_single_decision_only_report if args.decision_only else _run_single_report,
                    **(
                        {
                            "ticker": args.ticker,
                            "trade_date": trade_date,
                            "llm_model": args.llm_model,
                            "baseline_batch_dir": baseline_batch_dir,
                            "batch_reports_dir": batch_reports_dir,
                        }
                        if args.decision_only
                        else {
                            "ticker": args.ticker,
                            "trade_date": trade_date,
                            "team_id": args.team_id,
                            "llm_model": args.llm_model,
                            "selected_analysts": selected_analysts,
                            "batch_reports_dir": batch_reports_dir,
                        }
                    ),
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
