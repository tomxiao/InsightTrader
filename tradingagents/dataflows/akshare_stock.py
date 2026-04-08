from __future__ import annotations

import pandas as pd

from .akshare_common import get_akshare_module, run_without_proxy
from .formatting import format_dataframe_report
from .indicator_utils import compute_indicator_report
from .market_resolver import MARKET_A_SHARE, MARKET_HK, MARKET_US, detect_market, normalize_symbol_for_vendor


def _rename_by_position(dataframe: pd.DataFrame, market: str) -> pd.DataFrame:
    columns = list(dataframe.columns)
    if market == MARKET_A_SHARE and len(columns) >= 8:
        mapping = {
            columns[0]: "Date",
            columns[2]: "Open",
            columns[3]: "Close",
            columns[4]: "High",
            columns[5]: "Low",
            columns[6]: "Volume",
            columns[7]: "Amount",
        }
    elif len(columns) >= 7:
        mapping = {
            columns[0]: "Date",
            columns[1]: "Open",
            columns[2]: "Close",
            columns[3]: "High",
            columns[4]: "Low",
            columns[5]: "Volume",
            columns[6]: "Amount",
        }
    else:
        raise ValueError("AKShare returned insufficient columns for OHLCV formatting.")

    renamed = dataframe.rename(columns=mapping).copy()
    renamed["Date"] = pd.to_datetime(renamed["Date"], errors="coerce").dt.strftime("%Y-%m-%d")
    return renamed[[column for column in ["Date", "Open", "High", "Low", "Close", "Volume", "Amount"] if column in renamed.columns]]


def _fetch_akshare_ohlcv(symbol: str, start_date: str, end_date: str) -> tuple[pd.DataFrame, str, str]:
    market = detect_market(symbol)
    vendor_symbol = normalize_symbol_for_vendor(symbol, "akshare", market)
    ak = get_akshare_module()

    def _run():
        if market == MARKET_A_SHARE:
            return ak.stock_zh_a_hist(symbol=vendor_symbol, period="daily", start_date=start_date.replace("-", ""), end_date=end_date.replace("-", ""), adjust="")
        if market == MARKET_HK:
            return ak.stock_hk_hist(symbol=vendor_symbol, period="daily", start_date=start_date.replace("-", ""), end_date=end_date.replace("-", ""), adjust="")
        return ak.stock_us_hist(symbol=vendor_symbol, period="daily", start_date=start_date.replace("-", ""), end_date=end_date.replace("-", ""), adjust="")

    dataframe = run_without_proxy(_run)
    if dataframe is None or dataframe.empty:
        return pd.DataFrame(), market, vendor_symbol
    return _rename_by_position(dataframe, market), market, vendor_symbol


def get_stock(symbol: str, start_date: str, end_date: str) -> str:
    try:
        dataframe, market, vendor_symbol = _fetch_akshare_ohlcv(symbol, start_date, end_date)
        return format_dataframe_report(
            f"AKShare stock data for {symbol}",
            dataframe,
            {
                "Vendor": "akshare",
                "Market": market,
                "Vendor symbol": vendor_symbol,
                "Start date": start_date,
                "End date": end_date,
            },
        )
    except Exception as exc:
        return f"Error retrieving stock data for {symbol} via akshare: {exc}"


def get_indicator(symbol: str, indicator: str, curr_date: str, look_back_days: int = 30) -> str:
    try:
        start_date = (pd.Timestamp(curr_date) - pd.Timedelta(days=max(look_back_days * 3, 365))).strftime("%Y-%m-%d")
        dataframe, _market, _vendor_symbol = _fetch_akshare_ohlcv(symbol, start_date, curr_date)
        return compute_indicator_report(dataframe, indicator, curr_date, look_back_days)
    except Exception as exc:
        return f"Error retrieving indicator `{indicator}` for {symbol} via akshare: {exc}"
