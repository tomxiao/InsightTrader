from __future__ import annotations

import re
from pathlib import Path

from .models import ReportSignal


def _field_pattern(label: str, value_pattern: str, *, multiline: bool = False) -> re.Pattern[str]:
    prefix = (
        rf"(?:^|\n)\s*"
        rf"(?:\*{{0,2}}\s*)?"
        rf"(?:\d+\.\s*)?"
        rf"(?:\*{{0,2}}\s*)?"
        rf"{label}\s*(?:\*{{0,2}})?\s*[：:]\s*(?:\*{{0,2}})?\s*"
    )
    body = value_pattern if multiline else rf"({value_pattern})"
    pattern = prefix + body
    return re.compile(pattern, re.MULTILINE)


FIELD_PATTERNS = {
    "trade_date": _field_pattern("分析日期", r"([0-9]{4}-[0-9]{2}-[0-9]{2})"),
    "reference_price": _field_pattern("截面价格", r"([^\n]+)"),
    "action": _field_pattern(
        "建议行动",
        r"\*{0,2}\s*(确信买入|择机买入|保持观望|建议卖出)\s*\*{0,2}(?=\s*(?:\n|$))",
    ),
    "entry_style": _field_pattern("入场方式", r"([^\n]+)"),
    "invalidations": _field_pattern(
        "失效条件",
        r"([\s\S]*?)(?=\n\s*(?:\d+\.\s*)?\*{0,2}\s*(?:适合的场景|不适合的场景|证据摘要)\s*(?:\*{0,2})?\s*[：:]|\Z)",
        multiline=True,
    ),
}

ACTION_MAP = {
    "确信买入": "buy_now",
    "择机买入": "buy_on_pullback",
    "保持观望": "hold",
    "建议卖出": "sell",
}

PRICE_WITH_UNIT_RE = re.compile(r"([0-9]+(?:\.[0-9]+)?)\s*美元")
LEADING_PRICE_RE = re.compile(r"^\s*([0-9]+(?:\.[0-9]+)?)(?!\s*[-/])")
RANGE_RE = re.compile(
    r"([0-9]+(?:\.[0-9]+)?)\s*(?:-|–|—|至)\s*([0-9]+(?:\.[0-9]+)?)\s*(?:美元)?"
)
BREAK_PRICE_RE = re.compile(r"(?:跌破|低于|失守)\s*\**([0-9]+(?:\.[0-9]+)?)\**\s*美元")
PAREN_PRICE_RE = re.compile(r"[（(][^）)]*?([0-9]+(?:\.[0-9]+)?)\s*美元[^）)]*[）)]")


def _extract_field(pattern: re.Pattern[str], text: str) -> str | None:
    match = pattern.search(text)
    if not match:
        return None
    return match.group(1).strip()


def _normalize_action_text(value: str | None) -> str | None:
    if value is None:
        return None
    return value.replace("*", "").strip()


def _parse_reference_price(text: str) -> tuple[float | None, str | None]:
    raw = _extract_field(FIELD_PATTERNS["reference_price"], text)
    if not raw:
        return None, None
    match = PRICE_WITH_UNIT_RE.search(raw)
    if match:
        return float(match.group(1)), raw
    match = LEADING_PRICE_RE.search(raw)
    return (float(match.group(1)), raw) if match else (None, raw)


def _parse_entry_zone(entry_style: str | None) -> tuple[float | None, float | None]:
    if not entry_style:
        return None, None
    match = RANGE_RE.search(entry_style)
    if not match:
        return None, None
    low = float(match.group(1))
    high = float(match.group(2))
    return (low, high) if low <= high else (high, low)


def _split_invalidation_lines(block: str | None) -> list[str]:
    if not block:
        return []
    lines: list[str] = []
    for line in block.splitlines():
        cleaned = line.strip().lstrip("*").strip()
        if cleaned:
            lines.append(cleaned)
    return lines


def _parse_invalidation_price(lines: list[str]) -> float | None:
    for line in lines:
        match = BREAK_PRICE_RE.search(line)
        if match:
            return float(match.group(1))
    for line in lines:
        match = PAREN_PRICE_RE.search(line)
        if match and ("均线" in line or "SMA" in line or "EMA" in line):
            return float(match.group(1))
    for line in lines:
        match = RANGE_RE.search(line)
        if match and "突破" not in line:
            return float(match.group(1))
    return None


def infer_ticker_from_report_path(path: Path) -> str:
    report_dir = path.parent.parent
    prefix = report_dir.name.split("_", 1)[0].strip()
    if not prefix:
        raise ValueError(f"Cannot infer ticker from report path: {path}")
    return prefix.upper()


def parse_report_text(text: str, *, ticker: str, report_path: Path | None = None) -> ReportSignal:
    trade_date = _extract_field(FIELD_PATTERNS["trade_date"], text)
    action_text = _normalize_action_text(_extract_field(FIELD_PATTERNS["action"], text))
    if not trade_date:
        raise ValueError("Report is missing `分析日期`")
    if not action_text:
        raise ValueError("Report is missing `建议行动`")

    reference_price, reference_price_text = _parse_reference_price(text)
    entry_style = _extract_field(FIELD_PATTERNS["entry_style"], text)
    entry_zone_low, entry_zone_high = _parse_entry_zone(entry_style)
    invalidation_lines = _split_invalidation_lines(_extract_field(FIELD_PATTERNS["invalidations"], text))
    invalidation_price = _parse_invalidation_price(invalidation_lines)

    return ReportSignal(
        ticker=ticker.upper(),
        trade_date=trade_date,
        action=ACTION_MAP[action_text],
        reference_price=reference_price,
        reference_price_text=reference_price_text,
        entry_style=entry_style,
        entry_zone_low=entry_zone_low,
        entry_zone_high=entry_zone_high,
        invalidation_price=invalidation_price,
        invalidation_texts=invalidation_lines,
        report_path=report_path,
    )


def parse_report_file(path: str | Path, *, ticker: str | None = None) -> ReportSignal:
    report_path = Path(path)
    if not report_path.exists():
        raise FileNotFoundError(report_path)
    effective_ticker = ticker or infer_ticker_from_report_path(report_path)
    return parse_report_text(
        report_path.read_text(encoding="utf-8"),
        ticker=effective_ticker,
        report_path=report_path,
    )
