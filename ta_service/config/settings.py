from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    app_name: str = os.getenv("TA_SERVICE_APP_NAME", "ta_service")
    environment: str = os.getenv("TA_SERVICE_ENV", "development")
    host: str = os.getenv("TA_SERVICE_HOST", "127.0.0.1")
    port: int = int(os.getenv("TA_SERVICE_PORT", "8100"))
    api_prefix: str = os.getenv("TA_SERVICE_API_PREFIX", "")

    mongo_uri: str = os.getenv("TA_SERVICE_MONGO_URI", "mongodb://localhost:27017")
    mongo_db_name: str = os.getenv("TA_SERVICE_MONGO_DB", "ta_service")

    redis_url: str = os.getenv("TA_SERVICE_REDIS_URL", "redis://localhost:6379/0")
    redis_queue_key: str = os.getenv("TA_SERVICE_REDIS_QUEUE_KEY", "ta_service:analysis:queue")
    analysis_task_ttl_seconds: int = int(os.getenv("TA_SERVICE_ANALYSIS_TASK_TTL_SECONDS", "180"))

    results_root: Path = Path(os.getenv("TA_SERVICE_RESULTS_DIR", "./results/analysis"))
    reports_root: Path = Path(os.getenv("TA_SERVICE_REPORTS_DIR", "./reports"))
    logs_root: Path = Path(os.getenv("TA_SERVICE_LOG_DIR", "./logs"))
    version_file: Path = Path(
        os.getenv("TA_SERVICE_VERSION_FILE", str(Path.cwd() / "deploy" / "VERSION"))
    )
    followup_report_context_chars: int = int(
        os.getenv("TA_SERVICE_FOLLOWUP_REPORT_CONTEXT_CHARS", "8000")
    )
    followup_history_turns: int = int(os.getenv("TA_SERVICE_FOLLOWUP_HISTORY_TURNS", "6"))
    auth_token_prefix: str = os.getenv("TA_SERVICE_AUTH_TOKEN_PREFIX", "dev-token")
    auth_session_ttl_seconds: int = int(
        os.getenv("TA_SERVICE_AUTH_SESSION_TTL_SECONDS", str(7 * 24 * 60 * 60))
    )
    default_output_language: str = os.getenv("TA_SERVICE_DEFAULT_OUTPUT_LANGUAGE", "Chinese")
    cors_origins: tuple[str, ...] = tuple(
        origin.strip()
        for origin in os.getenv(
            "TA_SERVICE_CORS_ORIGINS",
            "http://127.0.0.1:3100,http://localhost:3100",
        ).split(",")
        if origin.strip()
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
