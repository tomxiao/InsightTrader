from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def spawn_analysis_task_runner(task_id: str) -> subprocess.Popen:
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

    return subprocess.Popen(
        command,
        cwd=str(Path(__file__).resolve().parents[2]),
        creationflags=creationflags,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
