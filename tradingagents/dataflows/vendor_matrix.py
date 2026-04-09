from __future__ import annotations

from .market_resolver import MARKET_A_SHARE, MARKET_HK, MARKET_US

DEFAULT_MARKET_TOOL_VENDORS = {
    MARKET_A_SHARE: {
        "get_stock_data": "tushare",
        "get_indicators": "tushare",
        "get_fundamentals": "tushare",
        "get_balance_sheet": "tushare",
        "get_cashflow": "tushare",
        "get_income_statement": "tushare",
        "get_news": "akshare",
        "get_global_news": "tushare",
        "get_insider_transactions": None,
    },
    MARKET_HK: {
        "get_stock_data": "tushare",
        "get_indicators": "tushare",
        "get_fundamentals": "akshare",
        "get_balance_sheet": "akshare",
        "get_cashflow": "akshare",
        "get_income_statement": "akshare",
        "get_news": "akshare",
        "get_global_news": "tushare",
        "get_insider_transactions": None,
    },
    MARKET_US: {
        "get_stock_data": "tushare",
        "get_indicators": "tushare",
        "get_fundamentals": "finnhub",
        "get_balance_sheet": "finnhub",
        "get_cashflow": "finnhub",
        "get_income_statement": "finnhub",
        "get_news": "finnhub",
        "get_global_news": "finnhub",
        "get_insider_transactions": "finnhub",
    },
}
