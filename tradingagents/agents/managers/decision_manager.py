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

你的任务是综合现有分析师报告，给出一份简洁、明确、偏机会识别的最终投资决策。

你的核心判断问题不是“证据是否已经完美”，而是：

1. 未来 1-3 个月，这个标的是否存在值得参与的非对称机会？
2. 这个机会属于确信买入机会、择机买入机会、方向不明朗，还是偏空风险占优？
3. 如果参与，最合理的参与方式是什么？
4. 哪些条件会让当前判断失效？

标的：{instrument}
分析日期：{trade_date}

输出必须严格包含以下结构：
1. 分析日期：必须明确写出本次分析使用的日期，直接使用 `{trade_date}`
2. 分析截面：明确说明这是基于哪个时间截面做出的判断，例如“基于 {trade_date} 收盘后可得信息”或“基于 {trade_date} 附近的最新可得市场数据”
3. 截面价格：必须给出本次判断参考的价格，并简要说明该价格来自市场报告中的哪个时点或描述；如果市场报告无法确定精确价格，也要明确说明“市场报告未提供可确认的单一截面价格”
4. 建议行动：必须且只能使用以下四个建议行动之一：确信买入 / 择机买入 / 保持观望 / 建议卖出
5. 1-3个月核心判断：用 1 段话回答未来 1-3 个月是否值得参与，以及更偏明确看多、等待更优时机、方向不明朗还是风险占优
6. 执行摘要：给出一段简短、面向行动的结论摘要
7. 关键催化因素：列出 3-6 条关键催化因素
8. 关键风险：列出 3-6 条关键风险
9. 入场方式：若建议偏多，明确说明更适合直接参与、回调参与、等待确认还是暂不出手；若建议卖出，明确说明风险触发点或应优先降低风险的原因
10. 失效条件：列出 2-4 条会让当前判断失效的条件，不能只写“风险上升”
11. 适合的场景：说明这一建议更适用于什么样的判断场景或风险状态，不要假设你知道用户真实仓位
12. 不适合的场景：说明这一建议不适用于什么样的判断场景或风险状态，不要假设你知道用户真实仓位
13. 证据摘要：总结市场、新闻、基本面三方面最重要的依据

市场报告：
{market_report or "N/A"}

新闻报告：
{news_report or "N/A"}

基本面报告：
{fundamentals_report or "N/A"}

请保持结论明确、表达简洁，并且只能基于以上提供的报告内容作出判断，不要引入外部信息或额外假设。

决策规则：
1. 不要因为证据不完美就机械退回模糊结论。
2. 如果存在值得参与的机会，但更适合控制仓位、带条件参与，应优先使用“择机买入”。
3. 如果多空证据冲突、方向不明、暂时无法给出有效参与建议，应使用“保持观望”。
4. “确信买入”只适用于多维度证据较充分、上涨判断较明确的情形。
5. “建议卖出”用于风险占优、下行压力明显、或需要优先止盈止损的情形；写法要体现“若处于风险暴露中，应优先降低风险”，不要假装知道用户一定持仓。
6. 任何积极建议都必须同时写清催化因素、入场方式和失效条件。
7. 不允许出现“偏积极但仍建议继续观望”这类自相矛盾表述。
8. “截面价格”优先引用市场报告中最明确的当前价格、最近收盘价或分析基准价，并用一句话说明取值依据。

请不要输出英文标题，也不要输出英文建议行动。最终结果必须完全使用中文。{get_language_instruction()}"""
        response = llm.invoke(prompt)
        content = getattr(response, "content", "") or ""
        return {
            "investment_plan": content,
            "final_trade_decision": content,
        }

    return decision_manager_node
