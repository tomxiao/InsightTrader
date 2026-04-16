from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
import re
from typing import Iterator

from ta_service.config.settings import Settings
from tradingagents.dataflows.config import clear_runtime_context, get_runtime_context, set_runtime_context

_SANITIZE_PATTERN = re.compile(r"[^A-Za-z0-9._-]+")


def build_resolution_trace_dir(
    *, settings: Settings, conversation_id: str, resolution_id: str
) -> Path:
    return _build_trace_scope_dir(
        settings=settings,
        category="resolution",
        scope_parts=(conversation_id, resolution_id),
    )


def build_reply_trace_dir(*, settings: Settings, conversation_id: str, reply_id: str) -> Path:
    return _build_trace_scope_dir(
        settings=settings,
        category="reply",
        scope_parts=(conversation_id, reply_id),
    )


@contextmanager
def runtime_trace_scope(**kwargs) -> Iterator[None]:
    previous = get_runtime_context()
    clear_runtime_context()
    if previous:
        set_runtime_context(**previous)
    set_runtime_context(**kwargs)
    try:
        yield
    finally:
        clear_runtime_context()
        if previous:
            set_runtime_context(**previous)


def _build_trace_scope_dir(
    *, settings: Settings, category: str, scope_parts: tuple[str, ...]
) -> Path:
    base_root = settings.results_root.parent
    trace_dir = base_root / _sanitize_path_component(category)
    for part in scope_parts:
        trace_dir = trace_dir / _sanitize_path_component(part)
    trace_dir.mkdir(parents=True, exist_ok=True)
    return trace_dir


def _sanitize_path_component(value: str) -> str:
    sanitized = _SANITIZE_PATTERN.sub("_", (value or "").strip()).strip("._")
    return sanitized or "unknown"
