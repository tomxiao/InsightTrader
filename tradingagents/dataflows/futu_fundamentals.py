from __future__ import annotations

from .formatting import unsupported_response
from .market_resolver import detect_market


def get_fundamentals(ticker: str, curr_date: str = None) -> str:
    return unsupported_response("futu", "get_fundamentals", detect_market(ticker), "Futu fundamentals were not validated in the current integration.")


def get_balance_sheet(ticker: str, freq: str = "quarterly", curr_date: str = None):
    return unsupported_response("futu", "get_balance_sheet", detect_market(ticker), "Futu balance sheet support was not validated.")


def get_cashflow(ticker: str, freq: str = "quarterly", curr_date: str = None):
    return unsupported_response("futu", "get_cashflow", detect_market(ticker), "Futu cash flow support was not validated.")


def get_income_statement(ticker: str, freq: str = "quarterly", curr_date: str = None):
    return unsupported_response("futu", "get_income_statement", detect_market(ticker), "Futu income statement support was not validated.")
