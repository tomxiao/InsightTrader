from __future__ import annotations

from typing import Any

from tradingagents.agents.utils.agent_states import AgentState
from tradingagents.agents.utils.agent_utils import get_language_instruction


def create_decision_manager(llm: Any):
    def decision_manager_node(state: AgentState) -> dict:
        market_report = state.get("market_report", "")
        news_report = state.get("news_report", "")
        fundamentals_report = state.get("fundamentals_report", "")
        instrument = state["company_of_interest"]
        trade_date = state["trade_date"]
        prompt = f"""You are the Decision Manager for a lightweight trading analysis team.

Your job is to synthesize the available analyst reports into a concise final investment decision.

Ticker: {instrument}
Trade date: {trade_date}

Required output structure:
1. Rating: use exactly one of Buy / Overweight / Hold / Underweight / Sell
2. Executive Summary: a short action-oriented summary
3. Key Catalysts: 2-4 bullets
4. Key Risks: 2-4 bullets
5. Evidence Snapshot: summarize the most important evidence from market, news, and fundamentals

Market report:
{market_report or "N/A"}

News report:
{news_report or "N/A"}

Fundamentals report:
{fundamentals_report or "N/A"}

Be decisive, concise, and grounded only in the supplied reports.{get_language_instruction()}"""
        response = llm.invoke(prompt)
        content = getattr(response, "content", "") or ""
        return {
            "investment_plan": content,
            "final_trade_decision": content,
        }

    return decision_manager_node
