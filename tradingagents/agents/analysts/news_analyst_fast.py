from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any

from langchain_core.messages import AIMessage

from tradingagents.agents.utils.agent_utils import (
    build_instrument_context,
    get_global_news,
    get_language_instruction,
    get_news,
)

_NEWS_LOOKBACK_DAYS = 7
_COMPANY_NEWS_MAX_LINES = 60
_GLOBAL_NEWS_MAX_LINES = 40
_SECTION_MAX_CHARS = 12000


def _parse_trade_date(value: str) -> date:
    raw = (value or "").strip()
    for fmt in ("%Y-%m-%d", "%Y%m%d"):
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Unsupported trade_date format: {value!r}")


def _trim_multiline_text(text: str, *, max_lines: int, max_chars: int) -> str:
    normalized = (text or "").strip()
    if not normalized:
        return "No data available."
    lines = normalized.splitlines()
    trimmed_lines = lines[:max_lines]
    trimmed = "\n".join(trimmed_lines)
    if len(trimmed) > max_chars:
        trimmed = trimmed[:max_chars].rstrip()
    if len(lines) > max_lines or len(normalized) > len(trimmed):
        trimmed += "\n... [truncated]"
    return trimmed


def create_news_analyst_fast(llm: Any):
    def news_analyst_fast_node(state):
        trade_date = state["trade_date"]
        instrument = state["company_of_interest"]
        instrument_context = build_instrument_context(instrument)
        trade_day = _parse_trade_date(trade_date)
        normalized_trade_date = trade_day.isoformat()
        start_date = (trade_day - timedelta(days=_NEWS_LOOKBACK_DAYS)).isoformat()

        company_news_raw = get_news.invoke(
            {
                "ticker": instrument,
                "start_date": start_date,
                "end_date": normalized_trade_date,
            }
        )
        global_news_raw = get_global_news.invoke(
            {
                "curr_date": normalized_trade_date,
                "look_back_days": _NEWS_LOOKBACK_DAYS,
                "limit": 8,
            }
        )

        company_news = _trim_multiline_text(
            company_news_raw,
            max_lines=_COMPANY_NEWS_MAX_LINES,
            max_chars=_SECTION_MAX_CHARS,
        )
        global_news = _trim_multiline_text(
            global_news_raw,
            max_lines=_GLOBAL_NEWS_MAX_LINES,
            max_chars=_SECTION_MAX_CHARS,
        )

        prompt = f"""你是一名高效率但经验扎实的新闻分析师，服务于轻量级交易分析团队。

你的任务是基于已经准备好的公司相关新闻和宏观/市场新闻，直接产出一份可用于投资决策的完整新闻分析报告。

请尽量对齐标准 News Analyst 的报告风格和质量目标：
- 不是简单摘要，也不是几条 bullet；
- 要像一份正式研究报告，结构完整、逻辑清晰、信息密度高；
- 但要避免为了追求全面而无限展开，聚焦“最近一周最重要、最影响交易判断的新闻”。

硬性要求：
1. 只基于下面提供的数据分析，不要要求额外工具，不要继续取数。
2. 不要编造未提供的事实；如果某部分信息不足，可以明确说明信息有限。
3. 重点覆盖：公司层面关键事件、行业/板块趋势、宏观环境、潜在催化剂、风险因素、交易含义。
4. 尽量保留事件发生的时间、来源、方向性影响和逻辑链条，不要只写空泛结论。
5. 用中文输出，篇幅请接近一份“轻量但完整”的分析报告，而不是短评。
6. 结尾必须附 Markdown 表格，用于整理关键新闻、市场影响和跟踪点。
7. 如果公司新闻和宏观新闻出现冲突，要明确指出冲突点，并给出你认为更重要的主导因素。
8. 输出应有章节、有展开、有总结，而非只列信息。
9. 版式上请多使用短段落、小节、编号列表与 bullet，不要把分析压缩成少数长段。
10. 报告要具备可读性和疏朗感；宁可拆成更多短行，也不要写成长块文字。
11. 公司层面关键新闻、行业趋势、宏观环境、风险提示、交易建议等部分，优先采用“总述 + 3-5 条分点展开”的写法。
12. 凡是涉及事件、时间、涨跌幅、来源或影响路径，尽量单独成条，并补一句“为什么重要”。

请按以下结构输出，标题可以自然微调，但整体结构尽量保持一致：

# {instrument} 新闻与宏观环境分析报告

## 一、核心结论摘要
- 先用 1-2 段总结最近一周最重要的新闻主线、对股价/交易判断的主要影响，以及总体偏多、偏空或中性的判断。
- 这部分也不要只写一个超长段，尽量拆成 2 段以内的短段。

## 二、公司层面关键新闻梳理
- 提炼最重要的公司相关新闻或与公司直接相关的市场叙事。
- 说明每条新闻为什么重要，以及它更偏向基本面改善、预期改善、情绪催化，还是短期噪音。
- 尽量按 `1.` `2.` `3.` 列点，每条下面补 1-2 句解释。

## 三、行业与主题趋势分析
- 分析公司所在行业、概念板块、竞争格局或主题交易方向。
- 说明行业新闻如何影响市场对公司的估值与预期。
- 尽量拆成 2-4 条主题，而不是一整段写完。

## 四、宏观环境与市场情绪
- 结合宏观/全球市场新闻，说明风险偏好、流动性、政策、商品价格或市场波动对该标的的潜在影响。
- 如果宏观信息有限，也要单独写出“信息局限说明”，保持和正文分段。

## 五、催化剂与风险提示

### 积极催化剂
### 主要风险因素
- 这两节都尽量列 3-5 条，不要只写成两个短段。

## 六、交易建议与观察重点
- 分别从短期交易、中期跟踪、已经持仓投资者三个角度给出建议。
- 每个视角尽量单独成条。

## 七、关键新闻汇总表
- 必须输出 Markdown 表格。
- 优先使用以下列：
  `类别 | 事件/主题 | 时间/时间窗 | 影响方向 | 影响逻辑 | 需要继续跟踪的点`

## 结论
- 用 1 段话收束全文，明确你对新闻面和市场叙事的总体判断。

**关键观察日期：**
- 用 1 句话说明未来 1-2 周最值得盯的事件、数据点或舆情变化。

**风险提示：**
- 用 1 句话提醒新闻分析的边界与交易纪律。

额外格式要求：
- 多用编号条目和 bullet，减少超长段落。
- 如果一节内出现多个观点，请拆分成多条，而不是用分号串联。

当前分析日期：{normalized_trade_date}
{instrument_context}

公司相关新闻（近一周，已裁剪）：
{company_news}

宏观/全球市场新闻（近一周，已裁剪）：
{global_news}

请直接给出最终新闻分析报告，保证结构完整、内容扎实、篇幅充分，并尽量贴近标准版 News Analyst 报告的完成度。{get_language_instruction()}"""

        response = llm.invoke(prompt)
        content = getattr(response, "content", "") or ""
        message = AIMessage(content=content)
        return {
            "messages": [message],
            "news_report": content,
        }

    return news_analyst_fast_node
