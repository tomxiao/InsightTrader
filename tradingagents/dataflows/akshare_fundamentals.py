from __future__ import annotations

import pandas as pd

from .akshare_common import get_akshare_module, run_without_proxy
from .formatting import format_dataframe_report
from .market_resolver import (
    MARKET_A_SHARE,
    MARKET_HK,
    detect_market,
    extract_a_share_code,
    infer_a_share_exchange,
    normalize_symbol_for_vendor,
)


def _a_share_prefixed_symbol(ticker: str) -> str:
    code = extract_a_share_code(ticker)
    return f"{infer_a_share_exchange(code)}{code}"


def get_fundamentals(ticker: str, curr_date: str = None) -> str:
    ak = get_akshare_module()
    market = detect_market(ticker)
    symbol = normalize_symbol_for_vendor(ticker, "akshare", market)
    try:
        if market == MARKET_A_SHARE:
            dataframe = run_without_proxy(lambda: ak.stock_financial_abstract(symbol=symbol))
        elif market == MARKET_HK:
            try:
                dataframe = run_without_proxy(lambda: ak.stock_hk_company_profile_em(symbol=symbol))
            except Exception:
                dataframe = run_without_proxy(
                    lambda: ak.stock_financial_hk_report_em(
                        stock=symbol, symbol="资产负债表", indicator="年报"
                    ).head(50)
                )
        else:
            dataframe = run_without_proxy(
                lambda: ak.stock_financial_us_report_em(
                    stock=symbol, symbol="资产负债表", indicator="年报"
                ).head(50)
            )
        return format_dataframe_report(
            f"AKShare fundamentals for {ticker}",
            dataframe,
            {"Vendor": "akshare", "Market": market, "Vendor symbol": symbol},
        )
    except Exception as exc:
        return f"Error retrieving fundamentals for {ticker} via akshare: {exc}"


def get_balance_sheet(ticker: str, freq: str = "quarterly", curr_date: str = None):
    return _statement_report(ticker, "balance_sheet", freq)


def get_cashflow(ticker: str, freq: str = "quarterly", curr_date: str = None):
    return _statement_report(ticker, "cashflow", freq)


def get_income_statement(ticker: str, freq: str = "quarterly", curr_date: str = None):
    return _statement_report(ticker, "income_statement", freq)


def _statement_report(ticker: str, statement_type: str, freq: str) -> str:
    ak = get_akshare_module()
    market = detect_market(ticker)
    symbol = normalize_symbol_for_vendor(ticker, "akshare", market)
    try:
        if market == MARKET_A_SHARE:
            prefixed = _a_share_prefixed_symbol(ticker)
            factory = {
                "balance_sheet": lambda: ak.stock_balance_sheet_by_report_em(symbol=prefixed),
                "cashflow": lambda: ak.stock_cash_flow_sheet_by_report_em(symbol=prefixed),
                "income_statement": lambda: ak.stock_profit_sheet_by_report_em(symbol=prefixed),
            }[statement_type]
            dataframe = run_without_proxy(factory)
        elif market == MARKET_HK:
            section = {
                "balance_sheet": "资产负债表",
                "cashflow": "现金流量表",
                "income_statement": "利润表",
            }[statement_type]
            dataframe = run_without_proxy(
                lambda: ak.stock_financial_hk_report_em(
                    stock=symbol, symbol=section, indicator="年报"
                )
            )
        else:
            section = {
                "balance_sheet": "资产负债表",
                "cashflow": "现金流量表",
                "income_statement": "利润表",
            }[statement_type]
            dataframe = run_without_proxy(
                lambda: ak.stock_financial_us_report_em(
                    stock=symbol, symbol=section, indicator="年报"
                )
            )

        title = {
            "balance_sheet": f"AKShare balance sheet for {ticker}",
            "cashflow": f"AKShare cash flow for {ticker}",
            "income_statement": f"AKShare income statement for {ticker}",
        }[statement_type]
        return format_dataframe_report(
            title,
            dataframe if isinstance(dataframe, pd.DataFrame) else pd.DataFrame(dataframe),
            {"Vendor": "akshare", "Market": market, "Vendor symbol": symbol, "Frequency": freq},
        )
    except Exception as exc:
        return f"Error retrieving {statement_type} for {ticker} via akshare: {exc}"
