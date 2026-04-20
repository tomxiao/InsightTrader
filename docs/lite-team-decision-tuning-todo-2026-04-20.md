# Lite Team Decision Tuning TODO

## 背景

本轮工作围绕 `InsightTrader lite team` 的 `decision manager` 与 `backtest` 展开，目标是解决：

- 下行区间里仍持续给出 `择机买入` 的动作惰性
- 回测批量生成历史报告默认继续使用 `deepseek-chat`
- `deepseek-reasoner` 输出格式与 `backtest` parser 的兼容性

核心样本标的是 `AXTI`，重点观察区间为：

- `2026-03-02 ~ 2026-04-07`

对应最新批次目录：

- `backtest/output/0420-0111-AXTI/`

## 今日已完成

### 1. backtest 历史报告生成默认模型确定为 `deepseek-chat`

已修改：

- `backtest/generate_report_batch.py`
- `ta_service/adapters/tradingagents_runner.py`
- `tradingagents/llm_clients/model_catalog.py`
- `backtest/README.md`
- `.codex/skills/report-backtest/SKILL.md`

当前行为：

- `generate_report_batch.py` 默认使用 `deepseek-chat`
- 仅影响 backtest 历史报告生成链路
- 不影响全局默认分析模型

### 2. 修复 `deepseek-reasoner` 输出与 backtest parser 的兼容性

已修改：

- `backtest/report_parser.py`
- `tests/test_backtest_report_parser.py`

已兼容的新格式包括：

- `**分析日期：** 2026-03-03`
- `**1. 分析日期：** 2026-03-23`
- `**建议行动：** 建议卖出`
- `**建议行动：** **建议卖出**`
- `**截面价格：** 46.32 美元`

### 3. 调整 `decision manager` 的动作语义

已修改：

- `tradingagents/agents/managers/decision_manager.py`

当前原则：

- 方向偏多时，建议行动默认假设用户无持仓
- 方向偏空时，建议行动默认假设用户已有持仓
- 方向不明或证据冲突时，优先 `保持观望`
- 如果正文已经是“仅博弈反弹 / 需要等待企稳 / 暂不适合直接买入”，默认不应继续落到 `择机买入`

## 今日关键回测结果

### A. 旧版本 lite team（偏买入惯性）

较早一版 `AXTI` 日频回测结果曾表现为：

- 大量 `buy_on_pullback`
- 在 `2026-03-25 ~ 2026-04-07` 明显下行区间里，仍持续给出 `择机买入`

问题定义：

- 对下行风险识别不够快
- 动作层对“风险主导”反应迟缓

### B. `deepseek-chat` 默认链路 + 新 decision manager

最新批次：

- `backtest/output/0420-0111-AXTI/`

回测结果：

- `signal_count = 26`
- `trade_count = 0`
- `triggered_trade_count = 0`
- `by_action.hold.signal_count = 21`
- `by_action.sell.signal_count = 5`

结论：

- 下行区间里“持续择机买入”的问题基本被纠正
- 但同时几乎完全错过了 `2026-03-09 ~ 2026-03-24` 这一段上涨周期

补充说明：

- 当前 backtest 默认模型已明确维持为 `deepseek-chat`
- `deepseek-reasoner` 相关内容主要用于记录 parser 兼容性验证，不作为默认运行口径

## 当前判断

现在系统从“过度偏多”切到了“过度保守”。

不是原则错，而是当前动作规则仍然过粗，把两类情况混在了一起：

1. 上涨趋势中的高风险阶段
2. 下跌/破位后的风险主导阶段

这两类情况都被大量压成了 `保持观望`，导致：

- 修复了 `3.25 ~ 4.07` 的惰性买入
- 但错杀了 `3.09 ~ 3.24` 的趋势延续机会

## 明天继续调整的方向

### 方向一：先分“趋势状态”，再决定动作

建议把 `decision manager` 的内部判断显式收敛到三态：

- 趋势延续
- 震荡等待确认
- 风险主导 / 破位下行

再映射动作：

- 趋势延续 -> `确信买入 / 择机买入`
- 震荡等待确认 -> `保持观望`
- 风险主导 / 破位下行 -> `建议卖出`

### 方向二：重新审视 `择机买入` 的边界

当前 `择机买入` 被压得太窄，明天要重点讨论：

- “上涨中的高风险但仍属趋势延续”是否应恢复为 `择机买入`
- “仅博弈反弹”是否仍然应保持 `保持观望`

需要把这两类情况明确拆开。

### 方向三：重点复盘 `AXTI 2026-03-09 ~ 2026-03-24`

需要逐日查看该区间新报告，确认：

- 哪些日期本应属于“趋势延续中的择机参与”
- 哪些日期已经应降级为“保持观望”

### 方向四：暂不改 3 个 analyst 的实现

当前决定：

- `market/news/fundamentals` 上游实现先不动
- 先继续只调 `decision manager`

理由：

- 上游材料总体足够
- 当前主要问题仍在最终动作收敛

## 明天的建议执行顺序

1. 逐日检查 `0420-0111-AXTI/reports/` 中 `2026-03-09 ~ 2026-03-24` 的 `summary.md`
2. 标记哪些日期应该是 `择机买入`，哪些应该是 `保持观望`
3. 微调 `decision_manager.py` prompt
4. 重新批量生成 `AXTI 2026-03-02 ~ 2026-04-07` 日频报告
5. 重新跑 backtest
6. 比较：
   - 下行区间是否继续保持 `hold/sell`
   - 上涨区间是否恢复适量的 `buy_on_pullback`

## 当前文件状态

已修改但明天仍需继续观察的核心文件：

- `tradingagents/agents/managers/decision_manager.py`
- `backtest/report_parser.py`
- `backtest/generate_report_batch.py`
- `ta_service/adapters/tradingagents_runner.py`
- `tradingagents/llm_clients/model_catalog.py`

## 备注

最新 parser、backtest 相关测试通过：

- `17 passed`

但 `AXTI` 的决策风格仍未达到目标状态，明天的重点不是修基础设施，而是继续收敛 `decision manager` 的动作边界。
