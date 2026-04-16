# Lite Team 慢 Agent 分析 TODO

## 背景

在 `lite team` 已完成 analyst 并行化后，整体时延的主要瓶颈已经从 `Market Analyst` 转移到：

- `News Analyst`
- `Fundamentals Analyst`

本文件记录这两个 agent 在真实运行中的慢点、证据、根因判断，以及后续优化 TODO，避免后续重复排查。

## 样本

重点分析样本：

- [AAPL_2026_0417_0240](D:/CodeBase/InsightTrader/results/analysis/AAPL_2026_0417_0240)

该轮 `lite` 4 个 agent 耗时：

- `Market Analyst`: `65.69s`
- `News Analyst`: `141.03s`
- `Fundamentals Analyst`: `213.44s`
- `Decision Manager`: `18.36s`

对应可参考文件：

- [stage_events.jsonl](D:/CodeBase/InsightTrader/results/analysis/AAPL_2026_0417_0240/stage_events.jsonl)
- [node_events.jsonl](D:/CodeBase/InsightTrader/results/analysis/AAPL_2026_0417_0240/node_events.jsonl)
- [llm_events.jsonl](D:/CodeBase/InsightTrader/results/analysis/AAPL_2026_0417_0240/llm_events.jsonl)

## Fundamentals Analyst

### 现象

`Fundamentals Analyst` 总耗时 `213.44s`，是当前 `lite team` 最大瓶颈。

### 运行特征

从 [node_events.jsonl](D:/CodeBase/InsightTrader/results/analysis/AAPL_2026_0417_0240/node_events.jsonl) 看，基本面路径不是“一次取数 + 一次成文”，而是多轮循环：

- `Fundamentals Analyst`
- `tools_fundamentals`
- `Fundamentals Analyst`
- `tools_fundamentals`
- `Fundamentals Analyst`
- `tools_fundamentals`
- `Fundamentals Analyst`
- `tools_fundamentals`
- `Fundamentals Analyst`

其中长轮主要集中在：

- 第一轮 `Fundamentals Analyst`: 约 `65.68s`
- 第三轮 `Fundamentals Analyst`: 约 `62.61s`
- 第五轮 `Fundamentals Analyst`: 约 `63.88s`

工具节点本身并不慢：

- `tools_fundamentals`: 约 `2.07s`
- `tools_fundamentals`: 约 `2.85s`
- `tools_fundamentals`: 约 `0s`
- `tools_fundamentals`: 约 `1.38s`

### 关键证据

从 [llm_events.jsonl](D:/CodeBase/InsightTrader/results/analysis/AAPL_2026_0417_0240/llm_events.jsonl) 看，`Fundamentals Analyst` 的输入体积快速膨胀：

- `1888`
- `3549`
- `26297`
- `52796`
- `81446`

说明它在不断把前几轮拉回来的财报、现金流、利润表等内容继续滚入上下文，再重新让模型读一遍。

### 根因判断

根因不是财务工具慢，而是以下几件事叠加：

1. `fundamentals_analyst.py` 的 prompt 明确要求“尽可能详细、全面、包含大量细节”
2. 工具有 4 个：
   - `get_fundamentals`
   - `get_balance_sheet`
   - `get_cashflow`
   - `get_income_statement`
3. 当前图执行允许它多轮补工具，没有硬性的轮数/字符上限
4. 每次补回来的长报表内容都会继续滚入下一轮 prompt

一句话概括：

`Fundamentals Analyst` 慢，核心是“多轮取财报 + 超长上下文重读 + 详细长报告生成”，不是数据源慢。

### TODO

- 为 `lite team` 设计 `Fundamentals Analyst Fast`
- 限制工具轮数，默认不超过 `1-2` 轮
- 限制进入 LLM 的财务原文字符数
- 优先做“财务摘要 -> 分析”，而不是“三大报表全文 -> 多轮重写”
- 明确 `lite` 基本面报告的最小必要结构，避免默认追求完整研究报告

## News Analyst

### 现象

`News Analyst` 总耗时 `141.03s`，是当前 `lite team` 第二大瓶颈。

### 运行特征

从 [node_events.jsonl](D:/CodeBase/InsightTrader/results/analysis/AAPL_2026_0417_0240/node_events.jsonl) 看，新闻路径也不是一次完成，而是多轮循环：

- `News Analyst`
- `tools_news`
- `News Analyst`
- `tools_news`
- `News Analyst`

其中 `News Analyst` 的主要轮次大约为：

- `4.23s`
- `4.25s`
- `5.05s`

工具节点本身并不慢：

- 一次 `tools_news`: `0s`
- 一次 `tools_news`: `2.80s`

### 关键证据

从 [llm_events.jsonl](D:/CodeBase/InsightTrader/results/analysis/AAPL_2026_0417_0240/llm_events.jsonl) 看，`News Analyst` 的输入体积膨胀更夸张：

- `1651`
- `13737`
- `106500`
- `113324`

说明新闻工具一旦返回较长新闻文本，后续 LLM 轮次会反复吞掉巨量上下文。

### 根因判断

根因同样不是新闻工具慢，而是：

1. `news_analyst.py` 的 prompt 默认要求综合写完整新闻/宏观报告
2. 工具返回的新闻正文天然较长
3. 多轮循环会把原始长新闻继续滚入上下文
4. 当前没有对新闻条数、新闻字符数、工具轮数做强限制

一句话概括：

`News Analyst` 慢，核心是“新闻原文太长 + 多轮循环 + 上下文爆炸”，不是抓新闻本身慢。

### TODO

- 为 `lite team` 设计 `News Analyst Fast`
- 限制新闻工具轮数
- 限制单轮新闻条数与单条新闻字符数
- 优先把新闻压缩成摘要后再进入成文 LLM
- 将 `lite` 新闻报告改成“关键事件摘要 + 市场影响 + 风险提示”结构

## 对比结论

两者属于同类问题，但侧重点不同：

- `Fundamentals Analyst`
  - 慢在多份财务资料反复进入上下文
  - 更像“多报表 + 多轮重写”

- `News Analyst`
  - 慢在新闻正文过长导致上下文爆炸
  - 更像“长新闻文本 + 多轮归纳”

共同点：

- 都不是工具慢
- 都是 LLM 多轮循环 + 输入持续膨胀
- 都不适合直接沿用 `full team` 的“详细研究报告”思路

## 后续建议顺序

建议优化顺序：

1. 先做 `Fundamentals Analyst Fast`
2. 再做 `News Analyst Fast`
3. 最后再考虑是否需要对 `Decision Manager` 做更轻量的收口

原因：

- `Fundamentals Analyst` 是当前最长路径
- 它对整体耗时的改善空间最大
- `News Analyst` 次之
