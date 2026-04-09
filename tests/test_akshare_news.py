from __future__ import annotations

import unittest
from unittest import mock

import pandas as pd

from tradingagents.dataflows.akshare_news import get_news
from tradingagents.dataflows.akshare_news_utils import (
    CompanyNameContext,
    NewsQueryVariant,
    build_news_query_variants,
    merge_dedupe_rank_news,
    prepare_news_result_frame,
    resolve_company_name_context,
)
from tradingagents.dataflows.interface import VENDOR_METHODS, route_to_vendor


class AkshareNewsTests(unittest.TestCase):
    def test_build_news_query_variants_prioritizes_cn_hk_name_and_ticker_forms(self):
        cn_variants = build_news_query_variants(
            "688679",
            "a_share",
            CompanyNameContext(
                company_name_local="通源环境",
                company_name_en="Tongyuan Environment",
                aliases=("安徽通源环境",),
            ),
        )
        hk_variants = build_news_query_variants(
            "0700.HK",
            "hk",
            CompanyNameContext(
                company_name_local="腾讯控股",
                company_name_en="Tencent Holdings",
                aliases=("腾讯", "Tencent"),
            ),
        )

        self.assertEqual(
            [item.value for item in cn_variants[:5]],
            ["通源环境", "安徽通源环境", "688679.SH", "SH.688679", "688679"],
        )
        self.assertEqual(
            [item.value for item in hk_variants[:6]],
            ["腾讯控股", "Tencent Holdings", "00700.HK", "00700", "0700.HK", "700"],
        )

    def test_resolve_company_name_context_prefers_tushare_basic_fields(self):
        fake_pro = mock.Mock()
        fake_pro.stock_basic.return_value = pd.DataFrame(
            [
                {
                    "name": "通源环境",
                    "fullname": "安徽通源环境股份有限公司",
                    "enname": "Tongyuan Environment",
                }
            ]
        )

        with mock.patch(
            "tradingagents.dataflows.akshare_news_utils.get_tushare_pro", return_value=fake_pro
        ):
            context = resolve_company_name_context("688679", "a_share")

        self.assertEqual(context.company_name_local, "通源环境")
        self.assertEqual(context.company_name_en, "Tongyuan Environment")
        self.assertIn("安徽通源环境股份有限公司", context.aliases)

    def test_merge_dedupe_rank_news_keeps_best_scored_hit(self):
        variant_name = NewsQueryVariant(role="company_name_local", value="通源环境", priority=130)
        variant_code = NewsQueryVariant(role="ticker_code", value="688679", priority=95)
        common_row = {
            "关键词": "通源环境",
            "新闻标题": "通源环境中标新项目",
            "新闻内容": "通源环境公告披露新项目进展。",
            "发布时间": "2026-04-08 10:00:00",
            "文章来源": "证券时报网",
            "新闻链接": "http://example.com/news/1",
        }

        high_score = prepare_news_result_frame(
            pd.DataFrame([common_row]),
            variant=variant_name,
            start_date="2026-04-02",
            end_date="2026-04-09",
        )
        low_score = prepare_news_result_frame(
            pd.DataFrame([{**common_row, "关键词": "688679"}]),
            variant=variant_code,
            start_date="2026-04-02",
            end_date="2026-04-09",
        )

        merged = merge_dedupe_rank_news([low_score, high_score])

        self.assertEqual(len(merged), 1)
        self.assertEqual(merged.iloc[0]["匹配关键词"], "通源环境, 688679")
        self.assertEqual(merged.iloc[0]["关键词"], "通源环境")

    def test_get_news_queries_multiple_variants_and_dedupes_results(self):
        query_calls: list[str] = []
        fake_ak = mock.Mock()
        fake_ak.stock_news_main_cx.return_value = pd.DataFrame()

        def fake_fetch(symbol: str) -> pd.DataFrame:
            query_calls.append(symbol)
            if symbol == "通源环境":
                return pd.DataFrame(
                    [
                        {
                            "关键词": symbol,
                            "新闻标题": "通源环境签署环保项目",
                            "新闻内容": "通源环境发布项目签约公告。",
                            "发布时间": "2026-04-08 11:00:00",
                            "文章来源": "证券时报网",
                            "新闻链接": "http://example.com/cn/1",
                        }
                    ]
                )
            if symbol == "688679.SH":
                return pd.DataFrame(
                    [
                        {
                            "关键词": symbol,
                            "新闻标题": "通源环境签署环保项目",
                            "新闻内容": "688679.SH 对应公司通源环境发布项目签约公告。",
                            "发布时间": "2026-04-08 11:00:00",
                            "文章来源": "证券时报网",
                            "新闻链接": "http://example.com/cn/1",
                        }
                    ]
                )
            return pd.DataFrame()

        with (
            mock.patch(
                "tradingagents.dataflows.akshare_news.get_akshare_module", return_value=fake_ak
            ),
            mock.patch(
                "tradingagents.dataflows.akshare_news.fetch_stock_news_em", side_effect=fake_fetch
            ),
            mock.patch(
                "tradingagents.dataflows.akshare_news.resolve_company_name_context",
                return_value=CompanyNameContext(
                    company_name_local="通源环境",
                    company_name_en="Tongyuan Environment",
                    aliases=("安徽通源环境",),
                ),
            ),
        ):
            result = get_news("688679", "2026-04-02", "2026-04-09")

        self.assertIn("通源环境签署环保项目", result)
        self.assertIn("# Fallback used: False", result)
        self.assertIn("# Successful variants:", result)
        self.assertIn("匹配关键词", result)
        self.assertIn("通源环境", query_calls)
        self.assertIn("688679.SH", query_calls)

    def test_get_news_uses_main_cx_only_when_all_variants_empty(self):
        fake_ak = mock.Mock()
        fake_ak.stock_news_main_cx.return_value = pd.DataFrame(
            [
                {
                    "关键词": "fallback",
                    "新闻标题": "腾讯控股回购股份",
                    "新闻内容": "腾讯控股在港交所公告回购股份。",
                    "发布时间": "2026-04-08 23:02:00",
                    "文章来源": "证券时报网",
                    "新闻链接": "http://example.com/hk/1",
                }
            ]
        )

        with (
            mock.patch(
                "tradingagents.dataflows.akshare_news.get_akshare_module", return_value=fake_ak
            ),
            mock.patch(
                "tradingagents.dataflows.akshare_news.fetch_stock_news_em",
                return_value=pd.DataFrame(),
            ),
            mock.patch(
                "tradingagents.dataflows.akshare_news.resolve_company_name_context",
                return_value=CompanyNameContext(
                    company_name_local="腾讯控股", company_name_en="Tencent Holdings"
                ),
            ),
            mock.patch(
                "tradingagents.dataflows.akshare_news.run_without_proxy",
                side_effect=lambda func: func(),
            ),
        ):
            result = get_news("0700.HK", "2026-04-02", "2026-04-09")

        self.assertIn("腾讯控股回购股份", result)
        self.assertIn("# Fallback used: True", result)
        fake_ak.stock_news_main_cx.assert_called_once()

    def test_route_to_vendor_prefers_akshare_for_cn_hk_get_news(self):
        observed_calls: list[tuple[str, str, str]] = []

        def fake_akshare_news(ticker: str, start_date: str, end_date: str) -> str:
            observed_calls.append((ticker, start_date, end_date))
            return "ok"

        config = {
            "market_routing_enabled": True,
            "market_tool_vendors": {
                "a_share": {"get_news": "akshare"},
                "hk": {"get_news": "akshare"},
                "us": {"get_news": "finnhub"},
            },
            "data_vendors": {"news_data": "tushare"},
            "tool_vendors": {},
        }

        original_akshare = VENDOR_METHODS["get_news"]["akshare"]
        try:
            VENDOR_METHODS["get_news"]["akshare"] = fake_akshare_news
            with (
                mock.patch("tradingagents.dataflows.interface.get_config", return_value=config),
                mock.patch(
                    "tradingagents.dataflows.interface.get_runtime_context", return_value={}
                ),
                mock.patch("tradingagents.dataflows.interface._emit_route_event"),
            ):
                self.assertEqual(
                    route_to_vendor("get_news", "688679", "2026-04-02", "2026-04-09"), "ok"
                )
                self.assertEqual(
                    route_to_vendor("get_news", "0700.HK", "2026-04-02", "2026-04-09"), "ok"
                )
        finally:
            VENDOR_METHODS["get_news"]["akshare"] = original_akshare

        self.assertEqual(observed_calls[0][0], "688679")
        self.assertEqual(observed_calls[1][0], "00700")


if __name__ == "__main__":
    unittest.main()
