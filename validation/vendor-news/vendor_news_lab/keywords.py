from dataclasses import asdict, dataclass

from tradingagents.dataflows.market_resolver import (
    extract_a_share_code,
    extract_hk_code,
    extract_us_code,
    infer_a_share_exchange,
)

from .loader import MarketNewsCase


@dataclass(frozen=True)
class KeywordVariant:
    role: str
    value: str
    source: str = "generated"
    label: str = ""

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


def _add_variant(
    items: list[KeywordVariant],
    seen: set[tuple[str, str]],
    *,
    role: str,
    value: str | None,
    source: str = "generated",
    label: str = "",
) -> None:
    if value is None:
        return
    text = str(value).strip()
    if not text:
        return
    identity = (role.casefold(), text.casefold())
    if identity in seen:
        return
    seen.add(identity)
    items.append(KeywordVariant(role=role, value=text, source=source, label=label))


def _build_cn_variants(case: MarketNewsCase) -> list[KeywordVariant]:
    code = extract_a_share_code(case.ticker)
    exchange = infer_a_share_exchange(code)
    variants: list[KeywordVariant] = []
    seen: set[tuple[str, str]] = set()
    _add_variant(variants, seen, role="ticker", value=case.ticker)
    _add_variant(variants, seen, role="ticker_code", value=code)
    _add_variant(variants, seen, role="ticker_symbol", value=f"{code}.{exchange}")
    _add_variant(variants, seen, role="ticker_exchange_prefix", value=f"{exchange}.{code}")
    _add_variant(variants, seen, role="company_name_local", value=case.company_name_local)
    _add_variant(variants, seen, role="company_name_en", value=case.company_name_en)
    for alias in case.aliases:
        _add_variant(variants, seen, role="alias", value=alias)
    for item in case.candidate_keywords:
        _add_variant(
            variants,
            seen,
            role=str(item.get("role", "manifest_keyword")),
            value=item.get("value"),
            source=str(item.get("source", "manifest")),
            label=str(item.get("label", "")),
        )
    return variants


def _build_hk_variants(case: MarketNewsCase) -> list[KeywordVariant]:
    code = extract_hk_code(case.ticker)
    compact = code.lstrip("0") or "0"
    variants: list[KeywordVariant] = []
    seen: set[tuple[str, str]] = set()
    _add_variant(variants, seen, role="ticker", value=case.ticker)
    _add_variant(variants, seen, role="ticker_numeric_compact", value=compact)
    _add_variant(variants, seen, role="ticker_numeric_padded", value=code)
    _add_variant(variants, seen, role="ticker_symbol", value=f"{code}.HK")
    _add_variant(variants, seen, role="company_name_local", value=case.company_name_local)
    _add_variant(variants, seen, role="company_name_en", value=case.company_name_en)
    for alias in case.aliases:
        _add_variant(variants, seen, role="alias", value=alias)
    for item in case.candidate_keywords:
        _add_variant(
            variants,
            seen,
            role=str(item.get("role", "manifest_keyword")),
            value=item.get("value"),
            source=str(item.get("source", "manifest")),
            label=str(item.get("label", "")),
        )
    return variants


def _build_us_variants(case: MarketNewsCase) -> list[KeywordVariant]:
    symbol = extract_us_code(case.ticker)
    variants: list[KeywordVariant] = []
    seen: set[tuple[str, str]] = set()
    _add_variant(variants, seen, role="ticker", value=case.ticker)
    _add_variant(variants, seen, role="ticker_symbol", value=symbol)
    _add_variant(variants, seen, role="ticker_us_prefix", value=f"US.{symbol}")
    _add_variant(variants, seen, role="company_name_en", value=case.company_name_en)
    _add_variant(variants, seen, role="company_name_local", value=case.company_name_local)
    for alias in case.aliases:
        _add_variant(variants, seen, role="alias", value=alias)
    for item in case.candidate_keywords:
        _add_variant(
            variants,
            seen,
            role=str(item.get("role", "manifest_keyword")),
            value=item.get("value"),
            source=str(item.get("source", "manifest")),
            label=str(item.get("label", "")),
        )
    return variants


def build_keyword_variants(case: MarketNewsCase) -> list[KeywordVariant]:
    market = case.market.lower()
    if market == "cn":
        return _build_cn_variants(case)
    if market == "hk":
        return _build_hk_variants(case)
    if market == "us":
        return _build_us_variants(case)
    raise ValueError(f"Unsupported market for keyword generation: {case.market}")
