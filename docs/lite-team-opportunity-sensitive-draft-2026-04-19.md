# Lite Team 进取化改造草案（2026-04-19）

## 1. 文档信息

- 文档名称：`Lite Team 进取化改造草案`
- 版本：`draft v0.1`
- 当前方案：只改 `lite team`，不改 `full team`
- 文档类型：产品与工程联合草案
- 面向对象：产品、后端、Prompt、测试
- 适用范围：`lite team` 的 analyst prompt、`Decision Manager` 收口逻辑、`lite` 最终输出结构

## 2. 背景与问题定义

### 2.1 当前基础能力

当前 `lite team` 已具备一条轻量分析链路：

- `market`
- `news`
- `fundamentals`
- `Decision Manager`

对应图编排位于：

- [D:/CodeBase/InsightTrader/tradingagents/graph/lite_trading_graph.py](D:/CodeBase/InsightTrader/tradingagents/graph/lite_trading_graph.py:180)

对应核心 agent 位于：

- [D:/CodeBase/InsightTrader/tradingagents/agents/analysts/market_analyst_fast.py](D:/CodeBase/InsightTrader/tradingagents/agents/analysts/market_analyst_fast.py:24)
- [D:/CodeBase/InsightTrader/tradingagents/agents/analysts/news_analyst_fast.py](D:/CodeBase/InsightTrader/tradingagents/agents/analysts/news_analyst_fast.py:39)
- [D:/CodeBase/InsightTrader/tradingagents/agents/analysts/fundamentals_analyst_fast.py](D:/CodeBase/InsightTrader/tradingagents/agents/analysts/fundamentals_analyst_fast.py:39)
- [D:/CodeBase/InsightTrader/tradingagents/agents/managers/decision_manager.py](D:/CodeBase/InsightTrader/tradingagents/agents/managers/decision_manager.py:9)

### 2.2 当前问题

从当前 `reports` 样本和代码实现看，`lite team` 的最终结论仍整体偏保守。

主要表现为：

- 在“逻辑成立但证据不完美”的情况下，结论容易退回模糊保守结论
- 缺少“可参与但需控制仓位”的中间行动建议
- analyst 报告更像“轻量版研究报告”，而不是“机会发现输入”
- 最终输出缺少明确的 `1-3 个月` 机会表达、进入方式和失效条件

### 2.3 根因判断

根因主要有三点：

1. [decision_manager.py](D:/CodeBase/InsightTrader/tradingagents/agents/managers/decision_manager.py:9) 传统 `买入 / 增持 / 持有 / 减持 / 卖出` 这类评级口径不适合当前 `lite team`，既缺少中间动作层，也容易暗含仓位假设。
2. `Decision Manager` 当前更像“证据审查器”，没有被要求判断“未来 1-3 个月是否值得试”。
3. 三个 fast analyst prompt 虽然完整，但没有被强制回答“如果要参与，最值得参与的理由、方式和边界是什么”。

### 2.4 本次改版定位

本次改版不是把 `lite team` 改成激进系统。

本次改版要把 `lite team` 改成：

**有纪律的机会发现器。**

也就是：

- 对机会更敏感
- 愿意明确表达可参与机会
- 但每个积极结论都必须带清晰边界

## 3. 产品定位

`lite team` 的新定位是：

**面向 `1-3` 个月窗口的机会识别型分析团队，用较快速度给出更有进攻性的判断，但所有积极建议都必须附带明确的进入条件、失效条件和风险边界。**

本版本强调的不是“更乐观”，而是：

- 更愿意给出 `可参与` 判断
- 更愿意识别催化驱动和预期差
- 但不允许无边界地喊 `买入`

## 4. 目标与非目标

### 4.1 产品目标

- 让 `lite team` 对 `1-3` 个月交易机会更敏感
- 降低“本应是试探性机会，却被压成模糊保守结论”的情况
- 让 `lite team` 的结论更适合短中期交易判断
- 保留 `lite team` 的轻量路径，不引入 `full team` 风格的多轮风险辩论
- 让最终结论天然带有进入方式、观察窗口和失效边界

### 4.2 非目标

- 不修改 `full team` 的 graph、prompt、评级体系或输出口径
- 不引入 `bull/bear debate`、`risk debate` 或 `portfolio manager`
- 不在本版本讨论模拟盘联动、下单规则或 broker 对接
- 不要求本版本把 markdown 报告改造成严格 JSON API
- 不扩大 `lite team` 的工具范围或 graph 复杂度

## 5. 适用范围与影响范围

### 5.1 适用范围

本次只影响 `lite team` 下列模块：

- `Decision Manager`
- `Market Analyst Fast`
- `News Analyst Fast`
- `Fundamentals Analyst Fast`
- `lite team` 最终报告模板与字段约束

### 5.2 受影响文件

- [D:/CodeBase/InsightTrader/tradingagents/agents/managers/decision_manager.py](D:/CodeBase/InsightTrader/tradingagents/agents/managers/decision_manager.py:9)
- [D:/CodeBase/InsightTrader/tradingagents/agents/analysts/market_analyst_fast.py](D:/CodeBase/InsightTrader/tradingagents/agents/analysts/market_analyst_fast.py:24)
- [D:/CodeBase/InsightTrader/tradingagents/agents/analysts/news_analyst_fast.py](D:/CodeBase/InsightTrader/tradingagents/agents/analysts/news_analyst_fast.py:39)
- [D:/CodeBase/InsightTrader/tradingagents/agents/analysts/fundamentals_analyst_fast.py](D:/CodeBase/InsightTrader/tradingagents/agents/analysts/fundamentals_analyst_fast.py:39)

### 5.3 不受影响范围

- `full team` 全部代码与 prompt
- `lite_trading_graph.py` 的总体节点结构
- 数据工具与取数接口
- 前端展示逻辑
- 模拟盘、订单、风控执行链路

## 6. 角色与术语定义

- `lite team`：轻量分析链路，当前由 `market/news/fundamentals + Decision Manager` 构成。
- `机会敏感`：系统愿意在证据未达“高确信配置级别”时，识别并表达值得参与的上涨机会。
- `可控`：所有积极建议都必须带进入条件、失效条件、观察窗口和风险边界。
- `择机买入`：适合短中期参与、但不代表确信买入的积极行动。
- `保持观望`：多空证据冲突或方向不明，当前不给有效动作建议。

## 7. 需求原则

1. `lite team` 要优先判断赔率，而不是优先追求结论完美。
2. `lite team` 可以比 `full team` 更积极，但不能取消交易边界。
3. 所有积极建议都必须回答四个问题：
   - 为什么值得参与
   - 参与窗口是什么
   - 错了如何认错
   - 适合谁参与
4. analyst 报告不是单纯汇总信息，而是为最终“机会判断”提供输入。
5. 本版本优先改口径，不优先改 graph。
6. 不允许通过引入更多风险节点来“平衡”进取性，否则会重新把 `lite team` 拉回保守收口。

## 8. 功能需求总览

- `F1`：调整 `lite team` 最终建议行动体系
- `F2`：调整 `Decision Manager` 的决策问题定义
- `F3`：为三个 fast analyst 增加“机会表达”固定输出要求
- `F4`：统一 `lite team` 最终结论模板
- `F5`：定义改造后的验收标准

## 9. 详细功能需求

### F1. 调整最终建议行动体系

#### 需求目标

让 `lite team` 拥有表达“可参与但需克制”的能力，并把输出统一成不依赖真实持仓信息的“建议行动”。

#### 功能规则

`Decision Manager` 的最终输出改为四档建议行动：

- `确信买入`
- `择机买入`
- `保持观望`
- `建议卖出`

#### 建议行动定义

- `确信买入`
  表示多维度证据较充分，方向明确，当前就具备较强参与价值。
- `择机买入`
  表示存在值得参与的 `1-3` 个月机会，但更适合等待更优位置、回调或确认信号后参与。
- `保持观望`
  表示多空证据冲突、方向不明，或暂时无法给出有效参与建议。
- `建议卖出`
  表示风险占优、下行压力明显；若处于风险暴露中，应优先考虑止盈、止损或降低风险。

#### 边界约束

- `择机买入` 不能等同于 `确信买入`
- `保持观望` 不能写成空泛的“再看看”
- `建议卖出` 的写法不能假装系统知道用户一定持仓
- 所有 `买入` 类建议都必须附带明确条件

### F2. 调整 Decision Manager 的决策问题定义

#### 需求目标

把 `Decision Manager` 从“谨慎汇总器”改成“建议行动生成器”。

#### 功能规则

[decision_manager.py](D:/CodeBase/InsightTrader/tradingagents/agents/managers/decision_manager.py:9) 的 prompt 需要明确回答：

- 未来 `1-3` 个月是否存在值得参与的机会
- 该机会是确信买入、择机买入、保持观望，还是建议卖出
- 如果参与，最合理的参与方式是什么
- 哪些条件会让当前判断失效

#### 新的输出结构

最终输出必须严格包含以下部分：

1. `建议行动`
3. `1-3个月核心判断`
4. `执行摘要`
5. `关键催化因素`
6. `关键风险`
7. `入场方式`
8. `失效条件`
9. `适合的场景`
10. `不适合的场景`
11. `证据摘要`

#### 文案规则

- 不允许只给抽象判断，不给行动边界
- 不允许把“证据不完美”直接写成模糊保守结论
- 允许在证据不完整但赔率明显时给出 `择机买入`
- 不允许出现“偏积极但建议继续观察”这种自相矛盾表述

### F3. 调整 Market Analyst Fast

#### 需求目标

让技术分析不只解释走势，还要明确“有没有交易窗口”。

#### 功能规则

[market_analyst_fast.py](D:/CodeBase/InsightTrader/tradingagents/agents/analysts/market_analyst_fast.py:24) 在保留现有报告结构的基础上，新增以下固定输出要求：

- `未来1-3个月最关键的上涨触发条件`
- `最值得关注的入场区间`
- `走势失效条件`
- `更适合追涨、回调参与还是仅观察`

#### 输出原则

- 支撑、阻力、趋势和动量分析不能只停留在描述层
- 需要显式回答“若要参与，技术面最合理的参与方式是什么”
- 若技术面不支持参与，也要明确写出“不支持参与”的原因

### F4. 调整 News Analyst Fast

#### 需求目标

让新闻分析从“事件整理”升级为“催化识别”。

#### 功能规则

[news_analyst_fast.py](D:/CodeBase/InsightTrader/tradingagents/agents/analysts/news_analyst_fast.py:39) 在保留现有结构的基础上，新增以下固定输出要求：

- `未来1-3个月最可能推动重估的催化剂`
- `当前是否存在市场预期差`
- `哪些新闻属于噪音，哪些会改变定价`
- `如果要参与，更适合事件前、事件后确认，还是仅观察`

#### 输出原则

- 不只总结新闻内容，还要给出定价含义
- 催化剂和风险必须能支持最终建议行动分层
- 当公司新闻与宏观环境冲突时，需要给出主导因素判断

### F5. 调整 Fundamentals Analyst Fast

#### 需求目标

让基本面分析不仅揭示风险，也明确回答“上涨逻辑是否成立”。

#### 功能规则

[fundamentals_analyst_fast.py](D:/CodeBase/InsightTrader/tradingagents/agents/analysts/fundamentals_analyst_fast.py:39) 在保留现有报告结构的基础上，新增以下固定输出要求：

- `当前基本面是否支持未来1-3个月的估值修复或预期改善`
- `最强多头逻辑是什么`
- `最关键证伪点是什么`
- `更像长期配置标的，还是阶段性交易机会`

#### 输出原则

- 不能只罗列财务风险
- 要强制总结“当前基本面最值得下注的一面”
- 若不支持积极判断，也必须明确写出哪个核心链条不成立

### F6. 统一 lite team 最终结论模板

#### 需求目标

让所有 `lite team` 报告在最终结论处都具备稳定、可比、可复盘的结构。

#### 功能规则

无论上游 analyst 报告怎么展开，最终结论必须至少包含以下字段：

- `建议行动`
- `观察周期`
- `核心催化剂`
- `入场方式`
- `失效条件`
- `适合的场景`
- `不适合的场景`

#### 默认规则

- `观察周期` 默认聚焦 `1-3` 个月
- `入场方式` 可以是区间、条件或观察方式
- `失效条件` 必须是具体可理解的情形，不能只写“风险上升”

## 10. 页面与交互影响

本版本暂不要求新增页面或前端交互改动。

现阶段影响主要体现在报告内容与结论模板变化：

- `lite team` 最终摘要会更偏交易判断
- 报告中会出现更多“入场方式 / 失效条件 / 适合人群”的稳定字段

前端在本版本中只需继续按 markdown 报告渲染即可。

## 11. 后端能力要求

### 11.1 保持现有 graph 不变

[lite_trading_graph.py](D:/CodeBase/InsightTrader/tradingagents/graph/lite_trading_graph.py:180) 当前的：

- `market`
- `news`
- `fundamentals`
- `Decision Manager`

这条图结构在本版本保持不变。

### 11.2 改动范围集中在 prompt 和输出契约

后端本版本只需要支持：

- 更新 `Decision Manager` prompt
- 更新三个 fast analyst prompt
- 稳定 `lite team` 结论模板

### 11.3 不新增新的 agent 或 tool

本版本不增加：

- 新的辩论节点
- 新的风控节点
- 新的行情/新闻/财务工具

## 12. 前端能力要求

前端本版本不需要做专门适配。

但从兼容性角度，后续建议前端保留对下列字段的识别弹性：

- `建议行动`
- `观察周期`
- `入场方式`
- `失效条件`

即便短期内仍按 markdown 展示，这些字段也应尽量保持稳定命名，便于后续结构化升级。

## 13. 验收标准

### 13.1 功能验收

- `lite team` 最终建议行动已统一为四档
- `Decision Manager` 输出中固定包含：
  - `建议行动`
  - `1-3个月核心判断`
  - `入场方式`
  - `失效条件`
- 三个 fast analyst prompt 都已新增机会表达相关要求
- `lite_trading_graph.py` 结构未被改重
- `full team` 代码未修改

### 13.2 体验验收

- 同一批标的中，`lite team` 的结论相较旧版更容易出现 `择机买入`
- `lite team` 报告比旧版更明确回答“能不能参与、怎么参与、错了怎么办”
- 报告不应因为更进取而变成无条件喊多
- 结论语义清楚，不出现“偏多但仍建议继续观望”这类模糊收口

## 14. 风险与注意事项

- 如果只改建议行动名称，不改 prompt 任务定义，模型仍可能大量输出保守结论。
- 如果只强调进取，不强调边界，`lite team` 容易退化成情绪化推荐器。
- 如果 analyst 仍只写“完整报告”，不写“机会表达”，`Decision Manager` 很难稳定产出新口径。
- 如果 `保持观望` 的定义不清晰，最终会再次塌缩为模糊结论。
- 如果 `择机买入` 的边界不清楚，容易与 `确信买入` 混淆。

## 15. 版本结论

这个版本的本质不是让 `lite team` 更乐观，而是让它更像一个有纪律的机会发现器：

**更愿意表达值得参与的机会，但每一个积极判断都必须带着边界。**

