from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

load_dotenv(ROOT_DIR / ".env")

from backtest.execution_rules import simulate_trade
from backtest.metrics import summarize_backtest
from backtest.pathing import build_output_run_dir
from backtest.report_parser import parse_report_file
from tradingagents.dataflows.finnhub_stock import _fetch_finnhub_ohlcv
from tradingagents.dataflows.stockstats_utils import load_ohlcv
from tradingagents.dataflows.tushare_stock import _fetch_tushare_ohlcv


def _fetch_ohlcv(ticker: str, start_date: str, end_date: str) -> pd.DataFrame:
    errors: list[str] = []

    try:
        data, _market, _symbol = _fetch_tushare_ohlcv(ticker, start_date, end_date)
        if not data.empty:
            data["Date"] = pd.to_datetime(data["Date"], errors="coerce")
            return data.dropna(subset=["Date"]).reset_index(drop=True)
        errors.append("tushare:empty")
    except Exception as exc:
        errors.append(f"tushare:{exc}")

    try:
        data = load_ohlcv(ticker, end_date)
        if not data.empty:
            frame = data[data["Date"] >= pd.Timestamp(start_date)].copy()
            if not frame.empty:
                return frame.reset_index(drop=True)
            errors.append("cached_yfinance:no_rows_in_range")
        else:
            errors.append("cached_yfinance:empty")
    except Exception as exc:
        errors.append(f"cached_yfinance:{exc}")

    try:
        data, _market, _symbol = _fetch_finnhub_ohlcv(ticker, start_date, end_date)
        if not data.empty:
            data["Date"] = pd.to_datetime(data["Date"], errors="coerce")
            return data.dropna(subset=["Date"]).reset_index(drop=True)
        errors.append("finnhub:empty")
    except Exception as exc:
        errors.append(f"finnhub:{exc}")

    raise RuntimeError(
        f"No OHLCV data returned for {ticker} between {start_date} and {end_date}; attempts={errors}"
    )


def _default_output_dir() -> Path:
    return Path("backtest") / "output"


def _infer_batch_output_dir(report_paths: list[str]) -> Path | None:
    candidates: set[Path] = set()
    for raw_path in report_paths:
        path = Path(raw_path).resolve()
        for parent in path.parents:
            if parent.name.lower() == "reports":
                candidates.add(parent.parent)
                break
        else:
            return None

    if len(candidates) != 1:
        return None
    return next(iter(candidates))


def _resolve_output_dir(report_paths: list[str], output_dir: str | None, ticker: str) -> Path:
    if output_dir:
        return Path(output_dir)

    inferred = _infer_batch_output_dir(report_paths)
    if inferred is not None:
        return inferred

    return build_output_run_dir(_default_output_dir(), ticker)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Backtest InsightTrader decision reports.")
    parser.add_argument(
        "--report",
        action="append",
        required=True,
        help="Path to a lite-team decision summary.md file. Repeat for multiple reports.",
    )
    parser.add_argument("--ticker", help="Override ticker instead of inferring it from the report path.")
    parser.add_argument(
        "--end-date",
        default=pd.Timestamp.today().strftime("%Y-%m-%d"),
        help="Last date to fetch OHLCV data for exits. Defaults to today.",
    )
    parser.add_argument(
        "--max-holding-days",
        type=int,
        default=60,
        help="Maximum calendar holding window after entry.",
    )
    parser.add_argument(
        "--output-dir",
        help="Optional target directory for signals.csv/trades.csv/summary.json. Defaults to the parent of reports/ when all reports belong to one batch.",
    )
    parser.add_argument(
        "--ohlcv-csv",
        help="Optional local CSV with Date/Open/High/Low/Close columns. When provided, skip remote fetch.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    signals = [parse_report_file(path, ticker=args.ticker) for path in args.report]
    if not signals:
        raise RuntimeError("No signals parsed")

    ticker = args.ticker or signals[0].ticker
    start_date = min(signal.trade_date for signal in signals)
    if args.ohlcv_csv:
        ohlcv = pd.read_csv(args.ohlcv_csv)
    else:
        ohlcv = _fetch_ohlcv(ticker, start_date, args.end_date)

    trades = [simulate_trade(signal, ohlcv, max_holding_days=args.max_holding_days) for signal in signals]
    summary = summarize_backtest(trades)

    output_dir = _resolve_output_dir(args.report, args.output_dir, ticker)
    output_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame([signal.to_dict() for signal in signals]).to_csv(
        output_dir / "signals.csv",
        index=False,
        encoding="utf-8-sig",
    )
    pd.DataFrame([trade.to_dict() for trade in trades]).to_csv(
        output_dir / "trades.csv",
        index=False,
        encoding="utf-8-sig",
    )
    (output_dir / "summary.json").write_text(
        json.dumps(summary.to_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(json.dumps(summary.to_dict(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
