from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from ta_service.config.settings import Settings
from tradingagents.run_paths import resolve_results_run_dir


@dataclass(frozen=True)
class RunContext:
    run_id: str
    ticker: str
    trade_date: str
    started_at: datetime
    trace_dir: Path


def build_run_context(*, settings: Settings, ticker: str, trade_date: str) -> RunContext:
    started_at = datetime.now(timezone.utc)
    run_id = f"{ticker}-{uuid4().hex[:12]}"
    trace_dir = resolve_results_run_dir(str(settings.results_root), ticker, started_at)
    trace_dir.mkdir(parents=True, exist_ok=True)
    return RunContext(
        run_id=run_id,
        ticker=ticker,
        trade_date=trade_date,
        started_at=started_at,
        trace_dir=trace_dir,
    )
