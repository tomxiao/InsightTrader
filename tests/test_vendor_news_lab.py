import importlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import pandas as pd

from tradingagents.dataflows.formatting import format_dataframe_report

VALIDATION_ROOT = Path(__file__).resolve().parents[1] / "validation" / "vendor-news-lab"
if str(VALIDATION_ROOT) not in sys.path:
    sys.path.insert(0, str(VALIDATION_ROOT))

vendor_news_lab = importlib.import_module("vendor_news_lab")
vendor_news_lab_loader = importlib.import_module("vendor_news_lab.loader")
vendor_news_lab_runner = importlib.import_module("vendor_news_lab.runner")

MarketNewsCase = vendor_news_lab.MarketNewsCase
NewsValidationRunner = vendor_news_lab.NewsValidationRunner
VendorConfig = vendor_news_lab.VendorConfig
build_keyword_variants = vendor_news_lab.build_keyword_variants
load_news_cases = vendor_news_lab_loader.load_news_cases
load_vendor_configs = vendor_news_lab_loader.load_vendor_configs
UnsupportedValidationError = vendor_news_lab_runner.UnsupportedValidationError
_build_akshare_symbol_candidates = vendor_news_lab_runner._build_akshare_symbol_candidates
_build_keyword_matcher = vendor_news_lab_runner._build_keyword_matcher
_fetch_akshare_keyword_news = vendor_news_lab_runner._fetch_akshare_keyword_news


class VendorNewsLabTests(unittest.TestCase):
    def test_loaders_read_case_and_vendor_manifests(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            cases_path = root / "cases.json"
            vendors_path = root / "vendors.json"
            cases_path.write_text(
                json.dumps(
                    [
                        {
                            "case_id": "cn_case",
                            "market": "cn",
                            "ticker": "688679",
                            "label": "通源环境",
                            "analysis_date": "2026-04-09",
                            "start_date": "2026-04-02",
                            "end_date": "2026-04-09",
                            "aliases": ["通源", "通源"],
                            "candidate_keywords": [
                                {"role": "ticker_symbol", "value": "688679.SH"},
                                {"role": "ticker_symbol", "value": "688679.SH"},
                            ],
                        }
                    ],
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            vendors_path.write_text(
                json.dumps(
                    [
                        {
                            "vendor_key": "akshare",
                            "display_name": "AKShare",
                            "markets_supported": ["cn", "hk"],
                            "news_mode": "symbol_with_fallback",
                            "enabled": True,
                        }
                    ],
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            cases = load_news_cases(cases_path)
            vendors = load_vendor_configs(vendors_path)

            self.assertEqual(cases[0].aliases, ["通源"])
            self.assertEqual(
                cases[0].candidate_keywords,
                [{"role": "ticker_symbol", "value": "688679.SH", "source": "manifest"}],
            )
            self.assertEqual(vendors[0].vendor_key, "akshare")
            self.assertTrue(vendors[0].supports_market("cn"))

    def test_build_keyword_variants_covers_cn_hk_us_rules(self):
        cn_case = MarketNewsCase(
            case_id="cn_case",
            market="cn",
            ticker="688679",
            label="通源环境",
            analysis_date="2026-04-09",
            start_date="2026-04-02",
            end_date="2026-04-09",
            company_name_local="通源环境",
            aliases=["通源"],
        )
        hk_case = MarketNewsCase(
            case_id="hk_case",
            market="hk",
            ticker="0700.HK",
            label="腾讯控股",
            analysis_date="2026-04-09",
            start_date="2026-04-02",
            end_date="2026-04-09",
            company_name_local="腾讯控股",
            company_name_en="Tencent Holdings",
        )
        us_case = MarketNewsCase(
            case_id="us_case",
            market="us",
            ticker="AAPL",
            label="Apple Inc.",
            analysis_date="2026-04-09",
            start_date="2026-04-02",
            end_date="2026-04-09",
            company_name_en="Apple Inc.",
            aliases=["Apple"],
        )

        cn_values = {item.value for item in build_keyword_variants(cn_case)}
        hk_values = {item.value for item in build_keyword_variants(hk_case)}
        us_values = {item.value for item in build_keyword_variants(us_case)}

        self.assertIn("688679.SH", cn_values)
        self.assertIn("SH.688679", cn_values)
        self.assertIn("00700", hk_values)
        self.assertIn("700", hk_values)
        self.assertIn("US.AAPL", us_values)
        self.assertIn("Apple", us_values)

    def test_build_akshare_symbol_candidates_preserves_raw_and_exchange_forms(self):
        hk_candidates = _build_akshare_symbol_candidates("hk", "0700.HK")
        cn_candidates = _build_akshare_symbol_candidates("cn", "688679.SH")
        name_candidates = _build_akshare_symbol_candidates("hk", "腾讯控股")

        self.assertEqual(hk_candidates[:3], ["0700.HK", "00700.HK", "700.HK"])
        self.assertIn("00700", hk_candidates)
        self.assertEqual(cn_candidates[:3], ["688679.SH", "SH.688679", "688679"])
        self.assertEqual(name_candidates, ["腾讯控股"])

    def test_fetch_akshare_keyword_news_tries_raw_keyword_before_fallback(self):
        symbol_calls: list[str] = []
        case = MarketNewsCase(
            case_id="hk_case",
            market="hk",
            ticker="0700.HK",
            label="腾讯控股",
            analysis_date="2026-04-09",
            start_date="2026-04-02",
            end_date="2026-04-09",
            company_name_local="腾讯控股",
            company_name_en="Tencent Holdings",
        )

        with (
            mock.patch("vendor_news_lab.runner.get_akshare_module") as ak_mock,
            mock.patch(
                "vendor_news_lab.runner.fetch_stock_news_em",
                side_effect=lambda symbol: (
                    symbol_calls.append(symbol)
                    or pd.DataFrame(
                        [{"标题": "腾讯控股回购股份", "发布时间": "2026-04-03 10:00:00"}]
                    )
                ),
            ),
        ):
            ak_mock.return_value.stock_news_main_cx.side_effect = AssertionError(
                "fallback should not be used when raw keyword succeeds"
            )
            response = _fetch_akshare_keyword_news(
                case,
                build_keyword_variants(case)[4],
            )

        self.assertEqual(symbol_calls, ["腾讯控股"])
        self.assertIn("腾讯控股回购股份", response)
        self.assertIn("# Vendor symbol: 腾讯控股", response)

    def test_build_keyword_matcher_avoids_numeric_substring_false_positive(self):
        pattern, use_regex = _build_keyword_matcher("700")
        dataframe = pd.DataFrame(
            [
                {"summary": "全市场超4700只个股飘绿"},
                {"summary": "腾讯控股(700)继续回购"},
            ]
        )

        filtered = dataframe[
            dataframe["summary"].str.contains(pattern, case=False, na=False, regex=use_regex)
        ]

        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered.iloc[0]["summary"], "腾讯控股(700)继续回购")

    def test_runner_writes_outputs_and_preserves_keyword_hits(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output_root = Path(temp_dir) / "outputs"
            case = MarketNewsCase(
                case_id="us_apple",
                market="us",
                ticker="AAPL",
                label="Apple Inc.",
                analysis_date="2026-04-09",
                start_date="2026-04-02",
                end_date="2026-04-09",
                company_name_en="Apple Inc.",
                company_name_local="苹果公司",
                aliases=["Apple"],
            )
            finnhub = VendorConfig(
                vendor_key="finnhub",
                display_name="Finnhub",
                markets_supported=["us"],
                news_mode="symbol_native",
            )
            akshare = VendorConfig(
                vendor_key="akshare",
                display_name="AKShare",
                markets_supported=["cn", "hk"],
                news_mode="symbol_with_fallback",
            )

            def fake_vendor_fetcher(vendor, _case):
                if vendor.vendor_key == "finnhub":
                    return format_dataframe_report(
                        "Finnhub news",
                        pd.DataFrame(
                            [{"headline": "Apple launches new device", "date": "2026-04-03"}]
                        ),
                    )
                raise UnsupportedValidationError("unsupported vendor in fake test")

            def fake_keyword_fetcher(vendor, _case, variant):
                if vendor.vendor_key != "finnhub":
                    raise UnsupportedValidationError("keyword adapter unavailable")
                if variant.role.startswith("ticker"):
                    return format_dataframe_report(
                        "Finnhub keyword news",
                        pd.DataFrame(
                            [{"headline": f"match:{variant.value}", "date": "2026-04-03"}]
                        ),
                    )
                raise UnsupportedValidationError(
                    "Finnhub keyword expansion only supports symbol-equivalent inputs"
                )

            runner = NewsValidationRunner(
                output_root,
                vendor_news_fetcher=fake_vendor_fetcher,
                keyword_expansion_fetcher=fake_keyword_fetcher,
            )
            run_dir, results = runner.run(cases=[case], vendors=[finnhub, akshare])

            self.assertTrue((run_dir / "results.jsonl").exists())
            self.assertTrue((run_dir / "summary.csv").exists())
            self.assertTrue((run_dir / "summary.md").exists())
            self.assertTrue(any(item.outcome == "ok" for item in results))
            self.assertTrue(any(item.outcome == "unsupported" for item in results))
            self.assertTrue(
                any(
                    item.keyword_value == "AAPL"
                    for item in results
                    if item.mode == "keyword-expansion"
                )
            )

            records = [
                json.loads(line)
                for line in (run_dir / "results.jsonl").read_text(encoding="utf-8").splitlines()
            ]
            ok_record = next(item for item in records if item["outcome"] == "ok")
            self.assertIn("Apple launches new device", ok_record["response_text"])
            self.assertTrue(ok_record["snapshot_path"])

            snapshot_path = run_dir / ok_record["snapshot_path"]
            self.assertTrue(snapshot_path.exists())
            self.assertIn("Apple launches new device", snapshot_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
