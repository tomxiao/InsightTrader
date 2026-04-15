from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ta_service.runtime.status_mapper import (
    resolve_display_state,
    resolve_node_message,
    resolve_stage_message,
)


def _iso_from_now(offset_seconds: int) -> str:
    return (datetime.now(timezone.utc) + timedelta(seconds=offset_seconds)).isoformat()


def test_resolve_stage_message_uses_business_copy() -> None:
    assert resolve_stage_message("analysts.news") == "新闻分析师整理近期关键事件与新闻影响"


def test_resolve_node_message_handles_tool_and_utility_nodes() -> None:
    assert resolve_node_message("tools_news") == "投资团队补充数据与公开信息"
    assert resolve_node_message("Msg Clear News") is None


def test_resolve_display_state_maps_terminal_statuses() -> None:
    assert resolve_display_state({"status": "completed", "updatedAt": _iso_from_now(0)}) == "done"
    assert resolve_display_state({"status": "failed", "updatedAt": _iso_from_now(0)}) == "failed"


def test_resolve_display_state_marks_stalled_running_tasks() -> None:
    document = {
        "status": "running",
        "updatedAt": _iso_from_now(-120),
    }
    assert resolve_display_state(document) == "stalled"


def test_resolve_display_state_keeps_recent_running_task_active() -> None:
    document = {
        "status": "running",
        "updatedAt": _iso_from_now(-5),
    }
    assert resolve_display_state(document) == "active"
