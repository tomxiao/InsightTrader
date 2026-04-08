import json
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional


SCHEMA_VERSION = 1
RUN_TRACE_FILENAME = "run_trace.jsonl"


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
                (stage_id for stage_id, status in stage_snapshot.items() if status == "in_progress"),
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
