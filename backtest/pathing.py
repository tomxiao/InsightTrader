from __future__ import annotations

from datetime import datetime
from pathlib import Path


def normalize_ticker_for_path(ticker: str) -> str:
    cleaned = "".join(char for char in ticker.strip().upper() if char.isalnum() or char in {"-", "_"})
    if not cleaned:
        raise ValueError("Ticker must contain at least one path-safe character.")
    return cleaned


def build_output_run_dir(base_dir: str | Path, ticker: str, *, now: datetime | None = None) -> Path:
    timestamp = (now or datetime.now()).strftime("%m%d-%H%M")
    return Path(base_dir) / f"{timestamp}-{normalize_ticker_for_path(ticker)}"


def build_report_dir_name(trade_date: str, ticker: str) -> str:
    normalized = datetime.strptime(trade_date, "%Y-%m-%d").strftime("%Y-%m%d")
    return f"{normalized}-{normalize_ticker_for_path(ticker)}"


def is_round_reports_ticker_dir(path: str | Path) -> bool:
    candidate = Path(path)
    return candidate.parent.name == "reports"


def is_round_batch_dir(path: str | Path) -> bool:
    candidate = Path(path)
    return candidate.parent.parent.name == "reports"
