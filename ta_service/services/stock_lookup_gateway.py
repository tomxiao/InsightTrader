from __future__ import annotations

from dataclasses import dataclass
import logging
import re
from threading import Lock
from typing import Any

import pandas as pd

from ta_service.models.resolution import ResolutionCandidate
from tradingagents.dataflows.market_resolver import (
    MARKET_A_SHARE,
    MARKET_HK,
    MARKET_US,
    detect_market,
    normalize_symbol_for_vendor,
)
from tradingagents.dataflows.tushare_common import get_tushare_pro

logger = logging.getLogger(__name__)

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
        normalized_query = query.strip().lower()
        if not normalized_query:
            return []

        exact_ticker = self.get_stock_profile(ticker=query)
        if exact_ticker is not None:
            return [exact_ticker.model_copy(update={"score": 1.0})]

        markets = _resolve_markets(query=query, market_hints=market_hints)
        scored: list[tuple[float, ResolutionCandidate]] = []
        errors: list[str] = []

        for market in markets:
            try:
                catalog = self._load_market_catalog(market)
            except Exception as exc:  # pragma: no cover - depends on vendor runtime
                logger.warning("stock_search_catalog_load_failed market=%s error=%s", market, exc)
                errors.append(str(exc))
                continue

            ticker_hint = _normalize_ticker_hint(query)
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

        ranked = sorted(deduped.values(), key=lambda candidate: (-(candidate.score or 0), candidate.ticker))
        return ranked[:limit]

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

        dataframe = self._load_tushare_catalog(market)
        entries = [_row_to_candidate(row, market) for _, row in dataframe.iterrows()]
        entries = [entry for entry in entries if entry is not None]

        with self._cache_lock:
            self._catalog_cache[market] = entries
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
