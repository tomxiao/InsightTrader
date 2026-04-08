from __future__ import annotations

import pandas as pd

from .akshare_common import get_akshare_module, run_without_proxy
from .formatting import format_dataframe_report, unsupported_response
from .market_resolver import detect_market, normalize_symbol_for_vendor


def get_news(ticker: str, start_date: str, end_date: str) -> str:
    ak = get_akshare_module()
    market = detect_market(ticker)
    symbol = normalize_symbol_for_vendor(ticker, "akshare", market)
    try:
        try:
            dataframe = run_without_proxy(lambda: ak.stock_news_em(symbol=symbol))
        except Exception:
            dataframe = run_without_proxy(lambda: ak.stock_news_main_cx())
        return format_dataframe_report(
            f"AKShare news for {ticker}",
            dataframe if isinstance(dataframe, pd.DataFrame) else pd.DataFrame(dataframe),
            {"Vendor": "akshare", "Market": market, "Vendor symbol": symbol, "Start date": start_date, "End date": end_date},
        )
    except Exception as exc:
        return f"Error retrieving news for {ticker} via akshare: {exc}"


def get_global_news(curr_date: str, look_back_days: int = 7, limit: int = 50) -> str:
    ak = get_akshare_module()
    try:
        dataframe = run_without_proxy(lambda: ak.news_cctv(date=curr_date.replace("-", "")))
        if isinstance(dataframe, pd.DataFrame) and not dataframe.empty:
            dataframe = dataframe.head(limit)
        return format_dataframe_report(
            "AKShare global news",
            dataframe if isinstance(dataframe, pd.DataFrame) else pd.DataFrame(dataframe),
            {"Vendor": "akshare", "Date": curr_date, "Look back days": look_back_days, "Limit": limit},
        )
    except Exception as exc:
        return f"Error retrieving global news via akshare: {exc}"


def get_insider_transactions(ticker: str) -> str:
    market = detect_market(ticker)
    return unsupported_response("akshare", "get_insider_transactions", market, "No validated insider transactions endpoint is wired.")
