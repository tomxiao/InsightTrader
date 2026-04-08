from __future__ import annotations

import os

import finnhub


def get_finnhub_client() -> finnhub.Client:
    token = os.getenv("FINNHUB_TOKEN")
    if not token:
        raise ValueError("FINNHUB_TOKEN environment variable is not set.")
    return finnhub.Client(api_key=token)
