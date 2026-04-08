from __future__ import annotations

import os
from contextlib import contextmanager


@contextmanager
def cleared_proxy_environment():
    keys = ["HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy"]
    snapshot = {key: os.environ.get(key) for key in keys}
    try:
        for key in keys:
            os.environ.pop(key, None)
        yield
    finally:
        for key, value in snapshot.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def run_without_proxy(func):
    with cleared_proxy_environment():
        return func()


def get_akshare_module():
    try:
        import akshare as ak
    except ImportError as exc:
        raise ImportError(
            "Optional dependency `akshare` is not installed in the active environment. "
            "Install `akshare` to enable the akshare vendor."
        ) from exc
    return ak
