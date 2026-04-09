from datetime import datetime
from pathlib import Path


RUN_DIR_TIMESTAMP_FORMAT = "%Y_%m%d_%H%M"


def format_run_started_at(started_at: datetime) -> str:
    return started_at.strftime(RUN_DIR_TIMESTAMP_FORMAT)


def build_run_directory_name(ticker: str, started_at: datetime) -> str:
    normalized_ticker = ticker.strip()
    return f"{normalized_ticker}_{format_run_started_at(started_at)}"


def resolve_results_run_dir(results_root: str | Path, ticker: str, started_at: datetime) -> Path:
    results_root = Path(results_root)
    base_name = build_run_directory_name(ticker, started_at)
    candidate = results_root / base_name

    if not candidate.exists():
        return candidate

    suffix = 2
    while True:
        candidate = results_root / f"{base_name}_{suffix:02d}"
        if not candidate.exists():
            return candidate
        suffix += 1
