from .y_finance import (
    get_YFin_data_online,
    get_stock_stats_indicators_window,
    get_fundamentals as get_yfinance_fundamentals,
    get_balance_sheet as get_yfinance_balance_sheet,
    get_cashflow as get_yfinance_cashflow,
    get_income_statement as get_yfinance_income_statement,
    get_insider_transactions as get_yfinance_insider_transactions,
)
from .yfinance_news import get_news_yfinance, get_global_news_yfinance
from .alpha_vantage import (
    get_stock as get_alpha_vantage_stock,
    get_indicator as get_alpha_vantage_indicator,
    get_fundamentals as get_alpha_vantage_fundamentals,
    get_balance_sheet as get_alpha_vantage_balance_sheet,
    get_cashflow as get_alpha_vantage_cashflow,
    get_income_statement as get_alpha_vantage_income_statement,
    get_insider_transactions as get_alpha_vantage_insider_transactions,
    get_news as get_alpha_vantage_news,
    get_global_news as get_alpha_vantage_global_news,
)
from .alpha_vantage_common import AlphaVantageRateLimitError

# Configuration and routing logic
from .config import get_config, get_runtime_context
from .formatting import unsupported_response
from .market_resolver import detect_market, normalize_symbol_for_vendor
from tradingagents.observability import emit_trace_event
from .tushare_stock import get_stock as get_tushare_stock, get_indicator as get_tushare_indicator
from .tushare_fundamentals import (
    get_fundamentals as get_tushare_fundamentals,
    get_balance_sheet as get_tushare_balance_sheet,
    get_cashflow as get_tushare_cashflow,
    get_income_statement as get_tushare_income_statement,
)
from .tushare_news import (
    get_news as get_tushare_news,
    get_global_news as get_tushare_global_news,
    get_insider_transactions as get_tushare_insider_transactions,
)
from .futu_stock import get_stock as get_futu_stock, get_indicator as get_futu_indicator
from .futu_fundamentals import (
    get_fundamentals as get_futu_fundamentals,
    get_balance_sheet as get_futu_balance_sheet,
    get_cashflow as get_futu_cashflow,
    get_income_statement as get_futu_income_statement,
)
from .futu_news import (
    get_news as get_futu_news,
    get_global_news as get_futu_global_news,
    get_insider_transactions as get_futu_insider_transactions,
)
from .finnhub_stock import get_stock as get_finnhub_stock, get_indicator as get_finnhub_indicator
from .finnhub_fundamentals import (
    get_fundamentals as get_finnhub_fundamentals,
    get_balance_sheet as get_finnhub_balance_sheet,
    get_cashflow as get_finnhub_cashflow,
    get_income_statement as get_finnhub_income_statement,
)
from .finnhub_news import (
    get_news as get_finnhub_news,
    get_global_news as get_finnhub_global_news,
    get_insider_transactions as get_finnhub_insider_transactions,
)
from .akshare_stock import get_stock as get_akshare_stock, get_indicator as get_akshare_indicator
from .akshare_fundamentals import (
    get_fundamentals as get_akshare_fundamentals,
    get_balance_sheet as get_akshare_balance_sheet,
    get_cashflow as get_akshare_cashflow,
    get_income_statement as get_akshare_income_statement,
)
from .akshare_news import (
    get_news as get_akshare_news,
    get_global_news as get_akshare_global_news,
    get_insider_transactions as get_akshare_insider_transactions,
)

# Tools organized by category
TOOLS_CATEGORIES = {
    "core_stock_apis": {
        "description": "OHLCV stock price data",
        "tools": [
            "get_stock_data"
        ]
    },
    "technical_indicators": {
        "description": "Technical analysis indicators",
        "tools": [
            "get_indicators"
        ]
    },
    "fundamental_data": {
        "description": "Company fundamentals",
        "tools": [
            "get_fundamentals",
            "get_balance_sheet",
            "get_cashflow",
            "get_income_statement"
        ]
    },
    "news_data": {
        "description": "News and insider data",
        "tools": [
            "get_news",
            "get_global_news",
            "get_insider_transactions",
        ]
    }
}

VENDOR_LIST = [
    "yfinance",
    "alpha_vantage",
    "tushare",
    "futu",
    "finnhub",
    "akshare",
]

# Mapping of methods to their vendor-specific implementations
VENDOR_METHODS = {
    # core_stock_apis
    "get_stock_data": {
        "alpha_vantage": get_alpha_vantage_stock,
        "yfinance": get_YFin_data_online,
        "tushare": get_tushare_stock,
        "futu": get_futu_stock,
        "finnhub": get_finnhub_stock,
        "akshare": get_akshare_stock,
    },
    # technical_indicators
    "get_indicators": {
        "alpha_vantage": get_alpha_vantage_indicator,
        "yfinance": get_stock_stats_indicators_window,
        "tushare": get_tushare_indicator,
        "futu": get_futu_indicator,
        "finnhub": get_finnhub_indicator,
        "akshare": get_akshare_indicator,
    },
    # fundamental_data
    "get_fundamentals": {
        "alpha_vantage": get_alpha_vantage_fundamentals,
        "yfinance": get_yfinance_fundamentals,
        "tushare": get_tushare_fundamentals,
        "futu": get_futu_fundamentals,
        "finnhub": get_finnhub_fundamentals,
        "akshare": get_akshare_fundamentals,
    },
    "get_balance_sheet": {
        "alpha_vantage": get_alpha_vantage_balance_sheet,
        "yfinance": get_yfinance_balance_sheet,
        "tushare": get_tushare_balance_sheet,
        "futu": get_futu_balance_sheet,
        "finnhub": get_finnhub_balance_sheet,
        "akshare": get_akshare_balance_sheet,
    },
    "get_cashflow": {
        "alpha_vantage": get_alpha_vantage_cashflow,
        "yfinance": get_yfinance_cashflow,
        "tushare": get_tushare_cashflow,
        "futu": get_futu_cashflow,
        "finnhub": get_finnhub_cashflow,
        "akshare": get_akshare_cashflow,
    },
    "get_income_statement": {
        "alpha_vantage": get_alpha_vantage_income_statement,
        "yfinance": get_yfinance_income_statement,
        "tushare": get_tushare_income_statement,
        "futu": get_futu_income_statement,
        "finnhub": get_finnhub_income_statement,
        "akshare": get_akshare_income_statement,
    },
    # news_data
    "get_news": {
        "alpha_vantage": get_alpha_vantage_news,
        "yfinance": get_news_yfinance,
        "tushare": get_tushare_news,
        "futu": get_futu_news,
        "finnhub": get_finnhub_news,
        "akshare": get_akshare_news,
    },
    "get_global_news": {
        "yfinance": get_global_news_yfinance,
        "alpha_vantage": get_alpha_vantage_global_news,
        "tushare": get_tushare_global_news,
        "futu": get_futu_global_news,
        "finnhub": get_finnhub_global_news,
        "akshare": get_akshare_global_news,
    },
    "get_insider_transactions": {
        "alpha_vantage": get_alpha_vantage_insider_transactions,
        "yfinance": get_yfinance_insider_transactions,
        "tushare": get_tushare_insider_transactions,
        "futu": get_futu_insider_transactions,
        "finnhub": get_finnhub_insider_transactions,
        "akshare": get_akshare_insider_transactions,
    },
}

def get_category_for_method(method: str) -> str:
    """Get the category that contains the specified method."""
    for category, info in TOOLS_CATEGORIES.items():
        if method in info["tools"]:
            return category
    raise ValueError(f"Method '{method}' not found in any category")

def get_vendor(category: str, method: str = None) -> str:
    """Get the configured vendor for a data category or specific tool method.
    Tool-level configuration takes precedence over category-level.
    """
    config = get_config()

    # Check tool-level configuration first (if method provided)
    if method:
        tool_vendors = config.get("tool_vendors", {})
        if method in tool_vendors:
            return tool_vendors[method]

    # Fall back to category-level configuration
    return config.get("data_vendors", {}).get(category, "default")


def _extract_ticker_from_call(method: str, args, kwargs) -> str | None:
    if method == "get_global_news":
        if "ticker" in kwargs and kwargs["ticker"]:
            return kwargs["ticker"]
        return get_runtime_context().get("ticker")

    if args:
        return args[0]
    for key in ["ticker", "symbol"]:
        if key in kwargs and kwargs[key]:
            return kwargs[key]
    return None


def _resolve_market_vendor(method: str, args, kwargs) -> tuple[str | None, str | None]:
    config = get_config()
    if not config.get("market_routing_enabled", False):
        return None, None

    ticker = _extract_ticker_from_call(method, args, kwargs)
    if not ticker:
        return None, None

    market = detect_market(ticker)
    vendor = config.get("market_tool_vendors", {}).get(market, {}).get(method)
    return vendor, market


def _normalize_call_args(method: str, vendor: str, market: str | None, args, kwargs):
    if not args or method == "get_global_news":
        return args, kwargs

    ticker = _extract_ticker_from_call(method, args, kwargs)
    if not ticker or not market:
        return args, kwargs

    normalized_args = list(args)
    normalized_args[0] = normalize_symbol_for_vendor(ticker, vendor, market)
    return tuple(normalized_args), kwargs


def _emit_route_event(event: str, **payload):
    config = get_config()
    runtime_context = get_runtime_context()
    emit_trace_event(
        "route_events.jsonl",
        event,
        config=config,
        runtime_context=runtime_context,
        run_id=runtime_context.get("run_id"),
        **payload,
    )


def _build_route_context(method: str, market_vendor: str | None, market: str | None, args, kwargs):
    category = get_category_for_method(method)
    configured_primary = get_vendor(category, method)
    ticker = _extract_ticker_from_call(method, args, kwargs)
    runtime_context = get_runtime_context()
    config = get_config()

    context = {
        "method": method,
        "category": category,
        "ticker_raw": ticker,
        "market": market,
        "market_vendor": market_vendor,
        "configured_primary": configured_primary,
        "market_routing_enabled": config.get("market_routing_enabled", False),
        "runtime_ticker": runtime_context.get("ticker"),
    }
    return context


def _returned_error_payload(result):
    if not isinstance(result, str):
        return None
    stripped = result.strip()
    if not stripped.startswith("Error "):
        return None
    return {
        "outcome": "error_string",
        "error_code": "vendor_returned_error",
        "error_message": stripped,
    }

def route_to_vendor(method: str, *args, **kwargs):
    """Route method calls to the appropriate vendor implementation."""
    if method not in VENDOR_METHODS:
        raise ValueError(f"Method '{method}' not supported")

    market_vendor, market = _resolve_market_vendor(method, args, kwargs)
    route_context = _build_route_context(method, market_vendor, market, args, kwargs)
    if market_vendor is None and market is not None:
        _emit_route_event(
            "route.blocked",
            **route_context,
            routing_mode="market_tool_vendors",
            vendor_chain=[],
            outcome="blocked",
            reason="no_best_vendor",
        )
        return unsupported_response("routing", method, market, "No best vendor is configured for this market and tool.")

    if market_vendor:
        vendor_chain = [market_vendor]
        routing_mode = "market_tool_vendors"
    else:
        vendor_config = route_context["configured_primary"]
        primary_vendors = [v.strip() for v in vendor_config.split(",") if v.strip()]
        all_available_vendors = list(VENDOR_METHODS[method].keys())
        vendor_chain = primary_vendors.copy()
        for vendor in all_available_vendors:
            if vendor not in vendor_chain:
                vendor_chain.append(vendor)
        routing_mode = "category_fallback"

    _emit_route_event(
        "route.decision",
        **route_context,
        routing_mode=routing_mode,
        vendor_chain=vendor_chain,
    )

    for attempt_index, vendor in enumerate(vendor_chain, start=1):
        if vendor not in VENDOR_METHODS[method]:
            continue

        vendor_impl = VENDOR_METHODS[method][vendor]
        impl_func = vendor_impl[0] if isinstance(vendor_impl, list) else vendor_impl
        call_args, call_kwargs = _normalize_call_args(method, vendor, market, args, kwargs)
        normalized_symbol = None
        if call_args and call_args != args:
            normalized_symbol = call_args[0]
        elif call_args:
            normalized_symbol = call_args[0]

        _emit_route_event(
            "route.attempt",
            **route_context,
            routing_mode=routing_mode,
            vendor_chain=vendor_chain,
            attempt_index=attempt_index,
            vendor=vendor,
            normalized_symbol=normalized_symbol,
        )

        try:
            result = impl_func(*call_args, **call_kwargs)
            result_payload = _returned_error_payload(result) or {"outcome": "success"}
            _emit_route_event(
                "route.result",
                **route_context,
                routing_mode=routing_mode,
                vendor_chain=vendor_chain,
                vendor=vendor,
                attempt_index=attempt_index,
                normalized_symbol=normalized_symbol,
                chosen_vendor=vendor,
                **result_payload,
            )
            return result
        except AlphaVantageRateLimitError:
            _emit_route_event(
                "route.result",
                **route_context,
                routing_mode=routing_mode,
                vendor_chain=vendor_chain,
                vendor=vendor,
                attempt_index=attempt_index,
                normalized_symbol=normalized_symbol,
                outcome="rate_limit",
                error_code="alpha_vantage_rate_limit",
            )
            if market_vendor:
                return f"Alpha Vantage rate limit exceeded while calling `{method}` for market `{market}`."
            continue
        except Exception as exc:
            _emit_route_event(
                "route.result",
                **route_context,
                routing_mode=routing_mode,
                vendor_chain=vendor_chain,
                vendor=vendor,
                attempt_index=attempt_index,
                normalized_symbol=normalized_symbol,
                outcome="error",
                error_code=exc.__class__.__name__,
                error_message=str(exc),
            )
            raise

    _emit_route_event(
        "route.result",
        **route_context,
        routing_mode=routing_mode,
        vendor_chain=vendor_chain,
        outcome="exhausted",
        error_code="no_available_vendor",
    )
    raise RuntimeError(f"No available vendor for '{method}'")