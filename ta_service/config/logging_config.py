"""日志配置：落盘到 logs/ta_service.log，按天轮转，保留 14 天。"""
from __future__ import annotations

import logging
import logging.handlers
import os
from pathlib import Path

_LOG_DIR = Path(__file__).resolve().parents[2] / "logs"
_LOG_FILE = _LOG_DIR / "ta_service.log"

_LOG_LEVEL = os.getenv("TA_SERVICE_LOG_LEVEL", "INFO").upper()

_FMT = "%(asctime)s %(levelname)-8s %(name)s | %(message)s"
_DATE_FMT = "%Y-%m-%d %H:%M:%S"


def setup_logging() -> None:
    """初始化日志：INFO+ 落盘，WARNING+ 同时输出到 stderr。幂等，多次调用安全。"""
    root = logging.getLogger()
    if root.handlers:
        return

    _LOG_DIR.mkdir(parents=True, exist_ok=True)

    formatter = logging.Formatter(_FMT, datefmt=_DATE_FMT)

    # 文件 handler：每天轮转，保留 14 天
    file_handler = logging.handlers.TimedRotatingFileHandler(
        _LOG_FILE,
        when="midnight",
        interval=1,
        backupCount=14,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)

    # 控制台 handler：INFO+ 输出，DEBUG 仅写文件不刷屏
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)

    level = getattr(logging, _LOG_LEVEL, logging.INFO)
    root.setLevel(level)
    root.addHandler(file_handler)
    root.addHandler(console_handler)

    logging.getLogger("uvicorn.access").propagate = False
    logging.getLogger("uvicorn.error").propagate = True
