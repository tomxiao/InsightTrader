from __future__ import annotations

import pandas as pd

from .finnhub_common import get_finnhub_client
from .formatting import format_dataframe_report, format_text_report
from .market_resolver import detect_market, normalize_symbol_for_vendor


def get_fundamentals(ticker: str, curr_date: str = None) -> str:
    try:
        market = detect_market(ticker)
        symbol = normalize_symbol_for_vendor(ticker, "finnhub", market)
        profile = get_finnhub_client().company_profile2(symbol=symbol)
        if not profile:
            return f"No fundamentals data found for {ticker} via finnhub."
        lines = [f"{key}: {value}" for key, value in profile.items() if value not in (None, "", [])]
        return format_text_report(
            f"Finnhub fundamentals for {ticker}",
            lines,
            {"Vendor": "finnhub", "Market": market, "Vendor symbol": symbol},
        )
    except Exception as exc:
        return f"Error retrieving fundamentals for {ticker} via finnhub: {exc}"


def _financials_report_to_frame(ticker: str, curr_date: str | None = None) -> tuple[dict, pd.DataFrame, str, str]:
    market = detect_market(ticker)
    symbol = normalize_symbol_for_vendor(ticker, "finnhub", market)
    report = get_finnhub_client().financials_reported(symbol=symbol, freq="annual")
    data = report.get("data", []) if isinstance(report, dict) else []
    if curr_date:
        data = [item for item in data if item.get("endDate", "") <= curr_date]
    rows = []
    for item in data:
        report_date = item.get("endDate")
        report_data = item.get("report", {})
        for section_name in ["bs", "cf", "ic"]:
            for entry in report_data.get(section_name, []):
                rows.append(
                    {
                        "report_date": report_date,
                        "section": section_name,
                        "label": entry.get("label"),
                        "concept": entry.get("concept"),
                        "value": entry.get("value"),
                        "unit": entry.get("unit"),
                    }
                )
    return report, pd.DataFrame(rows), market, symbol


def _section_report(ticker: str, section_name: str, title: str, freq: str = "quarterly", curr_date: str = None) -> str:
    try:
        _report, dataframe, market, symbol = _financials_report_to_frame(ticker, curr_date)
        filtered = dataframe[dataframe["section"] == section_name] if not dataframe.empty else dataframe
        return format_dataframe_report(
            title,
            filtered,
            {"Vendor": "finnhub", "Market": market, "Vendor symbol": symbol, "Frequency": freq},
        )
    except Exception as exc:
        return f"Error retrieving {title.lower()} for {ticker} via finnhub: {exc}"


def get_balance_sheet(ticker: str, freq: str = "quarterly", curr_date: str = None):
    return _section_report(ticker, "bs", f"Finnhub balance sheet for {ticker}", freq, curr_date)


def get_cashflow(ticker: str, freq: str = "quarterly", curr_date: str = None):
    return _section_report(ticker, "cf", f"Finnhub cash flow for {ticker}", freq, curr_date)


def get_income_statement(ticker: str, freq: str = "quarterly", curr_date: str = None):
    return _section_report(ticker, "ic", f"Finnhub income statement for {ticker}", freq, curr_date)
