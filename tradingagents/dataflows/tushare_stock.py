from __future__ import annotations

import pandas as pd

from .formatting import format_dataframe_report, standardize_ohlcv_dataframe
from .indicator_utils import compute_indicator_report
from .market_resolver import (
    MARKET_A_SHARE,
    MARKET_HK,
    MARKET_US,
    detect_market,
    normalize_symbol_for_vendor,
)
from .tushare_common import get_tushare_pro


def _fetch_tushare_ohlcv(
    symbol: str, start_date: str, end_date: str
) -> tuple[pd.DataFrame, str, str]:
    market = detect_market(symbol)
    ts_code = normalize_symbol_for_vendor(symbol, "tushare", market)
    pro = get_tushare_pro()
    method_name = {
        MARKET_A_SHARE: "daily",
        MARKET_HK: "hk_daily",
        MARKET_US: "us_daily",
    }[market]
    query = getattr(pro, method_name)
    dataframe = query(
        ts_code=ts_code,
        start_date=start_date.replace("-", ""),
        end_date=end_date.replace("-", ""),
    )
    if dataframe is None or dataframe.empty:
        return pd.DataFrame(), market, ts_code
    normalized = standardize_ohlcv_dataframe(
        dataframe,
        {
            "trade_date": "Date",
            "date": "Date",
            "open": "Open",
            "high": "High",
            "low": "Low",
            "close": "Close",
            "vol": "Volume",
            "amount": "Amount",
        },
        date_column="Date",
    )
    return normalized, market, ts_code


def get_stock(symbol: str, start_date: str, end_date: str) -> str:
    try:
        dataframe, market, ts_code = _fetch_tushare_ohlcv(symbol, start_date, end_date)
        return format_dataframe_report(
            f"Tushare stock data for {symbol}",
            dataframe,
            {
                "Vendor": "tushare",
                "Market": market,
                "Vendor symbol": ts_code,
                "Start date": start_date,
                "End date": end_date,
            },
        )
    except Exception as exc:
        return f"Error retrieving stock data for {symbol} via tushare: {exc}"


def get_indicator(symbol: str, indicator: str, curr_date: str, look_back_days: int = 30) -> str:
    try:
        start_date = (
            pd.Timestamp(curr_date) - pd.Timedelta(days=max(look_back_days * 3, 365))
        ).strftime("%Y-%m-%d")
        dataframe, _market, _ts_code = _fetch_tushare_ohlcv(symbol, start_date, curr_date)
        return compute_indicator_report(dataframe, indicator, curr_date, look_back_days)
    except Exception as exc:
        return f"Error retrieving indicator `{indicator}` for {symbol} via tushare: {exc}"
