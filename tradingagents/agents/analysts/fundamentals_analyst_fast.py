from __future__ import annotations

from datetime import date, datetime
from typing import Any

from langchain_core.messages import AIMessage

from tradingagents.agents.utils.agent_utils import (
    build_instrument_context,
    get_balance_sheet,
    get_cashflow,
    get_fundamentals,
    get_income_statement,
    get_language_instruction,
)

_FUNDAMENTALS_MAX_CHARS = 6000
_STATEMENT_MAX_LINES = 35
_STATEMENT_MAX_CHARS = 6000


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


def create_fundamentals_analyst_fast(llm: Any):
    def fundamentals_analyst_fast_node(state):
        trade_date = state["trade_date"]
        instrument = state["company_of_interest"]
        instrument_context = build_instrument_context(instrument)
        normalized_trade_date = _parse_trade_date(trade_date).isoformat()

        fundamentals_raw = get_fundamentals.invoke(
            {
                "ticker": instrument,
                "curr_date": normalized_trade_date,
            }
        )
        balance_sheet_raw = get_balance_sheet.invoke(
            {
                "ticker": instrument,
                "freq": "quarterly",
                "curr_date": normalized_trade_date,
            }
        )
        cashflow_raw = get_cashflow.invoke(
            {
                "ticker": instrument,
                "freq": "quarterly",
                "curr_date": normalized_trade_date,
            }
        )
        income_statement_raw = get_income_statement.invoke(
            {
                "ticker": instrument,
                "freq": "quarterly",
                "curr_date": normalized_trade_date,
            }
        )

        fundamentals = _trim_multiline_text(
            fundamentals_raw,
            max_lines=80,
            max_chars=_FUNDAMENTALS_MAX_CHARS,
        )
        balance_sheet = _trim_multiline_text(
            balance_sheet_raw,
            max_lines=_STATEMENT_MAX_LINES,
            max_chars=_STATEMENT_MAX_CHARS,
        )
        cashflow = _trim_multiline_text(
            cashflow_raw,
            max_lines=_STATEMENT_MAX_LINES,
            max_chars=_STATEMENT_MAX_CHARS,
        )
        income_statement = _trim_multiline_text(
            income_statement_raw,
            max_lines=_STATEMENT_MAX_LINES,
            max_chars=_STATEMENT_MAX_CHARS,
        )

        prompt = f"""你是一名高效率但经验扎实的基本面分析师，服务于轻量级交易分析团队。

你的任务是基于已经准备好的公司基础信息、资产负债表、现金流量表和利润表数据，直接产出一份可用于投资决策的完整基本面分析报告。

请尽量对齐标准 Fundamentals Analyst 的报告风格和质量目标：
- 保持完整研究报告的结构感和展开深度；
- 要有关键数字、同比/环比或阶段变化、财务结构解释、风险和投资含义；
- 但不要为了“极致全面”再次要求更多工具或多轮补数。

硬性要求：
1. 只基于下面提供的数据分析，不要要求更多工具，不要继续取数。
2. 尽量像原版 Fundamentals Analyst 一样写“完整报告”，而不是短摘要。
3. 报告应有公司概况、财务分析、关键比率、业务评估、投资建议、表格、结论。
4. 必须尽量引用具体数字、增减变化、财务结构特征，不要只写抽象判断。
5. 如果数据存在缺口、市场不适用或口径差异，要在文中说明，不要硬编。
6. 对盈利能力、现金流、偿债能力、成长性和财务风险都要覆盖。
7. 结尾必须附 Markdown 表格，整理关键指标和趋势判断。
8. 用中文输出，篇幅请接近“轻量但完整”的基本面研究报告。
9. 报告版式多使用短段落、小标题、编号条目和 bullet，不要把大量内容压缩进少数长段。
10. 除“结论”外，正文大多数章节都应拆成多条要点来写；优先使用：
   - 一个总括句
   - 随后 3-6 条分点展开
11. 行文密度目标上，宁可拆成更多短行，也不要写成长段大块文字。
12. 在财务分析部分，凡是出现重要数字，尽量单独成条列出，并补一句“这意味着什么”。
13. 请明显增加换行频率：每个编号条目、每个关键数字解释、每个小结论尽量单独成段。
14. 目标不是缩写成投研摘要，而是写成“轻量完整版报告”；如果同一段超过 3 行，请优先拆开。
15. 请尽量让全文形成更丰富的段落层次，尤其是财务分析、积极因素、风险因素、交易建议几节。

请按以下结构输出，标题名称可自然调整，但结构尽量保持一致：

# {instrument} 基本面分析报告

## 公司概况
- 简要介绍公司定位、核心业务、产品/服务、市场覆盖、竞争地位或经营特点。
- 若部分信息不足，可基于现有数据做谨慎概括。

## 财务分析

### 资产负债表分析
- 重点分析资产结构、负债结构、权益变化、现金储备、应收应付、杠杆与偿债压力。
- 这一节尽量采用“总述 + 关键资产项目 + 关键负债项目 + 权益/偿债结论”的拆分写法。
- 关键资产项目、关键负债项目尽量分别列 3-5 条。
- 在“关键资产项目”和“关键负债项目”下，尽量使用：
  `1. 项目名：数值`
  下一行单独解释该项目意味着什么。

### 现金流量表分析
- 重点分析经营现金流、投资现金流、融资现金流和现金净变动。
- 明确公司是在“自我造血”还是“依赖融资/资产处置/外部输血”。
- 经营/投资/融资/现金净变动最好分成独立小段或条目逐项写清。
- 每一类现金流后面单独补一行“这意味着什么”。

### 利润表分析
- 重点分析收入增长、毛利率、费用结构、营业利润/净利润变化、每股盈利或亏损情况。
- 如果公司处于高投入阶段，要解释这种模式意味着什么。
- 收入表现、盈利能力、费用结构、亏损状况尽量分别成段或成条。
- “费用结构”建议拆成研发费用、销售费用、行政费用等独立条目逐条解释。

## 关键财务比率分析
- 至少覆盖流动性、杠杆、盈利能力、营运效率或成长性中的关键指标。
- 尽量按编号条目输出，每个比率单独一行，并补充解释。
- 每个比率尽量写成两行：
  第一行写数值，
  第二行写含义。

## 业务发展评估

### 积极因素
### 风险因素
- 这两节都不要只写 1 段，尽量各列 3-5 条。
- 每一条积极因素/风险因素尽量单独占 2-3 行，先写结论，再写展开。

## 投资建议与风险提示

### 投资亮点
### 主要风险
### 交易建议
- “交易建议”，明确适合/不适合的投资者类型或持仓建议。
- “交易建议”优先拆成：
  - 适合的投资者类型
  - 不适合的投资者类型
  - 持仓/建仓建议

## 关键指标汇总表
- 必须输出 Markdown 表格。
- 表格优先使用：
  `指标类别 | 当前/最新值 | 对比期值 | 趋势分析 | 说明`
- 尽量覆盖收入、毛利率、研发/销售/行政费用、净利润、现金流、资产负债、流动性或杠杆等核心指标。

## 结论
- 用 1 段话收束全文，明确你对公司基本面的总体判断。

如能形成明确倾向，请在结尾附一行：
`FINAL TRANSACTION PROPOSAL: BUY/HOLD/SELL`
如果证据不足，也请给出最谨慎的方向性倾向并解释原因。

额外格式要求：
- 标题与子标题之间适当留空行，增强可读性。
- 多用 `1.` `2.` `3.` 或 `-` 拆分论点。
- 不要把“资产负债表分析”“现金流量表分析”“利润表分析”各自压缩成单个长段。
- 如果数据点很多，优先改成分项列示，而不是写成长句串联。
- 除表格外，尽量避免出现连续的大段正文。

当前分析日期：{normalized_trade_date}
{instrument_context}

公司基础信息（已裁剪）：
{fundamentals}

资产负债表（已裁剪）：
{balance_sheet}

现金流量表（已裁剪）：
{cashflow}

利润表（已裁剪）：
{income_statement}

请直接给出最终基本面分析报告，保证结构完整、数字充分、分析扎实，并尽量贴近标准版 Fundamentals Analyst 报告和 SOTA 样例的完成度。{get_language_instruction()}"""

        response = llm.invoke(prompt)
        content = getattr(response, "content", "") or ""
        message = AIMessage(content=content)
        return {
            "messages": [message],
            "fundamentals_report": content,
        }

    return fundamentals_analyst_fast_node
