from __future__ import annotations

import os
from typing import Any

os.environ.setdefault("PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION", "python")

RET_OK = 0


def get_futu_quote_context() -> Any:
    try:
        from moomoo import OpenQuoteContext
    except ImportError as exc:
        raise ImportError(
            "Optional dependency `moomoo` is not installed in the active environment. "
            "Install `moomoo-api` to enable the futu vendor."
        ) from exc
    host = os.getenv("FUTU_OPEND_HOST", "127.0.0.1")
    port = int(os.getenv("FUTU_OPEND_PORT", "11111"))
    return OpenQuoteContext(host=host, port=port)


def is_success(ret_code: int) -> bool:
    return ret_code == RET_OK
