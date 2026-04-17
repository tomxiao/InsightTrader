from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from ta_service.config.settings import Settings, get_settings
from tradingagents.dataflows.config import get_runtime_context

_SANITIZE_PATTERN = re.compile(r"[^A-Za-z0-9._-]+")
_LOCAL_TZ = ZoneInfo("Asia/Shanghai")


def append_user_trace(
    *,
    user_id: str,
    username: str | None = None,
    conversation_id: str,
    phase: str,
    event: str,
    settings: Settings | None = None,
    **payload: Any,
) -> None:
    trace_settings = settings or get_settings()
    user_dir = trace_settings.logs_root / "user"
    user_dir.mkdir(parents=True, exist_ok=True)
    normalized_username = (username or "").strip() or "unknown"
    file_stem = normalized_username
    path = user_dir / f"{_sanitize_component(file_stem)}.jsonl"

    record = {
        "ts": datetime.now(timezone.utc).astimezone(_LOCAL_TZ).isoformat(),
        "userName": normalized_username,
        "conversationId": conversation_id or "",
        "phase": phase,
        "event": event,
    }
    record.update(payload)

    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")


def append_runtime_user_trace(
    *,
    phase: str,
    event: str,
    settings: Settings | None = None,
    conversation_id: str | None = None,
    **payload: Any,
) -> None:
    runtime_context = get_runtime_context()
    user_id = str(runtime_context.get("user_id") or "").strip()
    username = str(runtime_context.get("username") or "").strip()
    if not user_id and not username:
        return
    append_user_trace(
        user_id=user_id,
        username=username or None,
        conversation_id=conversation_id or str(runtime_context.get("conversation_id") or ""),
        phase=phase,
        event=event,
        settings=settings,
        **payload,
    )


def _sanitize_component(value: str) -> str:
    sanitized = _SANITIZE_PATTERN.sub("_", (value or "").strip()).strip("._")
    return sanitized or "unknown"
