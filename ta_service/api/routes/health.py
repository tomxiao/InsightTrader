from __future__ import annotations

import os
import tempfile
from pathlib import Path

from fastapi import APIRouter
from fastapi import Request
from fastapi.responses import JSONResponse

from ta_service.config.settings import Settings
from ta_service.db.redis import create_redis_client

router = APIRouter(tags=["health"])


@router.get("/health")
def health(request: Request) -> JSONResponse:
    settings: Settings = request.app.state.settings
    mongo_client = request.app.state.mongo_client

    mongo_check = _check_mongo(mongo_client)
    redis_check = _check_redis(settings)
    writable_dirs = {
        "logs_root": _check_writable_dir(settings.logs_root),
        "reports_root": _check_writable_dir(settings.reports_root),
        "results_root": _check_writable_dir(settings.results_root),
    }
    version = _read_version(settings.version_file)

    all_ok = (
        mongo_check["ok"]
        and redis_check["ok"]
        and all(item["ok"] for item in writable_dirs.values())
    )
    payload = {
        "status": "ok" if all_ok else "degraded",
        "version": version,
        "checks": {
            "mongo": mongo_check,
            "redis": redis_check,
            "writable_dirs": writable_dirs,
        },
    }
    return JSONResponse(status_code=200 if all_ok else 503, content=payload)


def _check_mongo(mongo_client) -> dict:
    try:
        mongo_client.admin.command("ping")
        return {"ok": True}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def _check_redis(settings: Settings) -> dict:
    try:
        client = create_redis_client(settings)
    except Exception as exc:
        return {"ok": False, "error": str(exc)}

    try:
        client.ping()
        return {"ok": True}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}
    finally:
        try:
            client.close()
        except Exception:
            pass


def _check_writable_dir(path: Path) -> dict:
    resolved = path.resolve()
    try:
        resolved.mkdir(parents=True, exist_ok=True)
        fd, probe_path = tempfile.mkstemp(prefix=".healthcheck-", dir=resolved)
        os.close(fd)
        os.unlink(probe_path)
        return {"ok": True, "path": str(resolved)}
    except Exception as exc:
        return {"ok": False, "path": str(resolved), "error": str(exc)}


def _read_version(version_file: Path) -> str:
    try:
        return version_file.read_text(encoding="utf-8").strip() or "unknown"
    except Exception:
        return "unknown"
