import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class MarketNewsCase:
    case_id: str
    market: str
    ticker: str
    label: str
    analysis_date: str
    start_date: str
    end_date: str
    company_name_local: str = ""
    company_name_en: str = ""
    aliases: list[str] = field(default_factory=list)
    candidate_keywords: list[dict[str, Any]] = field(default_factory=list)
    notes: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class VendorConfig:
    vendor_key: str
    display_name: str
    markets_supported: list[str]
    news_mode: str
    requires_api_key_env: str | None = None
    enabled: bool = True
    notes: str = ""

    def supports_market(self, market: str) -> bool:
        return market in self.markets_supported

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _read_json(path: str | Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _normalize_text_list(values: list[Any] | None) -> list[str]:
    if not values:
        return []
    seen: set[str] = set()
    normalized: list[str] = []
    for value in values:
        text = str(value).strip()
        if not text:
            continue
        key = text.casefold()
        if key in seen:
            continue
        seen.add(key)
        normalized.append(text)
    return normalized


def _normalize_candidate_keywords(values: list[Any] | None) -> list[dict[str, Any]]:
    if not values:
        return []

    normalized: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for item in values:
        if isinstance(item, str):
            payload = {"role": "manifest_keyword", "value": item, "source": "manifest"}
        elif isinstance(item, dict):
            payload = {
                "role": str(item.get("role", "manifest_keyword")).strip() or "manifest_keyword",
                "value": str(item.get("value", "")).strip(),
                "source": str(item.get("source", "manifest")).strip() or "manifest",
            }
            for key in ("label", "notes"):
                if item.get(key):
                    payload[key] = str(item[key])
        else:
            continue

        value = payload["value"].strip()
        if not value:
            continue
        identity = (payload["role"].casefold(), value.casefold())
        if identity in seen:
            continue
        seen.add(identity)
        payload["value"] = value
        normalized.append(payload)
    return normalized


def load_news_cases(manifest_path: str | Path) -> list[MarketNewsCase]:
    payload = _read_json(manifest_path)
    cases: list[MarketNewsCase] = []
    for item in payload:
        cases.append(
            MarketNewsCase(
                case_id=item["case_id"],
                market=str(item["market"]).strip().lower(),
                ticker=str(item["ticker"]).strip(),
                label=str(item["label"]).strip(),
                analysis_date=str(item["analysis_date"]).strip(),
                start_date=str(item["start_date"]).strip(),
                end_date=str(item["end_date"]).strip(),
                company_name_local=str(item.get("company_name_local", "")).strip(),
                company_name_en=str(item.get("company_name_en", "")).strip(),
                aliases=_normalize_text_list(item.get("aliases")),
                candidate_keywords=_normalize_candidate_keywords(item.get("candidate_keywords")),
                notes=str(item.get("notes", "")).strip(),
                metadata=dict(item.get("metadata", {})),
            )
        )
    return cases


def load_vendor_configs(config_path: str | Path) -> list[VendorConfig]:
    payload = _read_json(config_path)
    vendors: list[VendorConfig] = []
    for item in payload:
        vendors.append(
            VendorConfig(
                vendor_key=str(item["vendor_key"]).strip().lower(),
                display_name=str(item["display_name"]).strip(),
                markets_supported=[str(market).strip().lower() for market in item.get("markets_supported", [])],
                news_mode=str(item["news_mode"]).strip(),
                requires_api_key_env=(
                    str(item["requires_api_key_env"]).strip()
                    if item.get("requires_api_key_env")
                    else None
                ),
                enabled=bool(item.get("enabled", True)),
                notes=str(item.get("notes", "")).strip(),
            )
        )
    return vendors
