from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from pathlib import Path
from threading import Lock
from typing import Any

import pandas as pd

from ta_service.models.resolution import ResolutionCandidate
from tradingagents.dataflows.finnhub_common import get_finnhub_client
from tradingagents.dataflows.market_resolver import (
    MARKET_A_SHARE,
    MARKET_HK,
    MARKET_US,
    detect_market,
    normalize_symbol_for_vendor,
)
from tradingagents.dataflows.tushare_common import get_tushare_pro

logger = logging.getLogger(__name__)

_DATA_DIR = Path(__file__).resolve().parents[1] / "data"


def _load_cn_alias_map() -> dict[str, str]:
    """加载中文别名字典，返回 {别名.lower(): ticker} 的反向查找表。"""
    json_path = _DATA_DIR / "us_cn_aliases.json"
    if not json_path.exists():
        logger.warning("us_cn_aliases.json not found at %s", json_path)
        return {}
    with json_path.open(encoding="utf-8") as f:
        data: dict[str, list[str]] = json.load(f)
    reverse: dict[str, str] = {}
    for ticker, aliases in data.items():
        for alias in aliases:
            key = alias.strip().lower()
            if key:
                reverse[key] = ticker.upper()
    logger.debug("cn_alias_map_loaded entries=%s", len(reverse))
    return reverse


_CN_ALIAS_MAP: dict[str, str] = _load_cn_alias_map()

_FIELDS_BY_MARKET = {
    MARKET_A_SHARE: "ts_code,symbol,name,fullname,enname,cnspell,exchange,list_status",
    MARKET_HK: "ts_code,name,enname,list_status",
    MARKET_US: "ts_code,name,enname,list_status",
}


class StockLookupError(RuntimeError):
    pass


@dataclass(frozen=True)
class _CatalogEntry:
    ticker: str
    name: str
    market: str
    exchange: str | None
    aliases: tuple[str, ...]
    is_active: bool


class StockLookupGateway:
    def __init__(self):
        self._catalog_cache: dict[str, list[_CatalogEntry]] = {}
        self._cache_lock = Lock()

    def search_stock_candidates(
        self,
        *,
        query: str,
        market_hints: list[str] | None = None,
        limit: int = 5,
    ) -> list[ResolutionCandidate]:
        # 剥离 .US / .us 后缀（兜底防御，正常由 LLM 在传参前清理）
        m_us = re.fullmatch(r"([A-Za-z]{1,5})\.[Uu][Ss]", query.strip())
        if m_us:
            query = m_us.group(1).upper()

        normalized_query = query.strip().lower()
        logger.info("stock_search_start query=%r market_hints=%s", query, market_hints)
        if not normalized_query:
            return []

        # 前置拦截：中文别名直接映射到 ticker，跳过全量 catalog 扫描
        cn_ticker = _CN_ALIAS_MAP.get(normalized_query)
        if cn_ticker:
            profile = self.get_stock_profile(ticker=cn_ticker)
            if profile is not None:
                logger.info("cn_alias_hit query=%s ticker=%s", query, cn_ticker)
                return [profile.model_copy(update={"score": 1.0})]

        exact_ticker = self.get_stock_profile(ticker=query)
        if exact_ticker is not None:
            logger.info("stock_search_exact_hit query=%r ticker=%s", query, exact_ticker.ticker)
            return [exact_ticker.model_copy(update={"score": 1.0})]

        ticker_hint = _normalize_ticker_hint(query)
        markets = _resolve_markets(query=query, market_hints=market_hints)
        logger.info(
            "stock_search_catalog query=%r ticker_hint=%r markets=%s",
            query,
            ticker_hint,
            markets,
        )
        scored: list[tuple[float, ResolutionCandidate]] = []
        errors: list[str] = []

        for market in markets:
            try:
                catalog = self._load_market_catalog(market)
            except Exception as exc:  # pragma: no cover - depends on vendor runtime
                logger.warning("stock_search_catalog_load_failed market=%s error=%s", market, exc)
                errors.append(str(exc))
                continue

            for item in catalog:
                score = _score_candidate(item, normalized_query, ticker_hint)
                if score <= 0:
                    continue
                scored.append(
                    (
                        score,
                        ResolutionCandidate(
                            ticker=item.ticker,
                            name=item.name,
                            market=_to_public_market(item.market),
                            exchange=item.exchange,
                            aliases=list(item.aliases),
                            score=score,
                            isActive=item.is_active,
                        ),
                    )
                )

        if not scored and errors:
            raise StockLookupError(errors[0])

        deduped: dict[str, ResolutionCandidate] = {}
        for score, candidate in scored:
            existing = deduped.get(candidate.ticker)
            if existing is None or (existing.score or 0) < score:
                deduped[candidate.ticker] = candidate

        ranked = sorted(
            deduped.values(), key=lambda candidate: (-(candidate.score or 0), candidate.ticker)
        )
        result = ranked[:limit]
        logger.info(
            "stock_search_done query=%r result_count=%s top=%s",
            query,
            len(result),
            [(r.ticker, r.score) for r in result[:3]],
        )
        return result

    def get_stock_profile(self, *, ticker: str) -> ResolutionCandidate | None:
        normalized = _normalize_ticker_hint(ticker)
        if not normalized:
            return None

        market = detect_market(normalized)
        try:
            catalog = self._load_market_catalog(market)
        except Exception as exc:  # pragma: no cover - depends on vendor runtime
            raise StockLookupError(str(exc)) from exc

        expected = _canonical_ticker(normalized, market).upper()
        for item in catalog:
            if item.ticker.upper() == expected:
                return ResolutionCandidate(
                    ticker=item.ticker,
                    name=item.name,
                    market=_to_public_market(item.market),
                    exchange=item.exchange,
                    aliases=list(item.aliases),
                    score=1.0,
                    isActive=item.is_active,
                )
        return None

    def _load_market_catalog(self, market: str) -> list[_CatalogEntry]:
        with self._cache_lock:
            if market in self._catalog_cache:
                return self._catalog_cache[market]

        if market == MARKET_US:
            entries = self._load_finnhub_us_catalog()
        else:
            dataframe = self._load_tushare_catalog(market)
            entries = [_row_to_candidate(row, market) for _, row in dataframe.iterrows()]
            entries = [entry for entry in entries if entry is not None]

        with self._cache_lock:
            self._catalog_cache[market] = entries
        return entries

    def _load_finnhub_us_catalog(self) -> list[_CatalogEntry]:
        """加载美股目录（约 3 万条 ticker）。

        优先从 ta_service/data/finnhub_us_basic.csv 读取本地缓存，
        文件不存在时回退到 Finnhub API 在线拉取。
        """
        local_csv = _DATA_DIR / "finnhub_us_basic.csv"
        if local_csv.exists():
            logger.info("finnhub_us_catalog_loading_from_csv path=%s", local_csv)
            df = pd.read_csv(local_csv, dtype=str, keep_default_na=False)
            symbols: list[dict] = df.to_dict(orient="records")
        else:
            logger.info("finnhub_us_catalog_loading_from_api")
            client = get_finnhub_client()
            symbols = client.stock_symbols("US")

        entries: list[_CatalogEntry] = []
        _allowed_types = {"Common Stock", "ETP", "DR", "Preferred Stock", "REIT", ""}
        for item in symbols:
            ticker = str(item.get("symbol") or "").strip().upper()
            name = str(item.get("description") or "").strip()
            if not ticker or not name:
                continue
            asset_type = str(item.get("type") or "").strip()
            if asset_type and asset_type not in _allowed_types:
                continue
            display = str(item.get("displaySymbol") or "").strip().upper()
            aliases: tuple[str, ...] = (display,) if display and display != ticker else ()
            entries.append(
                _CatalogEntry(
                    ticker=ticker,
                    name=name,
                    market=MARKET_US,
                    exchange=item.get("mic") or None,
                    aliases=aliases,
                    is_active=True,
                )
            )
        logger.info(
            "finnhub_us_catalog_loaded source=%s count=%s",
            "csv" if local_csv.exists() else "api",
            len(entries),
        )
        return entries

    def _load_tushare_catalog(self, market: str) -> pd.DataFrame:
        pro = get_tushare_pro()
        method_name = {
            MARKET_A_SHARE: "stock_basic",
            MARKET_HK: "hk_basic",
            MARKET_US: "us_basic",
        }[market]
        method = getattr(pro, method_name)
        fields = _FIELDS_BY_MARKET[market]

        attempts: list[dict[str, Any]] = [
            {"fields": fields},
            {"list_status": "L", "fields": fields},
            {"list_status": "L"},
            {},
        ]
        errors: list[str] = []
        for kwargs in attempts:
            try:
                dataframe = method(**kwargs)
                if dataframe is None:
                    continue
                if "fields" in kwargs:
                    return dataframe
                return _select_supported_columns(dataframe, fields)
            except TypeError as exc:
                errors.append(str(exc))
                continue
            except Exception:
                raise

        raise StockLookupError(
            f"Unable to load {market} stock catalog from tushare: {'; '.join(errors) or 'no successful attempts'}"
        )


def _normalize_ticker_hint(value: str) -> str:
    candidate = value.strip().upper()
    if re.fullmatch(r"[A-Z]{1,5}", candidate):
        return candidate
    # 支持 MU.US / MU.us 格式，剥离 .US 后缀
    m = re.fullmatch(r"([A-Z]{1,5})\.US", candidate)
    if m:
        return m.group(1)
    if re.fullmatch(r"\d{4,5}\.HK", candidate):
        return candidate
    if re.fullmatch(r"\d{6}\.(SZ|SH|BJ)", candidate):
        return candidate
    return ""


def _resolve_markets(*, query: str, market_hints: list[str] | None) -> list[str]:
    if market_hints:
        markets = [_to_internal_market(item) for item in market_hints if _to_internal_market(item)]
        if markets:
            return list(dict.fromkeys(markets))

    ticker_hint = _normalize_ticker_hint(query)
    if ticker_hint:
        return [detect_market(ticker_hint)]
    return [MARKET_US, MARKET_HK, MARKET_A_SHARE]


def _to_internal_market(value: str) -> str | None:
    upper = value.strip().upper()
    if upper in {"CN", "A", "A_SHARE"}:
        return MARKET_A_SHARE
    if upper == "HK":
        return MARKET_HK
    if upper == "US":
        return MARKET_US
    return None


def _to_public_market(value: str) -> str:
    if value == MARKET_A_SHARE:
        return "CN"
    if value == MARKET_HK:
        return "HK"
    return "US"


def _score_candidate(item: _CatalogEntry, normalized_query: str, ticker_hint: str) -> float:
    ticker = item.ticker.upper()
    if ticker_hint and ticker == ticker_hint:
        return 1.0

    if normalized_query == item.name.lower():
        return 0.98

    alias_scores = [0.97 for alias in item.aliases if normalized_query == alias.lower()]
    if alias_scores:
        return max(alias_scores)

    if normalized_query in item.name.lower():
        return 0.88

    for alias in item.aliases:
        alias_lower = alias.lower()
        if normalized_query in alias_lower or alias_lower in normalized_query:
            return 0.86

    if ticker.startswith(normalized_query.upper()) and normalized_query.isascii():
        return 0.75

    return 0.0


def _row_to_candidate(row: pd.Series, market: str) -> _CatalogEntry | None:
    ticker = _canonical_ticker(str(_first_value(row, "ts_code", "symbol", "code") or ""), market)
    name = str(_first_value(row, "name", "fullname", "enname") or "").strip()
    if not ticker or not name:
        return None

    aliases = _collect_aliases(row, name)
    exchange = _exchange_for_row(row, market, ticker)
    list_status = str(row.get("list_status") or "").upper()
    return _CatalogEntry(
        ticker=ticker,
        name=name,
        market=market,
        exchange=exchange,
        aliases=aliases,
        is_active=list_status in {"", "L"},
    )


def _canonical_ticker(ticker: str, market: str) -> str:
    value = ticker.strip().upper()
    if not value:
        return ""
    if market == MARKET_HK:
        match = re.fullmatch(r"(\d{4,5})(?:\.HK)?", value)
        if not match:
            return value
        digits = match.group(1).lstrip("0") or "0"
        return f"{digits.zfill(4)}.HK"
    if market == MARKET_A_SHARE:
        if re.fullmatch(r"\d{6}\.(?:SH|SZ|BJ)", value):
            return value
        if re.fullmatch(r"(?:SH|SZ|BJ)\.?\d{6}", value):
            exchange, digits = value[:2], value[-6:]
            return f"{digits}.{exchange}"
        normalized = normalize_symbol_for_vendor(value, "tushare", market)
        return normalized.upper()
    return value.removeprefix("US.")


def _collect_aliases(row: pd.Series, primary_name: str) -> tuple[str, ...]:
    aliases: list[str] = []
    for key in ("fullname", "enname", "cnspell"):
        value = str(row.get(key) or "").strip()
        if value and value.lower() != primary_name.lower():
            aliases.append(value)
    return tuple(dict.fromkeys(aliases))


def _exchange_for_row(row: pd.Series, market: str, ticker: str) -> str | None:
    exchange = str(row.get("exchange") or "").strip().upper()
    if exchange:
        if market == MARKET_A_SHARE:
            if exchange == "SH":
                return "SSE"
            if exchange == "SZ":
                return "SZSE"
            if exchange == "BJ":
                return "BSE"
            return exchange
        if market == MARKET_HK:
            return "HKEX" if exchange == "HK" else exchange
        return exchange

    if market == MARKET_A_SHARE:
        if ticker.endswith(".SH"):
            return "SSE"
        if ticker.endswith(".SZ"):
            return "SZSE"
        if ticker.endswith(".BJ"):
            return "BSE"
        return None
    if market == MARKET_HK:
        return "HKEX"
    return None


def _first_value(row: pd.Series, *columns: str) -> Any:
    for column in columns:
        value = row.get(column)
        if value is not None and str(value).strip():
            return value
    return None


def _select_supported_columns(dataframe: pd.DataFrame, fields: str) -> pd.DataFrame:
    columns = [column.strip() for column in fields.split(",") if column.strip()]
    supported = [column for column in columns if column in dataframe.columns]
    if not supported:
        return dataframe
    return dataframe[supported].copy()
