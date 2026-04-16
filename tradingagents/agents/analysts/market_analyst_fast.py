from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any

from langchain_core.messages import AIMessage

from tradingagents.agents.utils.agent_utils import (
    build_instrument_context,
    get_language_instruction,
    get_indicators,
    get_stock_data,
)

_FAST_MARKET_INDICATORS = [
    "close_10_ema",
    "close_50_sma",
    "close_200_sma",
    "macd",
    "rsi",
    "boll_ub",
    "boll_lb",
    "atr",
]


def _parse_trade_date(value: str) -> date:
    raw = (value or "").strip()
    for fmt in ("%Y-%m-%d", "%Y%m%d"):
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Unsupported trade_date format: {value!r}")


def create_market_analyst_fast(llm: Any):
    def market_analyst_fast_node(state):
        trade_date = state["trade_date"]
        instrument = state["company_of_interest"]
        instrument_context = build_instrument_context(instrument)
        trade_day = _parse_trade_date(trade_date)
        normalized_trade_date = trade_day.isoformat()

        end_date = trade_day - timedelta(days=1)
        start_date = end_date - timedelta(days=29)
        stock_data = get_stock_data.invoke(
            {
                "symbol": instrument,
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
            }
        )
        indicators = get_indicators.invoke(
            {
                "symbol": instrument,
                "indicator": ",".join(_FAST_MARKET_INDICATORS),
                "curr_date": normalized_trade_date,
                "look_back_days": 30,
            }
        )

        prompt = f"""你是一名高效率但经验扎实的市场技术分析师，服务于轻量级交易分析团队。

你的任务是基于已经准备好的价格数据和核心技术指标，直接产出一份可用于最终投资决策的市场报告。

请尽量对齐标准 Market Analyst 的报告风格：结构完整、层次清晰、论据扎实、结论明确。你可以比完整版略收敛，但不要写成轻飘飘的 memo，也不要只输出短要点。

硬性要求：
1. 只基于下面提供的数据分析，不要要求更多工具，也不要假设缺失数据。
2. 不要重复调用工具，不要说“还需要更多数据”。
3. 必须保留关键数字和趋势演变，不要只给结论。
4. 重点覆盖：长期/中期/短期趋势、动量、波动、关键支撑阻力、风险提示、交易建议。
5. 用中文输出，并尽量遵循下面的报告版式与标题层级。
6. 每个主要分析段落都要引用具体数字、价位、斜率变化或区间变化，避免空泛描述。
7. 风格上尽量贴近传统技术分析报告：先摘要，再展开分章节分析，最后给表格和综合评估。
8. 结尾必须附 Markdown 表格，整理关键技术指标与信号。

请按以下结构输出，标题名称尽量保持一致：

# {instrument}（若已知名称可补全名称）技术分析报告

## 执行摘要
- 用 1 段话概述趋势、动量、风险和核心建议。

## 详细技术分析

### 1. 趋势分析
- 分别分析长期趋势（200日SMA）、中期趋势（50日SMA）、短期趋势（10日EMA）。
- 说明当前价格相对各均线的位置、偏离程度和趋势含义。

### 2. 动量分析
- 重点分析 MACD 与 RSI。
- 说明它们的最新状态、近期演变，以及对后续走势意味着什么。

### 3. 波动率与价格通道分析
- 重点分析布林带与 ATR。
- 说明波动率扩张/收敛、价格是否贴近或突破通道边界。

### 4. 关键价格水平
- 明确列出支撑位与阻力位。
- 每个价位都要解释来源和意义。

### 5. 成交与结构观察
- 如果价格数据里能看出量价配合、加速上涨、冲高回落、放量突破等现象，请单独总结。
- 若成交信息有限，也要基于已有价格结构给出简洁判断。

## 风险提示与交易建议

### 积极因素
### 风险因素
### 交易策略建议

- “交易策略建议”里尽量分别覆盖持仓者、潜在买入者、短线交易者。

## 技术指标汇总表
- 必须输出 Markdown 表格。
- 表格列尽量对齐标准版，优先使用：
  `指标类别 | 指标名称 | 当前值 | 趋势方向 | 信号强度 | 关键观察点`
- 表格至少包含：价格、200日SMA、50日SMA、10日EMA、MACD、RSI、布林带上轨/下轨、ATR、关键支撑/阻力。

## 结论
- 用 1 段话收束全文，给出整体技术面判断和操作倾向。

**关键观察日期：**
- 用 1 句话说明未来 1-2 周最值得跟踪的价位、突破或回调观察点。

**风险提示：**
- 用 1 句话提醒技术分析的适用边界和仓位/止损纪律。

当前分析日期：{normalized_trade_date}
{instrument_context}

价格数据：
{stock_data}

核心技术指标：
{indicators}

请直接给出最终市场技术分析报告，注意格式尽量向标准版 Market Analyst 报告靠拢，尤其是表格字段和结尾的“结论 / 关键观察日期 / 风险提示”写法。{get_language_instruction()}"""

        response = llm.invoke(prompt)
        content = getattr(response, "content", "") or ""
        message = AIMessage(content=content)
        return {
            "messages": [message],
            "market_report": content,
        }

    return market_analyst_fast_node
