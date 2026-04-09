from __future__ import annotations

import pandas as pd

from .formatting import format_dataframe_report
from .futu_common import get_futu_quote_context, is_success
from .indicator_utils import compute_indicator_report
from .market_resolver import detect_market, normalize_symbol_for_vendor


def _fetch_futu_ohlcv(symbol: str, start_date: str, end_date: str) -> tuple[pd.DataFrame, str, str]:
    market = detect_market(symbol)
    futu_symbol = normalize_symbol_for_vendor(symbol, "futu", market)
    quote_ctx = get_futu_quote_context()
    try:
        ret, dataframe, _page = quote_ctx.request_history_kline(
            futu_symbol,
            start=start_date,
            end=end_date,
            max_count=None,
        )
        if not is_success(ret):
            raise RuntimeError(str(dataframe))
        if dataframe is None or dataframe.empty:
            return pd.DataFrame(), market, futu_symbol
        normalized = dataframe.rename(
            columns={
                "time_key": "Date",
                "open": "Open",
                "high": "High",
                "low": "Low",
                "close": "Close",
                "volume": "Volume",
                "turnover": "Amount",
            }
        ).copy()
        normalized["Date"] = pd.to_datetime(normalized["Date"], errors="coerce").dt.strftime(
            "%Y-%m-%d"
        )
        normalized = normalized[
            [
                column
                for column in ["Date", "Open", "High", "Low", "Close", "Volume", "Amount"]
                if column in normalized.columns
            ]
        ]
        return normalized, market, futu_symbol
    finally:
        quote_ctx.close()


def get_stock(symbol: str, start_date: str, end_date: str) -> str:
    try:
        dataframe, market, futu_symbol = _fetch_futu_ohlcv(symbol, start_date, end_date)
        return format_dataframe_report(
            f"Futu stock data for {symbol}",
            dataframe,
            {
                "Vendor": "futu",
                "Market": market,
                "Vendor symbol": futu_symbol,
                "Start date": start_date,
                "End date": end_date,
            },
        )
    except Exception as exc:
        return f"Error retrieving stock data for {symbol} via futu: {exc}"


def get_indicator(symbol: str, indicator: str, curr_date: str, look_back_days: int = 30) -> str:
    try:
        start_date = (
            pd.Timestamp(curr_date) - pd.Timedelta(days=max(look_back_days * 3, 365))
        ).strftime("%Y-%m-%d")
        dataframe, _market, _futu_symbol = _fetch_futu_ohlcv(symbol, start_date, curr_date)
        return compute_indicator_report(dataframe, indicator, curr_date, look_back_days)
    except Exception as exc:
        return f"Error retrieving indicator `{indicator}` for {symbol} via futu: {exc}"
