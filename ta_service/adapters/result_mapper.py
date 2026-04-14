from __future__ import annotations

import logging
from pathlib import Path

LOGGER = logging.getLogger(__name__)


def save_report_to_disk(final_state: dict, save_path: Path) -> Path:
    """Write each agent node's raw output as individual markdown files under save_path.

    Directory layout:
        1_analysts/  market.md  sentiment.md  news.md  fundamentals.md
        2_research/  bull.md  bear.md  manager.md
        3_trading/   trader.md
        4_risk/      aggressive.md  conservative.md  neutral.md
        5_portfolio/ decision.md
    """
    save_path.mkdir(parents=True, exist_ok=True)

    # 1. Analyst Team
    analysts_dir = save_path / "1_analysts"
    if final_state.get("market_report"):
        analysts_dir.mkdir(exist_ok=True)
        (analysts_dir / "market.md").write_text(final_state["market_report"], encoding="utf-8")
    if final_state.get("sentiment_report"):
        analysts_dir.mkdir(exist_ok=True)
        (analysts_dir / "sentiment.md").write_text(
            final_state["sentiment_report"], encoding="utf-8"
        )
    if final_state.get("news_report"):
        analysts_dir.mkdir(exist_ok=True)
        (analysts_dir / "news.md").write_text(final_state["news_report"], encoding="utf-8")
    if final_state.get("fundamentals_report"):
        analysts_dir.mkdir(exist_ok=True)
        (analysts_dir / "fundamentals.md").write_text(
            final_state["fundamentals_report"], encoding="utf-8"
        )

    # 2. Research Team
    if final_state.get("investment_debate_state"):
        research_dir = save_path / "2_research"
        debate = final_state["investment_debate_state"]
        if debate.get("bull_history"):
            research_dir.mkdir(exist_ok=True)
            (research_dir / "bull.md").write_text(debate["bull_history"], encoding="utf-8")
        if debate.get("bear_history"):
            research_dir.mkdir(exist_ok=True)
            (research_dir / "bear.md").write_text(debate["bear_history"], encoding="utf-8")
        if debate.get("judge_decision"):
            research_dir.mkdir(exist_ok=True)
            (research_dir / "manager.md").write_text(debate["judge_decision"], encoding="utf-8")

    # 3. Trading Team
    if final_state.get("trader_investment_plan"):
        trading_dir = save_path / "3_trading"
        trading_dir.mkdir(exist_ok=True)
        (trading_dir / "trader.md").write_text(
            final_state["trader_investment_plan"], encoding="utf-8"
        )

    # 4. Risk Management
    if final_state.get("risk_debate_state"):
        risk_dir = save_path / "4_risk"
        risk = final_state["risk_debate_state"]
        if risk.get("aggressive_history"):
            risk_dir.mkdir(exist_ok=True)
            (risk_dir / "aggressive.md").write_text(risk["aggressive_history"], encoding="utf-8")
        if risk.get("conservative_history"):
            risk_dir.mkdir(exist_ok=True)
            (risk_dir / "conservative.md").write_text(
                risk["conservative_history"], encoding="utf-8"
            )
        if risk.get("neutral_history"):
            risk_dir.mkdir(exist_ok=True)
            (risk_dir / "neutral.md").write_text(risk["neutral_history"], encoding="utf-8")

        # 5. Portfolio Manager
        if risk.get("judge_decision"):
            portfolio_dir = save_path / "5_portfolio"
            portfolio_dir.mkdir(exist_ok=True)
            (portfolio_dir / "decision.md").write_text(risk["judge_decision"], encoding="utf-8")

    LOGGER.info("report saved to %s", save_path)
    return save_path


def extract_executive_summary(final_state: dict) -> str | None:
    candidates = [
        final_state.get("final_trade_decision"),
        final_state.get("trader_investment_plan"),
        final_state.get("investment_plan"),
    ]
    for candidate in candidates:
        if candidate and candidate.strip():
            return candidate.strip()
    return None
