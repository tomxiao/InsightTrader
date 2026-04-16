from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ta_service.config.settings import Settings
from ta_service.runtime.trace_scopes import build_reply_trace_dir, build_resolution_trace_dir
from tradingagents.observability import build_trace_event
from tradingagents.run_paths import build_run_directory_name


def test_resolution_trace_dir_uses_results_resolution_root(tmp_path: Path) -> None:
    settings = Settings(results_root=tmp_path / "results" / "analysis")

    trace_dir = build_resolution_trace_dir(
        settings=settings,
        conversation_id="conv-1",
        resolution_id="res-1",
    )

    assert trace_dir == tmp_path / "results" / "resolution" / "conv-1" / "res-1"
    assert trace_dir.exists()


def test_reply_trace_dir_uses_results_reply_root(tmp_path: Path) -> None:
    settings = Settings(results_root=tmp_path / "results" / "analysis")

    trace_dir = build_reply_trace_dir(
        settings=settings,
        conversation_id="conv-1",
        reply_id="reply-1",
    )

    assert trace_dir == tmp_path / "results" / "reply" / "conv-1" / "reply-1"
    assert trace_dir.exists()


def test_build_run_directory_name_uses_asia_shanghai_local_time() -> None:
    started_at = datetime(2026, 4, 16, 13, 33, tzinfo=timezone.utc)

    directory_name = build_run_directory_name("SNDK", started_at)

    assert directory_name == "SNDK_2026_0416_2133"


def test_build_trace_event_uses_asia_shanghai_offset() -> None:
    event = build_trace_event("stage.started", stage_id="analysts.market")

    assert event["ts"].endswith("+08:00")
