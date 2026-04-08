from __future__ import annotations

import pandas as pd

from .finnhub_common import get_finnhub_client
from .formatting import format_dataframe_report
from .market_resolver import detect_market, normalize_symbol_for_vendor


def get_news(ticker: str, start_date: str, end_date: str) -> str:
    try:
        market = detect_market(ticker)
        symbol = normalize_symbol_for_vendor(ticker, "finnhub", market)
        data = get_finnhub_client().company_news(symbol, _from=start_date, to=end_date)
        dataframe = pd.DataFrame(data)
        return format_dataframe_report(
            f"Finnhub news for {ticker}",
            dataframe,
            {"Vendor": "finnhub", "Market": market, "Vendor symbol": symbol, "Start date": start_date, "End date": end_date},
        )
    except Exception as exc:
        return f"Error retrieving news for {ticker} via finnhub: {exc}"


def get_global_news(curr_date: str, look_back_days: int = 7, limit: int = 50) -> str:
    try:
        data = get_finnhub_client().general_news("general", min_id=0)
        dataframe = pd.DataFrame(data).head(limit)
        return format_dataframe_report(
            "Finnhub global news",
            dataframe,
            {"Vendor": "finnhub", "Date": curr_date, "Look back days": look_back_days, "Limit": limit},
        )
    except Exception as exc:
        return f"Error retrieving global news via finnhub: {exc}"


def get_insider_transactions(ticker: str) -> str:
    try:
        market = detect_market(ticker)
        symbol = normalize_symbol_for_vendor(ticker, "finnhub", market)
        data = get_finnhub_client().stock_insider_transactions(symbol=symbol)
        dataframe = pd.DataFrame(data.get("data", []) if isinstance(data, dict) else data)
        return format_dataframe_report(
            f"Finnhub insider transactions for {ticker}",
            dataframe,
            {"Vendor": "finnhub", "Market": market, "Vendor symbol": symbol},
        )
    except Exception as exc:
        return f"Error retrieving insider transactions for {ticker} via finnhub: {exc}"
