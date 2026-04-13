from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def spawn_analysis_task_runner(task_id: str) -> subprocess.Popen:
    project_root = Path(__file__).resolve().parents[2]
    log_dir = project_root / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    worker_log = log_dir / "ta_service.log"

    command = [
        sys.executable,
        "-m",
        "ta_service.workers.analysis_worker",
        "--task-id",
        task_id,
    ]
    creationflags = 0
    if os.name == "nt":
        creationflags = (
            getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
            | getattr(subprocess, "DETACHED_PROCESS", 0)
        )

    log_fh = worker_log.open("a", encoding="utf-8")
    return subprocess.Popen(
        command,
        cwd=str(project_root),
        creationflags=creationflags,
        stdin=subprocess.DEVNULL,
        stdout=log_fh,
        stderr=log_fh,
    )
