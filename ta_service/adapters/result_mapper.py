from __future__ import annotations

from datetime import datetime


def extract_executive_summary(final_state: dict) -> str | None:
    candidates = [
        final_state.get("investment_plan"),
        final_state.get("final_trade_decision"),
        final_state.get("trader_investment_plan"),
    ]
    for candidate in candidates:
        if candidate and candidate.strip():
            return candidate.strip()
    return None


def build_complete_report_markdown(final_state: dict, ticker: str) -> str:
    sections: list[str] = [
        f"# Trading Analysis Report: {ticker}",
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
    ]

    if final_state.get("market_report"):
        sections.append(f"## Market Analysis\n\n{final_state['market_report']}")
    if final_state.get("sentiment_report"):
        sections.append(f"## Social Sentiment\n\n{final_state['sentiment_report']}")
    if final_state.get("news_report"):
        sections.append(f"## News Analysis\n\n{final_state['news_report']}")
    if final_state.get("fundamentals_report"):
        sections.append(f"## Fundamentals Analysis\n\n{final_state['fundamentals_report']}")
    if final_state.get("investment_plan"):
        sections.append(f"## Research Team Decision\n\n{final_state['investment_plan']}")
    if final_state.get("trader_investment_plan"):
        sections.append(f"## Trading Team Plan\n\n{final_state['trader_investment_plan']}")
    if final_state.get("final_trade_decision"):
        sections.append(f"## Portfolio Decision\n\n{final_state['final_trade_decision']}")

    return "\n\n".join(sections)
