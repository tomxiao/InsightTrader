from __future__ import annotations

import pandas as pd

from .akshare_common import fetch_stock_news_em, get_akshare_module, run_without_proxy
from .akshare_news_utils import (
    CompanyNameContext,
    build_akshare_symbol_candidates,
    build_news_query_variants,
    filter_news_by_date,
    filter_news_by_keyword,
    merge_dedupe_rank_news,
    prepare_news_result_frame,
    resolve_company_name_context,
)
from .formatting import format_dataframe_report, unsupported_response
from .market_resolver import MARKET_A_SHARE, MARKET_HK, detect_market, normalize_symbol_for_vendor


def get_news(ticker: str, start_date: str, end_date: str) -> str:
    ak = get_akshare_module()
    market = detect_market(ticker)
    symbol = normalize_symbol_for_vendor(ticker, "akshare", market)
    try:
        name_context = (
            resolve_company_name_context(ticker, market)
            if market in {MARKET_A_SHARE, MARKET_HK}
            else CompanyNameContext()
        )
        variants = build_news_query_variants(ticker, market, name_context)
        frames: list[pd.DataFrame] = []
        successful_variants: list[str] = []
        fallback_used = False

        for variant in variants:
            symbol_candidates = build_akshare_symbol_candidates(market, variant.value)
            query_succeeded = False
            for candidate in symbol_candidates:
                try:
                    dataframe = fetch_stock_news_em(candidate)
                except Exception:
                    continue

                prepared = prepare_news_result_frame(
                    dataframe,
                    variant=variant,
                    start_date=start_date,
                    end_date=end_date,
                    source="stock_news_em",
                )
                if prepared.empty:
                    continue

                frames.append(prepared)
                successful_variants.append(f"{variant.role}:{candidate}")
                query_succeeded = True
                break

            if not symbol_candidates and not query_succeeded:
                prepared = prepare_news_result_frame(
                    pd.DataFrame(),
                    variant=variant,
                    start_date=start_date,
                    end_date=end_date,
                    source="stock_news_em",
                )
                if not prepared.empty:
                    frames.append(prepared)

        if not frames:
            fallback_used = True
            fallback_frame = filter_news_by_date(
                run_without_proxy(lambda: ak.stock_news_main_cx()),
                start_date,
                end_date,
            )
            for variant in variants:
                filtered = filter_news_by_keyword(fallback_frame, variant.value)
                prepared = prepare_news_result_frame(
                    filtered,
                    variant=variant,
                    start_date=start_date,
                    end_date=end_date,
                    source="main_cx_filter",
                )
                if prepared.empty:
                    continue
                frames.append(prepared)
                successful_variants.append(f"{variant.role}:{variant.value}")

        dataframe = merge_dedupe_rank_news(frames)
        return format_dataframe_report(
            f"AKShare news for {ticker}",
            dataframe if isinstance(dataframe, pd.DataFrame) else pd.DataFrame(dataframe),
            {
                "Vendor": "akshare",
                "Market": market,
                "Vendor symbol": symbol,
                "Start date": start_date,
                "End date": end_date,
                "Query variants": ", ".join(f"{item.role}:{item.value}" for item in variants),
                "Successful variants": ", ".join(successful_variants)
                if successful_variants
                else None,
                "Fallback used": fallback_used,
            },
        )
    except Exception as exc:
        return f"Error retrieving news for {ticker} via akshare: {exc}"


def get_global_news(curr_date: str, look_back_days: int = 7, limit: int = 50) -> str:
    ak = get_akshare_module()
    try:
        dataframe = run_without_proxy(lambda: ak.news_cctv(date=curr_date.replace("-", "")))
        if isinstance(dataframe, pd.DataFrame) and not dataframe.empty:
            dataframe = dataframe.head(limit)
        return format_dataframe_report(
            "AKShare global news",
            dataframe if isinstance(dataframe, pd.DataFrame) else pd.DataFrame(dataframe),
            {
                "Vendor": "akshare",
                "Date": curr_date,
                "Look back days": look_back_days,
                "Limit": limit,
            },
        )
    except Exception as exc:
        return f"Error retrieving global news via akshare: {exc}"


def get_insider_transactions(ticker: str) -> str:
    market = detect_market(ticker)
    return unsupported_response(
        "akshare",
        "get_insider_transactions",
        market,
        "No validated insider transactions endpoint is wired.",
    )
