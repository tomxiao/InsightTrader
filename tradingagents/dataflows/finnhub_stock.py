from __future__ import annotations

from datetime import datetime

import pandas as pd

from .finnhub_common import get_finnhub_client
from .formatting import format_dataframe_report
from .indicator_utils import compute_indicator_report
from .market_resolver import detect_market, normalize_symbol_for_vendor


def _fetch_finnhub_ohlcv(
    symbol: str, start_date: str, end_date: str
) -> tuple[pd.DataFrame, str, str]:
    market = detect_market(symbol)
    finnhub_symbol = normalize_symbol_for_vendor(symbol, "finnhub", market)
    client = get_finnhub_client()
    start_ts = int(datetime.strptime(start_date, "%Y-%m-%d").timestamp())
    end_ts = int(datetime.strptime(end_date, "%Y-%m-%d").timestamp())
    candles = client.stock_candles(finnhub_symbol, "D", start_ts, end_ts)
    if not candles or candles.get("s") != "ok":
        raise RuntimeError(str(candles))
    dataframe = pd.DataFrame(
        {
            "Date": pd.to_datetime(candles["t"], unit="s").strftime("%Y-%m-%d"),
            "Open": candles["o"],
            "High": candles["h"],
            "Low": candles["l"],
            "Close": candles["c"],
            "Volume": candles["v"],
        }
    )
    return dataframe, market, finnhub_symbol


def get_stock(symbol: str, start_date: str, end_date: str) -> str:
    try:
        dataframe, market, finnhub_symbol = _fetch_finnhub_ohlcv(symbol, start_date, end_date)
        return format_dataframe_report(
            f"Finnhub stock data for {symbol}",
            dataframe,
            {
                "Vendor": "finnhub",
                "Market": market,
                "Vendor symbol": finnhub_symbol,
                "Start date": start_date,
                "End date": end_date,
            },
        )
    except Exception as exc:
        return f"Error retrieving stock data for {symbol} via finnhub: {exc}"


def get_indicator(symbol: str, indicator: str, curr_date: str, look_back_days: int = 30) -> str:
    try:
        start_date = (
            pd.Timestamp(curr_date) - pd.Timedelta(days=max(look_back_days * 3, 365))
        ).strftime("%Y-%m-%d")
        dataframe, _market, _finnhub_symbol = _fetch_finnhub_ohlcv(symbol, start_date, curr_date)
        return compute_indicator_report(dataframe, indicator, curr_date, look_back_days)
    except Exception as exc:
        return f"Error retrieving indicator `{indicator}` for {symbol} via finnhub: {exc}"
