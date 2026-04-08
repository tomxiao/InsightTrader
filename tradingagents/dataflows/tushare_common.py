from __future__ import annotations

import os

import tushare as ts


def get_tushare_pro():
    token = os.getenv("TUSHARE_TOKEN")
    if not token:
        raise ValueError("TUSHARE_TOKEN environment variable is not set.")
    ts.set_token(token)
    return ts.pro_api(token)
