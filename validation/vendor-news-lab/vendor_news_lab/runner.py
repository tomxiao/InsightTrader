import csv
import json
import re
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from io import StringIO
from pathlib import Path
from typing import Any, Callable, Iterable

import pandas as pd

from tradingagents.dataflows.akshare_common import fetch_stock_news_em, get_akshare_module, run_without_proxy
from tradingagents.dataflows.finnhub_common import get_finnhub_client
from tradingagents.dataflows.formatting import format_dataframe_report
from tradingagents.dataflows.market_resolver import (
    extract_a_share_code,
    extract_hk_code,
    extract_us_code,
    infer_a_share_exchange,
)
from tradingagents.dataflows.tushare_common import get_tushare_pro

from .keywords import KeywordVariant, build_keyword_variants
from .loader import MarketNewsCase, VendorConfig

SUPPORTED_MODES = ("vendor-comparison", "keyword-expansion")


class UnsupportedValidationError(RuntimeError):
    pass


@dataclass
class ValidationResult:
    mode: str
    case_id: str
    market: str
    ticker: str
    case_label: str
    vendor_key: str
    vendor_display_name: str
    news_mode: str
    keyword_role: str | None
    keyword_value: str | None
    keyword_source: str | None
    started_at: str
    duration_ms: int
    supported: bool
    success: bool
    outcome: str
    is_empty: bool
    item_count: int
    response_text: str
    response_chars: int
    error_type: str | None
    error_message: str | None
    snapshot_path: str | None
    raw_metadata: dict[str, Any]

    def to_record(self) -> dict[str, Any]:
        return asdict(self)


VendorFetcher = Callable[[VendorConfig, MarketNewsCase], str]
KeywordFetcher = Callable[[VendorConfig, MarketNewsCase, KeywordVariant], str]


def default_vendor_news_fetcher(vendor: VendorConfig, case: MarketNewsCase) -> str:
    from tradingagents.dataflows.interface import VENDOR_METHODS

    method = VENDOR_METHODS["get_news"].get(vendor.vendor_key)
    if method is None:
        raise UnsupportedValidationError(f"No get_news implementation registered for vendor `{vendor.vendor_key}`.")
    return method(case.ticker, case.start_date, case.end_date)


def default_keyword_expansion_fetcher(
    vendor: VendorConfig,
    case: MarketNewsCase,
    variant: KeywordVariant,
) -> str:
    if vendor.vendor_key == "tushare":
        return _fetch_tushare_keyword_news(case, variant)
    if vendor.vendor_key == "akshare":
        return _fetch_akshare_keyword_news(case, variant)
    if vendor.vendor_key == "finnhub":
        return _fetch_finnhub_keyword_news(case, variant)
    raise UnsupportedValidationError(
        f"Keyword expansion is not implemented for vendor `{vendor.vendor_key}`."
    )


class NewsValidationRunner:
    def __init__(
        self,
        output_root: str | Path,
        *,
        vendor_news_fetcher: VendorFetcher = default_vendor_news_fetcher,
        keyword_expansion_fetcher: KeywordFetcher = default_keyword_expansion_fetcher,
    ) -> None:
        self.output_root = Path(output_root)
        self.vendor_news_fetcher = vendor_news_fetcher
        self.keyword_expansion_fetcher = keyword_expansion_fetcher

    def run(
        self,
        *,
        cases: list[MarketNewsCase],
        vendors: list[VendorConfig],
        modes: Iterable[str] = SUPPORTED_MODES,
    ) -> tuple[Path, list[ValidationResult]]:
        selected_modes = tuple(dict.fromkeys(modes))
        invalid_modes = [mode for mode in selected_modes if mode not in SUPPORTED_MODES]
        if invalid_modes:
            raise ValueError(f"Unsupported validation modes: {invalid_modes}")

        run_dir = self.output_root / datetime.now().strftime("%Y%m%d_%H%M%S")
        run_dir.mkdir(parents=True, exist_ok=True)
        results: list[ValidationResult] = []

        enabled_vendors = [vendor for vendor in vendors if vendor.enabled]
        for mode in selected_modes:
            if mode == "vendor-comparison":
                results.extend(self._run_vendor_comparison(cases, enabled_vendors))
            elif mode == "keyword-expansion":
                results.extend(self._run_keyword_expansion(cases, enabled_vendors))

        self._write_outputs(run_dir, results)
        return run_dir, results

    def _run_vendor_comparison(
        self,
        cases: list[MarketNewsCase],
        vendors: list[VendorConfig],
    ) -> list[ValidationResult]:
        results: list[ValidationResult] = []
        for case in cases:
            for vendor in vendors:
                results.append(
                    self._execute_call(
                        mode="vendor-comparison",
                        case=case,
                        vendor=vendor,
                        keyword_variant=None,
                        fetch=lambda: self.vendor_news_fetcher(vendor, case),
                    )
                )
        return results

    def _run_keyword_expansion(
        self,
        cases: list[MarketNewsCase],
        vendors: list[VendorConfig],
    ) -> list[ValidationResult]:
        results: list[ValidationResult] = []
        for case in cases:
            variants = build_keyword_variants(case)
            for vendor in vendors:
                for variant in variants:
                    results.append(
                        self._execute_call(
                            mode="keyword-expansion",
                            case=case,
                            vendor=vendor,
                            keyword_variant=variant,
                            fetch=lambda vendor=vendor, case=case, variant=variant: self.keyword_expansion_fetcher(
                                vendor,
                                case,
                                variant,
                            ),
                        )
                    )
        return results

    def _execute_call(
        self,
        *,
        mode: str,
        case: MarketNewsCase,
        vendor: VendorConfig,
        keyword_variant: KeywordVariant | None,
        fetch: Callable[[], str],
    ) -> ValidationResult:
        started_at = datetime.now().isoformat()

        if not vendor.supports_market(case.market):
            return self._build_unsupported_result(
                mode=mode,
                case=case,
                vendor=vendor,
                keyword_variant=keyword_variant,
                started_at=started_at,
                message=f"Vendor `{vendor.vendor_key}` is not configured for market `{case.market}`.",
            )

        start = time.monotonic()
        try:
            response_text = fetch()
        except UnsupportedValidationError as exc:
            return self._build_unsupported_result(
                mode=mode,
                case=case,
                vendor=vendor,
                keyword_variant=keyword_variant,
                started_at=started_at,
                message=str(exc),
                duration_ms=int((time.monotonic() - start) * 1000),
            )
        except Exception as exc:
            return self._build_result(
                mode=mode,
                case=case,
                vendor=vendor,
                keyword_variant=keyword_variant,
                started_at=started_at,
                duration_ms=int((time.monotonic() - start) * 1000),
                supported=True,
                success=False,
                outcome="error",
                is_empty=False,
                item_count=0,
                response_text="",
                error_type=exc.__class__.__name__,
                error_message=str(exc),
                raw_metadata={},
            )

        duration_ms = int((time.monotonic() - start) * 1000)
        if response_text.startswith("Error "):
            return self._build_result(
                mode=mode,
                case=case,
                vendor=vendor,
                keyword_variant=keyword_variant,
                started_at=started_at,
                duration_ms=duration_ms,
                supported=True,
                success=False,
                outcome="error",
                is_empty=False,
                item_count=0,
                response_text=response_text,
                error_type="VendorErrorString",
                error_message=response_text,
                raw_metadata={},
            )

        item_count = _extract_item_count(response_text)
        is_empty = item_count == 0 or "No data available" in response_text
        return self._build_result(
            mode=mode,
            case=case,
            vendor=vendor,
            keyword_variant=keyword_variant,
            started_at=started_at,
            duration_ms=duration_ms,
            supported=True,
            success=True,
            outcome="empty" if is_empty else "ok",
            is_empty=is_empty,
            item_count=item_count,
            response_text=response_text,
            error_type=None,
            error_message=None,
            raw_metadata={},
        )

    def _build_unsupported_result(
        self,
        *,
        mode: str,
        case: MarketNewsCase,
        vendor: VendorConfig,
        keyword_variant: KeywordVariant | None,
        started_at: str,
        message: str,
        duration_ms: int = 0,
    ) -> ValidationResult:
        return self._build_result(
            mode=mode,
            case=case,
            vendor=vendor,
            keyword_variant=keyword_variant,
            started_at=started_at,
            duration_ms=duration_ms,
            supported=False,
            success=False,
            outcome="unsupported",
            is_empty=False,
            item_count=0,
            response_text="",
            error_type="UnsupportedValidationError",
            error_message=message,
            raw_metadata={},
        )

    def _build_result(
        self,
        *,
        mode: str,
        case: MarketNewsCase,
        vendor: VendorConfig,
        keyword_variant: KeywordVariant | None,
        started_at: str,
        duration_ms: int,
        supported: bool,
        success: bool,
        outcome: str,
        is_empty: bool,
        item_count: int,
        response_text: str,
        error_type: str | None,
        error_message: str | None,
        raw_metadata: dict[str, Any],
    ) -> ValidationResult:
        return ValidationResult(
            mode=mode,
            case_id=case.case_id,
            market=case.market,
            ticker=case.ticker,
            case_label=case.label,
            vendor_key=vendor.vendor_key,
            vendor_display_name=vendor.display_name,
            news_mode=vendor.news_mode,
            keyword_role=keyword_variant.role if keyword_variant else None,
            keyword_value=keyword_variant.value if keyword_variant else None,
            keyword_source=keyword_variant.source if keyword_variant else None,
            started_at=started_at,
            duration_ms=duration_ms,
            supported=supported,
            success=success,
            outcome=outcome,
            is_empty=is_empty,
            item_count=item_count,
            response_text=response_text,
            response_chars=len(response_text),
            error_type=error_type,
            error_message=error_message,
            snapshot_path=None,
            raw_metadata=raw_metadata,
        )

    def _write_outputs(self, run_dir: Path, results: list[ValidationResult]) -> None:
        self._write_snapshots(run_dir / "snapshots", results)
        self._write_results_jsonl(run_dir / "results.jsonl", results)
        self._write_summary_csv(run_dir / "summary.csv", results)
        self._write_summary_md(run_dir / "summary.md", results)

    def _write_snapshots(self, snapshot_root: Path, results: list[ValidationResult]) -> None:
        for result in results:
            variant_slug = _slugify(result.keyword_value or "direct")
            filename = f"{result.mode}__{variant_slug}.md"
            target = snapshot_root / result.case_id / result.vendor_key / filename
            target.parent.mkdir(parents=True, exist_ok=True)
            lines = [
                f"# {result.case_id} / {result.vendor_display_name}",
                "",
                f"- mode: `{result.mode}`",
                f"- market: `{result.market}`",
                f"- ticker: `{result.ticker}`",
                f"- outcome: `{result.outcome}`",
                f"- duration_ms: `{result.duration_ms}`",
                f"- item_count: `{result.item_count}`",
            ]
            if result.keyword_value:
                lines.append(f"- keyword: `{result.keyword_value}`")
            if result.error_message:
                lines.append(f"- error_message: `{result.error_message}`")
            lines.append("")
            if result.success and result.response_chars:
                lines.append(result.response_text)
            elif result.error_message:
                lines.extend(["## Error", "", result.error_message])
            else:
                lines.append("No snapshot content captured.")
            target.write_text("\n".join(lines) + "\n", encoding="utf-8")
            result.snapshot_path = str(target.relative_to(run_dir := snapshot_root.parent))

    def _write_results_jsonl(self, path: Path, results: list[ValidationResult]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as handle:
            for result in results:
                handle.write(json.dumps(result.to_record(), ensure_ascii=False, default=str) + "\n")

    def _write_summary_csv(self, path: Path, results: list[ValidationResult]) -> None:
        rows = [
            {
                "mode": result.mode,
                "case_id": result.case_id,
                "market": result.market,
                "ticker": result.ticker,
                "vendor_key": result.vendor_key,
                "news_mode": result.news_mode,
                "keyword_role": result.keyword_role,
                "keyword_value": result.keyword_value,
                "supported": result.supported,
                "success": result.success,
                "outcome": result.outcome,
                "is_empty": result.is_empty,
                "item_count": result.item_count,
                "duration_ms": result.duration_ms,
                "response_chars": result.response_chars,
                "error_type": result.error_type,
                "error_message": result.error_message,
                "snapshot_path": result.snapshot_path,
            }
            for result in results
        ]
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()) if rows else [])
            if rows:
                writer.writeheader()
                writer.writerows(rows)

    def _write_summary_md(self, path: Path, results: list[ValidationResult]) -> None:
        mode_market_vendor_rows = _aggregate_rows(
            results,
            keys=("mode", "market", "vendor_key"),
        )
        keyword_rows = _aggregate_rows(
            [item for item in results if item.mode == "keyword-expansion"],
            keys=("market", "vendor_key", "keyword_role"),
        )

        lines = [
            "# News Vendor Validation Summary",
            "",
            f"- total_calls: {len(results)}",
            f"- successful_calls: {sum(1 for item in results if item.success)}",
            f"- failed_calls: {sum(1 for item in results if not item.success and item.outcome == 'error')}",
            f"- unsupported_calls: {sum(1 for item in results if item.outcome == 'unsupported')}",
            f"- empty_calls: {sum(1 for item in results if item.outcome == 'empty')}",
            "",
            "## Mode / Market / Vendor",
            "",
            "| Mode | Market | Vendor | Calls | Ok | Empty | Error | Unsupported | Avg Duration (ms) |",
            "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
        for row in mode_market_vendor_rows:
            lines.append(
                "| {mode} | {market} | {vendor_key} | {calls} | {ok} | {empty} | {error} | {unsupported} | {avg_duration_ms} |".format(
                    **row
                )
            )

        if keyword_rows:
            lines.extend(
                [
                    "",
                    "## Keyword Role Coverage",
                    "",
                    "| Market | Vendor | Keyword Role | Calls | Ok | Empty | Error | Unsupported | Avg Duration (ms) |",
                    "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |",
                ]
            )
            for row in keyword_rows:
                lines.append(
                    "| {market} | {vendor_key} | {keyword_role} | {calls} | {ok} | {empty} | {error} | {unsupported} | {avg_duration_ms} |".format(
                        **row
                    )
                )

        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _fetch_tushare_keyword_news(case: MarketNewsCase, variant: KeywordVariant) -> str:
    if case.market not in {"cn", "hk"}:
        raise UnsupportedValidationError(
            "Tushare keyword expansion is limited to CN/HK in this validation lab."
        )
    dataframe = get_tushare_pro().news(
        start_date=case.start_date.replace("-", ""),
        end_date=case.end_date.replace("-", ""),
    )
    filtered = _filter_dataframe_by_keyword(dataframe, variant.value)
    return format_dataframe_report(
        f"Tushare keyword news for {case.ticker}",
        filtered,
        {
            "Vendor": "tushare",
            "Market": case.market,
            "Keyword": variant.value,
            "Keyword role": variant.role,
            "Fetch mode": "time_window_filter",
            "Start date": case.start_date,
            "End date": case.end_date,
        },
    )


def _fetch_akshare_keyword_news(case: MarketNewsCase, variant: KeywordVariant) -> str:
    if case.market not in {"cn", "hk"}:
        raise UnsupportedValidationError(
            "AKShare keyword expansion is limited to CN/HK in this validation lab."
        )

    ak = get_akshare_module()
    errors: list[str] = []
    dataframe = pd.DataFrame()
    strategy = "main_cx_filter"
    symbol_candidates = _build_akshare_symbol_candidates(case.market, variant.value)
    selected_symbol = symbol_candidates[0] if symbol_candidates else variant.value.strip()

    for candidate in symbol_candidates:
        try:
            dataframe = fetch_stock_news_em(candidate)
            dataframe = _filter_dataframe_by_date(dataframe, case.start_date, case.end_date)
            selected_symbol = candidate
            strategy = "stock_news_em"
            if not dataframe.empty:
                break
        except Exception as exc:
            errors.append(f"{candidate}: {exc}")
            dataframe = pd.DataFrame()

    if dataframe.empty:
        dataframe = run_without_proxy(lambda: ak.stock_news_main_cx())
        dataframe = _coerce_dataframe(dataframe)
        dataframe = _filter_dataframe_by_date(dataframe, case.start_date, case.end_date)
        dataframe = _filter_dataframe_by_keyword(dataframe, variant.value)
        strategy = "main_cx_filter" if not errors else "stock_news_em->main_cx_filter"

    return format_dataframe_report(
        f"AKShare keyword news for {case.ticker}",
        dataframe,
        {
            "Vendor": "akshare",
            "Market": case.market,
            "Keyword": variant.value,
            "Keyword role": variant.role,
            "Vendor symbol": selected_symbol,
            "Candidate symbols": ", ".join(symbol_candidates),
            "Fetch mode": strategy,
            "Fallback errors": "; ".join(errors) if errors else None,
            "Start date": case.start_date,
            "End date": case.end_date,
        },
    )


def _fetch_finnhub_keyword_news(case: MarketNewsCase, variant: KeywordVariant) -> str:
    if case.market != "us":
        raise UnsupportedValidationError(
            "Finnhub keyword expansion is limited to US in this validation lab."
        )
    symbol = _normalize_finnhub_symbol(case, variant.value)
    data = get_finnhub_client().company_news(symbol, _from=case.start_date, to=case.end_date)
    dataframe = pd.DataFrame(data)
    return format_dataframe_report(
        f"Finnhub keyword news for {case.ticker}",
        dataframe,
        {
            "Vendor": "finnhub",
            "Market": case.market,
            "Keyword": variant.value,
            "Keyword role": variant.role,
            "Vendor symbol": symbol,
            "Fetch mode": "symbol_native",
            "Start date": case.start_date,
            "End date": case.end_date,
        },
    )


def _build_akshare_symbol_candidates(market: str, keyword: str) -> list[str]:
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

    if market == "cn":
        try:
            code = extract_a_share_code(text)
            exchange = infer_a_share_exchange(code)
            add(f"{code}.{exchange}")
            add(f"{exchange}.{code}")
            add(code)
        except Exception:
            pass
        return candidates

    if market == "hk":
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


def _normalize_finnhub_symbol(case: MarketNewsCase, keyword: str) -> str:
    canonical = extract_us_code(case.ticker)
    candidate = extract_us_code(keyword)
    if candidate != canonical:
        raise UnsupportedValidationError(
            "Finnhub keyword expansion only supports symbol-equivalent keyword variants."
        )
    return candidate

def _coerce_dataframe(payload: Any) -> pd.DataFrame:
    if isinstance(payload, pd.DataFrame):
        return payload
    return pd.DataFrame(payload)


def _filter_dataframe_by_keyword(dataframe: pd.DataFrame, keyword: str) -> pd.DataFrame:
    dataframe = _coerce_dataframe(dataframe)
    if dataframe.empty:
        return dataframe
    pattern, use_regex = _build_keyword_matcher(keyword)
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


def _build_keyword_matcher(keyword: str) -> tuple[str, bool]:
    text = keyword.strip()
    if not text:
        return "", False

    if re.fullmatch(r"\d+", text):
        return rf"(?<!\d){re.escape(text)}(?!\d)", True

    upper = text.upper()
    if re.fullmatch(r"\d+\.(?:HK|SH|SZ)", upper) or re.fullmatch(r"(?:HK|SH|SZ)\.\d+", upper):
        return rf"(?<![A-Z0-9]){re.escape(text)}(?![A-Z0-9])", True

    return text, False


def _filter_dataframe_by_date(dataframe: pd.DataFrame, start_date: str, end_date: str) -> pd.DataFrame:
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


def _extract_item_count(response_text: str) -> int:
    if not response_text or "No data available" in response_text:
        return 0
    csv_body = _extract_csv_body(response_text)
    if not csv_body:
        return 0
    rows = list(csv.reader(StringIO(csv_body)))
    return max(len(rows) - 1, 0)


def _extract_csv_body(response_text: str) -> str:
    parts = response_text.split("\n\n", 1)
    if len(parts) < 2:
        return ""
    return parts[1].strip()


def _aggregate_rows(results: list[ValidationResult], *, keys: tuple[str, ...]) -> list[dict[str, Any]]:
    grouped: dict[tuple[Any, ...], list[ValidationResult]] = {}
    for result in results:
        key = tuple(getattr(result, field) for field in keys)
        grouped.setdefault(key, []).append(result)

    rows: list[dict[str, Any]] = []
    for key, items in sorted(grouped.items(), key=lambda item: item[0]):
        row = {
            field: value if value is not None else ""
            for field, value in zip(keys, key, strict=False)
        }
        row.update(
            {
                "calls": len(items),
                "ok": sum(1 for item in items if item.outcome == "ok"),
                "empty": sum(1 for item in items if item.outcome == "empty"),
                "error": sum(1 for item in items if item.outcome == "error"),
                "unsupported": sum(1 for item in items if item.outcome == "unsupported"),
                "avg_duration_ms": round(sum(item.duration_ms for item in items) / len(items), 2),
            }
        )
        rows.append(row)
    return rows


def _slugify(value: str) -> str:
    text = re.sub(r"[^A-Za-z0-9._-]+", "_", value.strip()).strip("._")
    return text[:80] or "default"
