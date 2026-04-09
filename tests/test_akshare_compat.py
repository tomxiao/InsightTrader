from __future__ import annotations

import unittest
from unittest import mock

import pandas as pd

from tradingagents.dataflows.akshare_common import fetch_stock_news_em


class AkshareCompatTests(unittest.TestCase):
    def test_fetch_stock_news_em_returns_official_result_when_available(self):
        fake_ak = mock.Mock()
        fake_ak.stock_news_em.return_value = pd.DataFrame([{"新闻标题": "官方返回"}])

        with mock.patch("tradingagents.dataflows.akshare_common.get_akshare_module", return_value=fake_ak):
            result = fetch_stock_news_em("603777")

        self.assertEqual(len(result), 1)
        self.assertEqual(result.iloc[0]["新闻标题"], "官方返回")

    def test_fetch_stock_news_em_falls_back_on_arrow_regex_error(self):
        fake_ak = mock.Mock()
        fake_ak.stock_news_em.side_effect = Exception(
            "ArrowInvalid: Invalid regular expression: invalid escape sequence: \\u"
        )
        compat_df = pd.DataFrame([{"新闻标题": "兼容路径返回"}])

        with (
            mock.patch("tradingagents.dataflows.akshare_common.get_akshare_module", return_value=fake_ak),
            mock.patch(
                "tradingagents.dataflows.akshare_common._fetch_stock_news_em_compat",
                return_value=compat_df,
            ) as compat_mock,
        ):
            result = fetch_stock_news_em("603777")

        compat_mock.assert_called_once_with("603777")
        self.assertEqual(len(result), 1)
        self.assertEqual(result.iloc[0]["新闻标题"], "兼容路径返回")


if __name__ == "__main__":
    unittest.main()
