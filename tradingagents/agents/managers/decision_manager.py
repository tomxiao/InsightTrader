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
        prompt = f"""你是一个轻量级交易分析团队的投资决策经理。

你的任务是综合现有分析师报告，给出一份简洁、明确的最终投资决策。

标的：{instrument}
分析日期：{trade_date}

输出必须严格包含以下结构：
1. 评级：必须且只能使用以下五个评级之一：买入 / 增持 / 持有 / 减持 / 卖出
2. 执行摘要：给出一段简短、面向行动的结论摘要
3. 关键催化因素：列出 3-6 条关键催化因素
4. 关键风险：列出 3-6 条关键风险
5. 证据摘要：总结市场、新闻、基本面三方面最重要的依据

市场报告：
{market_report or "N/A"}

新闻报告：
{news_report or "N/A"}

基本面报告：
{fundamentals_report or "N/A"}

请保持结论明确、表达简洁，并且只能基于以上提供的报告内容作出判断，不要引入外部信息或额外假设。

请不要输出英文标题，也不要输出英文评级。最终结果必须完全使用中文。{get_language_instruction()}"""
        response = llm.invoke(prompt)
        content = getattr(response, "content", "") or ""
        return {
            "investment_plan": content,
            "final_trade_decision": content,
        }

    return decision_manager_node
