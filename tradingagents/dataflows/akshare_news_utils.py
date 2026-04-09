from __future__ import annotations

import re
from dataclasses import dataclass

import pandas as pd

from .akshare_common import get_akshare_module, run_without_proxy
from .market_resolver import (
    MARKET_A_SHARE,
    MARKET_HK,
    detect_market,
    extract_a_share_code,
    extract_hk_code,
    infer_a_share_exchange,
    normalize_symbol_for_vendor,
)
from .tushare_common import get_tushare_pro


@dataclass(frozen=True)
class CompanyNameContext:
    company_name_local: str | None = None
    company_name_en: str | None = None
    aliases: tuple[str, ...] = ()


@dataclass(frozen=True)
class NewsQueryVariant:
    role: str
    value: str
    priority: int


def resolve_company_name_context(ticker: str, market: str | None = None) -> CompanyNameContext:
    market = market or detect_market(ticker)
    local_name = ""
    english_name = ""
    aliases: list[str] = []

    try:
        pro = get_tushare_pro()
        symbol = normalize_symbol_for_vendor(ticker, "tushare", market)
        if market == MARKET_A_SHARE:
            dataframe = pro.stock_basic(ts_code=symbol)
        elif market == MARKET_HK:
            dataframe = pro.hk_basic(ts_code=symbol)
        else:
            dataframe = pd.DataFrame()

        if isinstance(dataframe, pd.DataFrame) and not dataframe.empty:
            row = dataframe.iloc[0].to_dict()
            local_name = _first_non_empty(row, ("name", "fullname", "short_name", "cname"))
            english_name = _first_non_empty(
                row, ("enname", "english_name", "eng_name", "fullname_en")
            )
            aliases.extend(_collect_aliases(row, local_name, english_name))
    except Exception:
        pass

    if market == MARKET_HK and not local_name:
        local_name, english_name, fallback_aliases = _resolve_hk_names_via_akshare(ticker)
        aliases.extend(fallback_aliases)

    deduped_aliases = _dedupe_texts(aliases, exclude=[local_name, english_name])
    return CompanyNameContext(
        company_name_local=local_name or None,
        company_name_en=english_name or None,
        aliases=tuple(deduped_aliases),
    )


def build_news_query_variants(
    ticker: str,
    market: str | None = None,
    name_context: CompanyNameContext | None = None,
) -> list[NewsQueryVariant]:
    market = market or detect_market(ticker)
    name_context = name_context or CompanyNameContext()
    items: list[NewsQueryVariant] = []
    seen: set[str] = set()

    def add(role: str, value: str | None, priority: int) -> None:
        text = (value or "").strip()
        if not text:
            return
        key = text.casefold()
        if key in seen:
            return
        seen.add(key)
        items.append(NewsQueryVariant(role=role, value=text, priority=priority))

    if market == MARKET_A_SHARE:
        code = extract_a_share_code(ticker)
        exchange = infer_a_share_exchange(code)
        add("company_name_local", name_context.company_name_local, 130)
        for alias in name_context.aliases:
            add("alias", alias, 120)
        add("ticker_symbol", f"{code}.{exchange}", 110)
        add("ticker_exchange_prefix", f"{exchange}.{code}", 105)
        add("ticker", ticker, 100)
        add("ticker_code", code, 95)
        add("company_name_en", name_context.company_name_en, 60)
        return items

    if market == MARKET_HK:
        code = extract_hk_code(ticker)
        compact = code.lstrip("0") or "0"
        add("company_name_local", name_context.company_name_local, 135)
        add("company_name_en", name_context.company_name_en, 130)
        add("ticker_symbol", f"{code}.HK", 120)
        add("ticker_numeric_padded", code, 115)
        add("ticker", ticker, 110)
        add("ticker_numeric_compact", compact, 100)
        for alias in name_context.aliases:
            add("alias", alias, 95)
        return items

    add("ticker", ticker, 100)
    return items


def build_akshare_symbol_candidates(market: str, keyword: str) -> list[str]:
    text = keyword.strip()
    if not text:
        return []

    candidates: list[str] = []
    seen: set[str] = set()

    def add(candidate: str | None) -> None:
        if candidate is None:
            return
        value = candidate.strip()
        if not value:
            return
        key = value.casefold()
        if key in seen:
            return
        seen.add(key)
        candidates.append(value)

    add(text)
    add(text.upper())

    if market == MARKET_A_SHARE:
        try:
            code = extract_a_share_code(text)
            exchange = infer_a_share_exchange(code)
            add(f"{code}.{exchange}")
            add(f"{exchange}.{code}")
            add(code)
        except Exception:
            pass
        return candidates

    if market == MARKET_HK:
        try:
            code = extract_hk_code(text)
            compact = code.lstrip("0") or "0"
            add(f"{code}.HK")
            add(f"{compact}.HK")
            add(code)
            add(compact)
        except Exception:
            pass
        return candidates

    return candidates


def filter_news_by_date(dataframe: pd.DataFrame, start_date: str, end_date: str) -> pd.DataFrame:
    dataframe = _coerce_dataframe(dataframe)
    if dataframe.empty:
        return dataframe

    start = pd.to_datetime(start_date)
    end = pd.to_datetime(end_date) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)
    for column in ("发布时间", "pubDate", "datetime", "date", "time", "displayTime"):
        if column not in dataframe.columns:
            continue
        parsed = pd.to_datetime(dataframe[column], errors="coerce")
        if parsed.notna().any():
            mask = parsed.between(start, end, inclusive="both")
            return dataframe[mask].reset_index(drop=True)
    return dataframe


def filter_news_by_keyword(dataframe: pd.DataFrame, keyword: str) -> pd.DataFrame:
    dataframe = _coerce_dataframe(dataframe)
    if dataframe.empty:
        return dataframe
    pattern, use_regex = build_keyword_matcher(keyword)
    filters = []
    for column in dataframe.columns:
        series = dataframe[column].astype(str)
        filters.append(series.str.contains(pattern, case=False, na=False, regex=use_regex))
    if not filters:
        return pd.DataFrame(columns=dataframe.columns)
    mask = filters[0]
    for item in filters[1:]:
        mask = mask | item
    return dataframe[mask].reset_index(drop=True)


def build_keyword_matcher(keyword: str) -> tuple[str, bool]:
    text = keyword.strip()
    if not text:
        return "", False

    if re.fullmatch(r"\d+", text):
        return rf"(?<!\d){re.escape(text)}(?!\d)", True

    upper = text.upper()
    if re.fullmatch(r"\d+\.(?:HK|SH|SZ)", upper) or re.fullmatch(r"(?:HK|SH|SZ)\.\d+", upper):
        return rf"(?<![A-Z0-9]){re.escape(text)}(?![A-Z0-9])", True

    return text, False


def prepare_news_result_frame(
    dataframe: pd.DataFrame,
    *,
    variant: NewsQueryVariant,
    start_date: str,
    end_date: str,
    source: str = "stock_news_em",
) -> pd.DataFrame:
    filtered = filter_news_by_date(dataframe, start_date, end_date).copy()
    if filtered.empty:
        return filtered
    filtered["query_value"] = variant.value
    filtered["query_role"] = variant.role
    filtered["query_priority"] = variant.priority
    filtered["query_source"] = source
    filtered["match_score"] = filtered.apply(
        lambda row: score_news_row(row, variant=variant, source=source),
        axis=1,
    )
    return filtered


def merge_dedupe_rank_news(frames: list[pd.DataFrame]) -> pd.DataFrame:
    valid_frames = [
        frame.copy() for frame in frames if isinstance(frame, pd.DataFrame) and not frame.empty
    ]
    if not valid_frames:
        return pd.DataFrame()

    combined = pd.concat(valid_frames, ignore_index=True, sort=False)
    combined["发布时间_dt"] = pd.to_datetime(combined.get("发布时间"), errors="coerce")
    combined["dedupe_key"] = combined.apply(_build_dedupe_key, axis=1)
    combined["query_value"] = (
        combined.get("query_value", pd.Series(dtype=str)).fillna("").astype(str)
    )
    combined["query_role"] = combined.get("query_role", pd.Series(dtype=str)).fillna("").astype(str)
    combined["match_score"] = pd.to_numeric(combined.get("match_score"), errors="coerce").fillna(0)

    combined = combined.sort_values(
        by=["match_score", "发布时间_dt"],
        ascending=[False, False],
        na_position="last",
    ).reset_index(drop=True)

    matched_queries = combined.groupby("dedupe_key")["query_value"].apply(_join_unique_values)
    matched_roles = combined.groupby("dedupe_key")["query_role"].apply(_join_unique_values)
    query_counts = combined.groupby("dedupe_key")["query_value"].apply(
        lambda series: len([item for item in series if item])
    )

    best = combined.drop_duplicates(subset=["dedupe_key"], keep="first").copy()
    best["匹配关键词"] = best["dedupe_key"].map(matched_queries)
    best["匹配角色"] = best["dedupe_key"].map(matched_roles)
    best["匹配次数"] = best["dedupe_key"].map(query_counts)
    best["匹配分数"] = best["match_score"].astype(int)

    output_columns = [
        column
        for column in [
            "关键词",
            "新闻标题",
            "新闻内容",
            "发布时间",
            "文章来源",
            "新闻链接",
            "匹配关键词",
            "匹配角色",
            "匹配次数",
            "匹配分数",
        ]
        if column in best.columns
    ]
    return best[output_columns].reset_index(drop=True)


def score_news_row(
    row: pd.Series, *, variant: NewsQueryVariant, source: str = "stock_news_em"
) -> int:
    title = str(row.get("新闻标题", ""))
    content = str(row.get("新闻内容", ""))
    keyword = variant.value
    score = variant.priority

    if keyword and keyword.lower() in title.lower():
        score += 40
    if keyword and keyword.lower() in content.lower():
        score += 20

    title_lower = title.lower()
    if any(token in title_lower for token in ("一览", "余额", "追踪", "统计", "变动")):
        score -= 15
    if source != "stock_news_em":
        score -= 25
    return score


def _resolve_hk_names_via_akshare(ticker: str) -> tuple[str, str, list[str]]:
    try:
        ak = get_akshare_module()
        symbol = normalize_symbol_for_vendor(ticker, "akshare", MARKET_HK)
        dataframe = run_without_proxy(lambda: ak.stock_hk_company_profile_em(symbol=symbol))
    except Exception:
        return "", "", []

    if not isinstance(dataframe, pd.DataFrame) or dataframe.empty:
        return "", "", []

    local_name = ""
    english_name = ""
    aliases: list[str] = []

    if {"item", "value"}.issubset(dataframe.columns):
        item_map = {
            str(item).strip().casefold(): str(value).strip()
            for item, value in zip(dataframe["item"], dataframe["value"], strict=False)
            if pd.notna(item) and pd.notna(value)
        }
        local_name = _first_non_empty_map(item_map, ("公司名称", "中文名称", "名称"))
        english_name = _first_non_empty_map(item_map, ("英文名称", "英文名", "英文名稱"))
        aliases = _dedupe_texts(
            [
                _first_non_empty_map(item_map, ("简称", "簡稱")),
                _first_non_empty_map(item_map, ("全称", "全稱")),
            ],
            exclude=[local_name, english_name],
        )

    return local_name, english_name, aliases


def _collect_aliases(row: dict[str, object], local_name: str, english_name: str) -> list[str]:
    aliases = [
        _safe_text(row.get("fullname")),
        _safe_text(row.get("name")),
        _safe_text(row.get("short_name")),
        _safe_text(row.get("cname")),
    ]
    return _dedupe_texts(aliases, exclude=[local_name, english_name])


def _first_non_empty(row: dict[str, object], keys: tuple[str, ...]) -> str:
    for key in keys:
        value = _safe_text(row.get(key))
        if value:
            return value
    return ""


def _first_non_empty_map(row: dict[str, str], keys: tuple[str, ...]) -> str:
    for key in keys:
        value = _safe_text(row.get(key.casefold()))
        if value:
            return value
    return ""


def _safe_text(value: object) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    if not text or text.lower() == "nan":
        return ""
    return text


def _dedupe_texts(values: list[str], *, exclude: list[str] | None = None) -> list[str]:
    excluded = {item.casefold() for item in (exclude or []) if item}
    items: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = _safe_text(value)
        if not text:
            continue
        key = text.casefold()
        if key in seen or key in excluded:
            continue
        seen.add(key)
        items.append(text)
    return items


def _coerce_dataframe(payload: object) -> pd.DataFrame:
    if isinstance(payload, pd.DataFrame):
        return payload
    return pd.DataFrame(payload)


def _build_dedupe_key(row: pd.Series) -> str:
    url = str(row.get("新闻链接", "")).strip()
    if url:
        return f"url:{url}"
    title = str(row.get("新闻标题", "")).strip()
    published_at = str(row.get("发布时间", "")).strip()
    source = str(row.get("文章来源", "")).strip()
    return f"meta:{title}|{published_at}|{source}"


def _join_unique_values(series: pd.Series) -> str:
    items: list[str] = []
    seen: set[str] = set()
    for value in series:
        text = str(value).strip()
        if not text:
            continue
        key = text.casefold()
        if key in seen:
            continue
        seen.add(key)
        items.append(text)
    return ", ".join(items)
