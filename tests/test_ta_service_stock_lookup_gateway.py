import unittest
from unittest.mock import patch

import pandas as pd

from ta_service.services.stock_lookup_gateway import StockLookupGateway
from tradingagents.dataflows.market_resolver import MARKET_A_SHARE, MARKET_HK, MARKET_US


class StockLookupGatewayTests(unittest.TestCase):
    @patch.object(StockLookupGateway, "_load_tushare_catalog")
    def test_search_candidates_ranks_exact_alias_and_maps_markets(self, mock_load_catalog):
        def fake_catalog(market: str):
            if market == MARKET_US:
                return pd.DataFrame(
                    [
                        {"ts_code": "AAPL", "name": "Apple Inc.", "enname": "Apple", "list_status": "L"},
                        {"ts_code": "APLE", "name": "Apple Hospitality REIT", "enname": "Apple Hospitality", "list_status": "L"},
                    ]
                )
            if market == MARKET_HK:
                return pd.DataFrame([])
            return pd.DataFrame([])

        mock_load_catalog.side_effect = fake_catalog
        gateway = StockLookupGateway()

        candidates = gateway.search_stock_candidates(query="Apple", market_hints=["US"], limit=5)

        self.assertEqual(candidates[0].ticker, "AAPL")
        self.assertEqual(candidates[0].market, "US")
        self.assertGreater((candidates[0].score or 0), (candidates[1].score or 0))

    @patch.object(StockLookupGateway, "_load_tushare_catalog")
    def test_get_stock_profile_normalizes_hk_ticker(self, mock_load_catalog):
        def fake_catalog(market: str):
            if market == MARKET_HK:
                return pd.DataFrame(
                    [
                        {"ts_code": "00700.HK", "name": "Tencent Holdings Limited", "list_status": "L"},
                    ]
                )
            return pd.DataFrame([])

        mock_load_catalog.side_effect = fake_catalog
        gateway = StockLookupGateway()

        profile = gateway.get_stock_profile(ticker="0700.HK")

        self.assertIsNotNone(profile)
        self.assertEqual(profile.ticker, "0700.HK")
        self.assertEqual(profile.market, "HK")

    @patch.object(StockLookupGateway, "_load_tushare_catalog")
    def test_get_stock_profile_maps_a_share_exchange(self, mock_load_catalog):
        def fake_catalog(market: str):
            if market == MARKET_A_SHARE:
                return pd.DataFrame(
                    [
                        {
                            "ts_code": "300750.SZ",
                            "name": "宁德时代新能源科技股份有限公司",
                            "exchange": "SZ",
                            "list_status": "L",
                        },
                    ]
                )
            return pd.DataFrame([])

        mock_load_catalog.side_effect = fake_catalog
        gateway = StockLookupGateway()

        profile = gateway.get_stock_profile(ticker="300750.SZ")

        self.assertIsNotNone(profile)
        self.assertEqual(profile.exchange, "SZSE")
        self.assertEqual(profile.market, "CN")

    @patch.object(StockLookupGateway, "_load_tushare_catalog")
    def test_get_stock_profile_supports_bj_ticker(self, mock_load_catalog):
        def fake_catalog(market: str):
            if market == MARKET_A_SHARE:
                return pd.DataFrame(
                    [
                        {
                            "ts_code": "920964.BJ",
                            "name": "某北交所公司",
                            "exchange": "BJ",
                            "list_status": "L",
                        },
                    ]
                )
            return pd.DataFrame([])

        mock_load_catalog.side_effect = fake_catalog
        gateway = StockLookupGateway()

        profile = gateway.get_stock_profile(ticker="920964.BJ")

        self.assertIsNotNone(profile)
        self.assertEqual(profile.ticker, "920964.BJ")
        self.assertEqual(profile.exchange, "BSE")
        self.assertEqual(profile.market, "CN")


if __name__ == "__main__":
    unittest.main()
