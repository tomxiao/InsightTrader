import os
from tradingagents.dataflows.vendor_matrix import DEFAULT_MARKET_TOOL_VENDORS

DEFAULT_CONFIG = {
    "project_dir": os.path.abspath(os.path.join(os.path.dirname(__file__), ".")),
    "results_dir": os.getenv("TRADINGAGENTS_RESULTS_DIR", "./results"),
    "data_cache_dir": os.path.join(
        os.path.abspath(os.path.join(os.path.dirname(__file__), ".")),
        "dataflows/data_cache",
    ),
    # LLM settings
    "llm_provider": "deepseek",
    "deep_think_llm": "deepseek-chat",
    "quick_think_llm": "deepseek-chat",
    "backend_url": "https://api.deepseek.com/v1",  # Override for compatible providers like OpenRouter, DeepSeek, or MiniMax
    "llm_timeout": 240,                   # Bound each LLM request so stalled network calls do not hang forever
    "llm_max_retries": 2,                 # Small retry budget for transient upstream/provider failures
    # Provider-specific thinking configuration
    "google_thinking_level": None,      # "high", "minimal", etc.
    "openai_reasoning_effort": None,    # "medium", "high", "low"
    "anthropic_effort": None,           # "high", "medium", "low" (Anthropic only, not used for MiniMax)
    # Output language for user-visible reports, plans, and final decision
    # Internal agent debate can stay in English for reasoning quality
    "output_language": "English",
    # Debate and discussion settings
    "max_debate_rounds": 1,
    "max_risk_discuss_rounds": 1,
    "max_recur_limit": 100,
    # Data vendor configuration
    # Category-level configuration (default for all tools in category)
    "data_vendors": {
        "core_stock_apis": "tushare",       # Options: yfinance, alpha_vantage, tushare, futu, finnhub, akshare
        "technical_indicators": "tushare",  # Options: yfinance, alpha_vantage, tushare, futu, finnhub, akshare
        "fundamental_data": "tushare",      # Options: yfinance, alpha_vantage, tushare, futu, finnhub, akshare
        "news_data": "akshare",             # Options: yfinance, alpha_vantage, tushare, futu, finnhub, akshare
    },
    "market_routing_enabled": True,
    "market_tool_vendors": DEFAULT_MARKET_TOOL_VENDORS,
    # Tool-level configuration (takes precedence over category-level)
    "tool_vendors": {
        # Example: "get_stock_data": "alpha_vantage",  # Override category default
    },
}
