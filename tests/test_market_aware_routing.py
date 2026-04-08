import unittest
from unittest.mock import patch

from tradingagents.dataflows.config import clear_runtime_context, get_config, set_config, set_runtime_context
from tradingagents.dataflows.interface import VENDOR_METHODS, route_to_vendor
from tradingagents.dataflows.market_resolver import detect_market, normalize_symbol_for_vendor


class MarketAwareRoutingTests(unittest.TestCase):
    def setUp(self):
        self.original_config = get_config()
        set_config(
            {
                "market_routing_enabled": True,
                "market_tool_vendors": {
                    "a_share": {
                        "get_stock_data": "tushare",
                        "get_insider_transactions": None,
                    },
                    "hk": {
                        "get_fundamentals": "akshare",
                    },
                    "us": {
                        "get_global_news": "finnhub",
                    },
                },
            }
        )
        clear_runtime_context()

    def tearDown(self):
        clear_runtime_context()
        set_config(self.original_config)

    def test_detect_market_supports_a_h_us(self):
        self.assertEqual(detect_market("600519"), "a_share")
        self.assertEqual(detect_market("00700.HK"), "hk")
        self.assertEqual(detect_market("AAPL"), "us")

    def test_normalize_symbol_for_vendor_matches_expected_formats(self):
        self.assertEqual(normalize_symbol_for_vendor("600519", "tushare"), "600519.SH")
        self.assertEqual(normalize_symbol_for_vendor("00700.HK", "futu"), "HK.00700")
        self.assertEqual(normalize_symbol_for_vendor("AAPL", "finnhub"), "AAPL")

    def test_route_to_vendor_uses_market_specific_vendor_for_stock_data(self):
        with patch.dict(VENDOR_METHODS["get_stock_data"], {"tushare": lambda symbol, *_args, **_kwargs: symbol}, clear=False):
            result = route_to_vendor("get_stock_data", "600519", "2026-01-01", "2026-02-01")
        self.assertEqual(result, "600519.SH")

    def test_route_to_vendor_uses_market_specific_vendor_for_hk_fundamentals(self):
        with patch.dict(VENDOR_METHODS["get_fundamentals"], {"akshare": lambda ticker, *_args, **_kwargs: ticker}, clear=False):
            result = route_to_vendor("get_fundamentals", "00700.HK", "2026-04-09")
        self.assertEqual(result, "00700")

    def test_global_news_uses_runtime_context_market(self):
        set_runtime_context(ticker="AAPL")
        with patch.dict(VENDOR_METHODS["get_global_news"], {"finnhub": lambda *_args, **_kwargs: "finnhub-global"}, clear=False):
            result = route_to_vendor("get_global_news", "2026-04-09", 7, 5)
        self.assertEqual(result, "finnhub-global")

    def test_route_returns_message_when_market_tool_has_no_best_vendor(self):
        result = route_to_vendor("get_insider_transactions", "600519")
        self.assertIn("No best vendor is configured", result)

    @patch("tradingagents.dataflows.interface.emit_trace_event")
    def test_route_emits_trace_for_market_specific_vendor(self, emit_trace_event):
        with patch.dict(
            VENDOR_METHODS["get_stock_data"],
            {"tushare": lambda symbol, *_args, **_kwargs: symbol},
            clear=False,
        ):
            result = route_to_vendor("get_stock_data", "600519", "2026-01-01", "2026-02-01")

        self.assertEqual(result, "600519.SH")
        decision_call = next(call for call in emit_trace_event.call_args_list if call.args[1] == "route.decision")
        self.assertEqual(decision_call.kwargs["routing_mode"], "market_tool_vendors")
        self.assertEqual(decision_call.kwargs["market"], "a_share")
        self.assertEqual(decision_call.kwargs["vendor_chain"], ["tushare"])

        result_call = next(call for call in emit_trace_event.call_args_list if call.args[1] == "route.result")
        self.assertEqual(result_call.kwargs["outcome"], "success")
        self.assertEqual(result_call.kwargs["chosen_vendor"], "tushare")
        self.assertEqual(result_call.kwargs["normalized_symbol"], "600519.SH")

    @patch("tradingagents.dataflows.interface.emit_trace_event")
    def test_route_emits_blocked_trace_when_market_tool_has_no_best_vendor(self, emit_trace_event):
        result = route_to_vendor("get_insider_transactions", "600519")

        self.assertIn("No best vendor is configured", result)
        blocked_call = emit_trace_event.call_args_list[0]
        self.assertEqual(blocked_call.args[1], "route.blocked")
        self.assertEqual(blocked_call.kwargs["outcome"], "blocked")
        self.assertEqual(blocked_call.kwargs["reason"], "no_best_vendor")
        self.assertEqual(blocked_call.kwargs["market"], "a_share")

    @patch("tradingagents.dataflows.interface.emit_trace_event")
    def test_route_emits_category_fallback_trace_when_market_routing_disabled(self, emit_trace_event):
        set_config({"market_routing_enabled": False})

        with patch.dict(
            VENDOR_METHODS["get_stock_data"],
            {"yfinance": lambda symbol, *_args, **_kwargs: symbol},
            clear=False,
        ):
            result = route_to_vendor("get_stock_data", "AAPL", "2026-01-01", "2026-02-01")

        self.assertEqual(result, "AAPL")
        decision_call = next(call for call in emit_trace_event.call_args_list if call.args[1] == "route.decision")
        self.assertEqual(decision_call.kwargs["routing_mode"], "category_fallback")
        self.assertIsNone(decision_call.kwargs["market"])
        self.assertIn("yfinance", decision_call.kwargs["vendor_chain"])

    @patch("tradingagents.dataflows.interface.emit_trace_event")
    def test_route_marks_returned_error_string_as_error_outcome(self, emit_trace_event):
        with patch.dict(
            VENDOR_METHODS["get_stock_data"],
            {"tushare": lambda *_args, **_kwargs: "Error retrieving stock data for 600519 via tushare: boom"},
            clear=False,
        ):
            result = route_to_vendor("get_stock_data", "600519", "2026-01-01", "2026-02-01")

        self.assertIn("Error retrieving stock data", result)
        result_call = next(call for call in emit_trace_event.call_args_list if call.args[1] == "route.result")
        self.assertEqual(result_call.kwargs["outcome"], "error_string")
        self.assertEqual(result_call.kwargs["error_code"], "vendor_returned_error")
        self.assertIn("boom", result_call.kwargs["error_message"])


if __name__ == "__main__":
    unittest.main()
