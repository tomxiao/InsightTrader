from __future__ import annotations

from .formatting import unsupported_response
from .market_resolver import detect_market


def get_news(ticker: str, start_date: str, end_date: str) -> str:
    return unsupported_response(
        "futu",
        "get_news",
        detect_market(ticker),
        "Futu news support was not validated in the current integration.",
    )


def get_global_news(curr_date: str, look_back_days: int = 7, limit: int = 50) -> str:
    return unsupported_response(
        "futu",
        "get_global_news",
        None,
        "Futu global news support was not validated in the current integration.",
    )


def get_insider_transactions(ticker: str) -> str:
    return unsupported_response(
        "futu",
        "get_insider_transactions",
        detect_market(ticker),
        "Futu insider transaction support was not validated in the current integration.",
    )
