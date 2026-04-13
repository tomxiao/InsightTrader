import json
import re
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from tradingagents.dataflows.config import get_runtime_context

SCHEMA_VERSION = 1
RUN_TRACE_FILENAME = "run_trace.jsonl"
NODE_TRACE_FILENAME = "node_events.jsonl"
LLM_TRACE_FILENAME = "llm_events.jsonl"

_RESEARCH_DEBATE_INPUT_DIR = Path("llm_inputs") / "research.debate"
_TRACE_COUNTERS_LOCK = threading.Lock()
_TRACE_COUNTERS: Dict[str, Dict[str, int]] = {}
_SANITIZE_PATTERN = re.compile(r"[^A-Za-z0-9._-]+")
_NODE_STAGE_OVERRIDES = {
    "Bull Researcher": "research.debate",
    "Bear Researcher": "research.debate",
    "Research Manager": "research.debate",
    "Trader": "trader.plan",
    "Aggressive Analyst": "risk.debate",
    "Conservative Analyst": "risk.debate",
    "Neutral Analyst": "risk.debate",
    "Portfolio Manager": "portfolio.decision",
}


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_trace_event(event: str, **payload: Any) -> Dict[str, Any]:
    trace_event = {
        "ts": _utc_now_iso(),
        "schema_version": SCHEMA_VERSION,
        "event": event,
    }
    trace_event.update(payload)
    return trace_event


def _resolve_trace_dir(
    config: Optional[Dict[str, Any]] = None,
    runtime_context: Optional[Dict[str, Any]] = None,
) -> Path:
    runtime_context = runtime_context or {}
    config = config or {}

    trace_dir = runtime_context.get("trace_dir")
    if trace_dir:
        return Path(trace_dir)

    results_dir = Path(config.get("results_dir", "./results"))
    project_dir = Path(config.get("project_dir", "."))
    if not results_dir.is_absolute():
        results_dir = project_dir / results_dir
    return results_dir / "_trace"


def _append_jsonl(path: Path, event: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=False, default=str) + "\n")


def _merge_runtime_context(runtime_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    merged = dict(runtime_context or {})
    merged.update(get_runtime_context())
    return merged


def _sanitize_path_component(value: Any) -> str:
    sanitized = _SANITIZE_PATTERN.sub("_", str(value or "").strip()).strip("._")
    return sanitized or "unknown"


def _next_trace_sequence(trace_dir: Path, counter_name: str) -> int:
    trace_dir_key = str(trace_dir.resolve())
    with _TRACE_COUNTERS_LOCK:
        counters = _TRACE_COUNTERS.setdefault(trace_dir_key, {})
        counters[counter_name] = counters.get(counter_name, 0) + 1
        return counters[counter_name]


def resolve_stage_id_for_node(node_name: str) -> str:
    if node_name in _NODE_STAGE_OVERRIDES:
        return _NODE_STAGE_OVERRIDES[node_name]

    if node_name.startswith("tools_"):
        analyst_key = node_name.removeprefix("tools_").strip().lower()
        return f"analysts.{analyst_key}"

    if node_name.startswith("Msg Clear "):
        analyst_name = node_name.removeprefix("Msg Clear ").removesuffix(" Analyst").strip().lower()
        return f"analysts.{analyst_name}"

    if node_name.endswith(" Analyst"):
        analyst_name = node_name.removesuffix(" Analyst").strip().lower()
        return f"analysts.{analyst_name}"

    return "graph.internal"


def resolve_node_kind(node_name: str) -> str:
    if node_name.startswith("tools_"):
        return "tool"
    if node_name.startswith("Msg Clear "):
        return "utility"
    return "agent"


def _serialize_llm_input(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        return {str(key): _serialize_llm_input(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_serialize_llm_input(item) for item in value]

    role = getattr(value, "role", None) or getattr(value, "type", None)
    content = getattr(value, "content", None)
    name = getattr(value, "name", None)
    if role is not None or content is not None:
        payload = {
            "message_type": value.__class__.__name__,
            "role": role,
            "content": _serialize_llm_input(content),
        }
        if name is not None:
            payload["name"] = name
        return payload

    if hasattr(value, "to_dict") and callable(value.to_dict):
        try:
            return _serialize_llm_input(value.to_dict())
        except Exception:
            return str(value)

    if hasattr(value, "dict") and callable(value.dict):
        try:
            return _serialize_llm_input(value.dict())
        except Exception:
            return str(value)

    return str(value)


def _extract_llm_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        if isinstance(value.get("content"), str):
            return value["content"]
        if value.get("type") == "text" and isinstance(value.get("text"), str):
            return value["text"]
        return "\n".join(filter(None, (_extract_llm_text(item) for item in value.values())))
    if isinstance(value, (list, tuple)):
        return "\n".join(filter(None, (_extract_llm_text(item) for item in value)))

    content = getattr(value, "content", None)
    if content is not None:
        return _extract_llm_text(content)

    return str(value)


def _build_llm_input_preview(llm_input: Any, max_chars: int = 500) -> str:
    text = _extract_llm_text(llm_input).strip()
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "...[truncated]"


def _classify_llm_input(llm_input: Any) -> str:
    if isinstance(llm_input, str):
        return "string"
    if isinstance(llm_input, dict):
        return "dict"
    if isinstance(llm_input, (list, tuple)):
        return "messages"
    return llm_input.__class__.__name__


def persist_research_debate_llm_input(
    llm_input: Any,
    *,
    config: Optional[Dict[str, Any]] = None,
    runtime_context: Optional[Dict[str, Any]] = None,
    provider: Optional[str] = None,
    model: Optional[str] = None,
) -> Optional[str]:
    merged_runtime_context = _merge_runtime_context(runtime_context)
    stage_id = merged_runtime_context.get("current_stage_id") or merged_runtime_context.get(
        "stage_id"
    )
    if stage_id != "research.debate":
        return None

    trace_dir = _resolve_trace_dir(config=config, runtime_context=merged_runtime_context)
    sequence = _next_trace_sequence(trace_dir, "research_debate_llm_input")
    node_id = merged_runtime_context.get("current_node_id") or "unknown-node"
    filename = f"{sequence:03d}_{_sanitize_path_component(node_id)}.json"
    output_path = trace_dir / _RESEARCH_DEBATE_INPUT_DIR / filename
    serialized_input = _serialize_llm_input(llm_input)
    payload = {
        "captured_at": _utc_now_iso(),
        "run_id": merged_runtime_context.get("run_id"),
        "stage_id": stage_id,
        "node_id": node_id,
        "provider": provider,
        "model": model,
        "input_type": _classify_llm_input(llm_input),
        "input_preview": _build_llm_input_preview(llm_input, max_chars=1200),
        "input": serialized_input,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    return str(output_path)


def emit_llm_event(
    event: str,
    *,
    llm_input: Any = None,
    duration_ms: Optional[int] = None,
    config: Optional[Dict[str, Any]] = None,
    runtime_context: Optional[Dict[str, Any]] = None,
    provider: Optional[str] = None,
    model: Optional[str] = None,
    error: Optional[Exception] = None,
) -> Dict[str, Any]:
    merged_runtime_context = _merge_runtime_context(runtime_context)
    payload: Dict[str, Any] = {
        "run_id": merged_runtime_context.get("run_id"),
        "stage_id": merged_runtime_context.get("current_stage_id"),
        "node_id": merged_runtime_context.get("current_node_id"),
        "provider": provider,
        "model": model,
    }

    if llm_input is not None:
        payload["input_type"] = _classify_llm_input(llm_input)
        payload["input_preview"] = _build_llm_input_preview(llm_input)
        payload["input_chars"] = len(_extract_llm_text(llm_input))
        input_path = persist_research_debate_llm_input(
            llm_input,
            config=config,
            runtime_context=merged_runtime_context,
            provider=provider,
            model=model,
        )
        if input_path:
            payload["input_path"] = input_path

    if duration_ms is not None:
        payload["duration_ms"] = duration_ms

    if error is not None:
        payload["error_code"] = error.__class__.__name__
        payload["error_message"] = str(error)

    return emit_trace_event(
        LLM_TRACE_FILENAME,
        event,
        config=config,
        runtime_context=merged_runtime_context,
        **payload,
    )


def emit_trace_event(
    filename: str,
    event: str,
    *,
    config: Optional[Dict[str, Any]] = None,
    runtime_context: Optional[Dict[str, Any]] = None,
    mirror_to_run_trace: bool = True,
    **payload: Any,
) -> Dict[str, Any]:
    trace_event = build_trace_event(event, **payload)
    trace_dir = _resolve_trace_dir(config=config, runtime_context=runtime_context)

    _append_jsonl(trace_dir / filename, trace_event)
    if mirror_to_run_trace and filename != RUN_TRACE_FILENAME:
        _append_jsonl(trace_dir / RUN_TRACE_FILENAME, trace_event)

    return trace_event


class StageEventTracker:
    def __init__(
        self,
        *,
        config: Optional[Dict[str, Any]] = None,
        runtime_context: Optional[Dict[str, Any]] = None,
        stall_threshold_s: float = 60.0,
        check_interval_s: float = 5.0,
    ) -> None:
        self.config = config or {}
        self.runtime_context = runtime_context or {}
        self.stall_threshold_s = stall_threshold_s
        self.check_interval_s = check_interval_s
        self.stage_status: Dict[str, str] = {}
        self.last_progress_at = time.monotonic()
        self.current_stage_id: Optional[str] = None
        self._stalled_stage_id: Optional[str] = None
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._watchdog_thread: Optional[threading.Thread] = None

    def _emit(self, event: str, **payload: Any) -> Dict[str, Any]:
        return emit_trace_event(
            "stage_events.jsonl",
            event,
            config=self.config,
            runtime_context=self.runtime_context,
            run_id=self.runtime_context.get("run_id"),
            **payload,
        )

    def start_watchdog(self) -> None:
        if self._watchdog_thread is not None or self.stall_threshold_s <= 0:
            return

        self._watchdog_thread = threading.Thread(
            target=self._watchdog_loop,
            name="stage-event-watchdog",
            daemon=True,
        )
        self._watchdog_thread.start()

    def stop_watchdog(self) -> None:
        self._stop_event.set()
        if self._watchdog_thread is not None:
            self._watchdog_thread.join(timeout=1)
            self._watchdog_thread = None

    def sync(
        self,
        stage_snapshot: Dict[str, str],
        stage_metadata: Optional[Dict[str, Dict[str, Any]]] = None,
    ) -> None:
        stage_metadata = stage_metadata or {}
        now = time.monotonic()

        with self._lock:
            previous_snapshot = dict(self.stage_status)
            snapshot_changed = stage_snapshot != previous_snapshot
            if snapshot_changed:
                self.last_progress_at = now
                self._stalled_stage_id = None

            for stage_id, status in stage_snapshot.items():
                previous_status = previous_snapshot.get(stage_id, "pending")
                if status == previous_status:
                    continue

                payload = {
                    "stage_id": stage_id,
                    "previous_status": previous_status,
                    "status": status,
                }
                payload.update(stage_metadata.get(stage_id, {}))

                if status == "in_progress" and previous_status == "pending":
                    self._emit("stage.started", **payload)
                elif status == "completed" and previous_status != "completed":
                    if previous_status == "pending":
                        started_payload = dict(payload)
                        started_payload["status"] = "in_progress"
                        self._emit("stage.started", **started_payload)
                    self._emit("stage.completed", **payload)

            self.stage_status = dict(stage_snapshot)
            self.current_stage_id = next(
                (
                    stage_id
                    for stage_id, status in stage_snapshot.items()
                    if status == "in_progress"
                ),
                None,
            )

    def mark_failed(self, error: Exception) -> None:
        with self._lock:
            stage_id = self.current_stage_id
        if not stage_id:
            return

        self._emit(
            "stage.failed",
            stage_id=stage_id,
            status="failed",
            error_code=error.__class__.__name__,
            error_message=str(error),
        )

    def _watchdog_loop(self) -> None:
        while not self._stop_event.wait(self.check_interval_s):
            with self._lock:
                if not self.current_stage_id:
                    continue
                if self._stalled_stage_id == self.current_stage_id:
                    continue
                if self.stage_status.get(self.current_stage_id) != "in_progress":
                    continue
                if time.monotonic() - self.last_progress_at < self.stall_threshold_s:
                    continue

                self._stalled_stage_id = self.current_stage_id
                self._emit(
                    "stage.stalled",
                    stage_id=self.current_stage_id,
                    status="in_progress",
                    stalled_for_seconds=self.stall_threshold_s,
                )


class NodeEventTracker:
    def __init__(
        self,
        *,
        config: Optional[Dict[str, Any]] = None,
        runtime_context: Optional[Dict[str, Any]] = None,
        runtime_context_getter=None,
        stall_threshold_s: float = 60.0,
        check_interval_s: float = 5.0,
        on_node_started=None,
    ) -> None:
        self.config = config or {}
        self.runtime_context = runtime_context or {}
        self.runtime_context_getter = runtime_context_getter
        self.stall_threshold_s = stall_threshold_s
        self.check_interval_s = check_interval_s
        self.on_node_started = on_node_started
        self.last_progress_at = time.monotonic()
        self.current_node: Optional[Dict[str, Any]] = None
        self._stalled_node_id: Optional[str] = None
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._watchdog_thread: Optional[threading.Thread] = None

    def _current_runtime_context(self) -> Dict[str, Any]:
        runtime_context = dict(self.runtime_context)
        if self.runtime_context_getter is not None:
            runtime_context.update(self.runtime_context_getter())
        return runtime_context

    def _emit(self, event: str, **payload: Any) -> Dict[str, Any]:
        runtime_context = self._current_runtime_context()
        return emit_trace_event(
            NODE_TRACE_FILENAME,
            event,
            config=self.config,
            runtime_context=runtime_context,
            run_id=runtime_context.get("run_id"),
            **payload,
        )

    def start_watchdog(self) -> None:
        if self._watchdog_thread is not None or self.stall_threshold_s <= 0:
            return

        self._watchdog_thread = threading.Thread(
            target=self._watchdog_loop,
            name="node-event-watchdog",
            daemon=True,
        )
        self._watchdog_thread.start()

    def stop_watchdog(self) -> None:
        self._stop_event.set()
        if self._watchdog_thread is not None:
            self._watchdog_thread.join(timeout=1)
            self._watchdog_thread = None

    def mark_started(self, *, node_id: str, stage_id: str, node_kind: str) -> None:
        now = time.monotonic()
        payload = {
            "node_id": node_id,
            "stage_id": stage_id,
            "node_kind": node_kind,
            "status": "in_progress",
        }
        with self._lock:
            self.current_node = dict(payload)
            self.current_node["started_at_monotonic"] = now
            self.last_progress_at = now
            self._stalled_node_id = None
        self._emit("node.started", **payload)
        if node_kind == "agent" and self.on_node_started is not None:
            try:
                self.on_node_started(node_id, stage_id)
            except Exception:
                pass

    def mark_completed(self) -> None:
        now = time.monotonic()
        with self._lock:
            node_info = dict(self.current_node) if self.current_node else None
            self.current_node = None
            self.last_progress_at = now
            self._stalled_node_id = None

        if not node_info:
            return

        started_at = node_info.pop("started_at_monotonic", now)
        node_info["status"] = "completed"
        node_info["duration_ms"] = int((now - started_at) * 1000)
        self._emit("node.completed", **node_info)

    def mark_failed(self, error: Exception) -> None:
        now = time.monotonic()
        with self._lock:
            node_info = dict(self.current_node) if self.current_node else None
            self.current_node = None
            self.last_progress_at = now
            self._stalled_node_id = None

        if not node_info:
            return

        started_at = node_info.pop("started_at_monotonic", now)
        node_info["status"] = "failed"
        node_info["duration_ms"] = int((now - started_at) * 1000)
        node_info["error_code"] = error.__class__.__name__
        node_info["error_message"] = str(error)
        self._emit("node.failed", **node_info)

    def _watchdog_loop(self) -> None:
        while not self._stop_event.wait(self.check_interval_s):
            with self._lock:
                if not self.current_node:
                    continue
                node_id = self.current_node["node_id"]
                if self._stalled_node_id == node_id:
                    continue
                running_for_s = time.monotonic() - self.current_node["started_at_monotonic"]
                if running_for_s < self.stall_threshold_s:
                    continue

                self._stalled_node_id = node_id
                payload = {
                    "node_id": node_id,
                    "stage_id": self.current_node["stage_id"],
                    "node_kind": self.current_node["node_kind"],
                    "status": "in_progress",
                    "stalled_for_seconds": self.stall_threshold_s,
                    "running_for_seconds": round(running_for_s, 3),
                }
            self._emit("node.stalled", **payload)
