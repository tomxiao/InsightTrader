from __future__ import annotations

import sys
import uvicorn

from ta_service.config.logging_config import setup_logging

setup_logging()

from ta_service.app.factory import create_app
from ta_service.config.settings import get_settings


app = create_app()


def run() -> None:
    settings = get_settings()
    try:
        uvicorn.run(
            "ta_service.main:app",
            host=settings.host,
            port=settings.port,
            reload=settings.environment == "development",
        )
    except SystemExit as exc:
        raise
    except OSError as exc:
        print(
            f"[ta_service] 启动失败：无法绑定 {settings.host}:{settings.port}，"
            f"端口可能已被占用。错误：{exc}",
            file=sys.stderr,
        )
        sys.exit(1)


if __name__ == "__main__":
    run()
