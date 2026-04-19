from __future__ import annotations

import pandas as pd

from backtest.generate_report_batch import (
    DEFAULT_BACKTEST_LLM_MODEL,
    _decision_path_exists,
    _sample_dates_from_ohlcv,
    build_parser,
)
from backtest.pathing import build_output_run_dir, build_report_dir_name


def test_sample_dates_from_ohlcv_weekly_uses_first_trading_day_per_week(monkeypatch) -> None:
    frame = pd.DataFrame(
        {
            "Date": pd.to_datetime(
                [
                    "2026-02-23",
                    "2026-02-24",
                    "2026-02-27",
                    "2026-03-02",
                    "2026-03-03",
                ]
            )
        }
    )

    def fake_fetch(_ticker: str, _start: str, _end: str):
        return frame, "us", "AXTI"

    monkeypatch.setattr(
        "backtest.generate_report_batch._fetch_tushare_ohlcv",
        fake_fetch,
    )

    sampled = _sample_dates_from_ohlcv("AXTI", "2026-02-23", "2026-03-03", mode="weekly", step=5)

    assert sampled == ["2026-02-23", "2026-03-02"]


def test_sample_dates_from_ohlcv_daily_uses_step(monkeypatch) -> None:
    frame = pd.DataFrame(
        {
            "Date": pd.to_datetime(
                [
                    "2026-02-23",
                    "2026-02-24",
                    "2026-02-25",
                    "2026-02-26",
                    "2026-02-27",
                ]
            )
        }
    )

    def fake_fetch(_ticker: str, _start: str, _end: str):
        return frame, "us", "AXTI"

    monkeypatch.setattr(
        "backtest.generate_report_batch._fetch_tushare_ohlcv",
        fake_fetch,
    )

    sampled = _sample_dates_from_ohlcv("AXTI", "2026-02-23", "2026-02-27", mode="daily", step=2)

    assert sampled == ["2026-02-23", "2026-02-25", "2026-02-27"]


def test_build_output_run_dir_uses_mmdd_hhmm_ticker() -> None:
    output_dir = build_output_run_dir(
        "backtest/output",
        "AXTI",
        now=pd.Timestamp("2026-04-19 22:34").to_pydatetime(),
    )

    assert output_dir.as_posix().endswith("backtest/output/0419-2234-AXTI")


def test_build_report_dir_name_uses_yyyy_mmdd_ticker() -> None:
    assert build_report_dir_name("2026-04-13", "AXTI") == "2026-0413-AXTI"


def test_decision_path_exists_checks_local_file(tmp_path) -> None:
    decision = tmp_path / "2_decision" / "summary.md"
    decision.parent.mkdir(parents=True)
    decision.write_text("ok", encoding="utf-8")

    assert _decision_path_exists({"decision_path": str(decision)}) is True
    assert _decision_path_exists({"decision_path": str(decision.parent / "missing.md")}) is False


def test_generate_report_batch_defaults_to_deepseek_reasoner() -> None:
    parser = build_parser()

    args = parser.parse_args(
        [
            "--ticker",
            "AXTI",
            "--start-date",
            "2026-03-02",
            "--end-date",
            "2026-04-07",
        ]
    )

    assert args.llm_model == DEFAULT_BACKTEST_LLM_MODEL
