# 主题：MU + AAOI + 2513.HK（2026-03-02 ~ 2026-04-07，日频）

## 主题定义

- 样本池：`MU`、`AAOI`、`2513.HK`
- 回测区间：`2026-03-02` ~ `2026-04-07`
- 采样方式：`daily`
- 调优主线：围绕 `decision manager` 做纯信号方向优化，并在第二阶段再处理价格区间与执行质量

## 主题目标

- 当前主题的正式主目标：把纯信号方向准确率提升到 `55%`
- 方向准确率统一定义为：`accuracy = good / (good + bad)`
- `unclear` 不计入方向准确率分母
- 后续每个 round 都必须显式汇报：
  - `good`
  - `bad`
  - `accuracy = good / (good + bad)`
  - 相对当前 baseline 的变化

## 当前基线

- 当前更稳的 baseline 为 `round11`
- `round11` 全主题纯信号统计：`good = 31`，`bad = 32`
- 对应方向准确率：`31 / (31 + 32) = 49.2%`
- 当前主指标最高的 candidate 为 `round13`
- `round13` 全主题纯信号统计：`good = 33`，`bad = 34`
- 对应方向准确率：`33 / (33 + 34) = 49.3%`
- 当前打标口径已采用对称阈值与未来 3 个交易日收盘均价：`buy good >= +2%`、`buy bad <= -2%`、`sell good <= -2%`、`sell bad >= +2%`
- `round14 ~ round16` 的连续实验都没能超过 `round13`，说明主题已经进入“接近 50% 后，全局 prompt 改写收益递减”的阶段
- `round17` 对“先分型，再决策”的第一次验证也没能超过 `round13`：它明显修回了 `MU`，但把 `AAOI` 的 `sell` 分支几乎清空，并让 `2513.HK` 回到更多 `hold`
- `round18 ~ round20` 再次从 `round13` 重新出发做了 3 轮迭代，结果仍未超过 `round13`：这说明当前瓶颈已经不是“再补一条 prompt 规则”，而是 prompt 级局部修补本身开始低于 `round13` 的结构上限
- `round21` 作为第一轮“架构 round”已经把结构化字段链路跑通：`样本分型 / 主导驱动 / 趋势完整性 / 风险状态 / 趋势判断` 可以稳定进入最终报告、被 parser 读取并进入实验汇总
- 但 `round21` 的主指标只有 `35.3%`，主要新增坏模式是把大量样本推回 `震荡等待确认 -> 保持观望`；其中这一分支的准确率只有 `16.7%`
- 这说明结构化设计方向是对的，但当前这版“显式分型 + 全局状态映射”还不能直接替代 `round13`，更适合作为归因增强层或局部 tie-breaker 来源
- `round22` 继续证明：把结构化字段降级成辅助层之后，主指标能从 `35.3%` 回升到 `42.6%`，`AAOI` 从 `29.2%` 提升到 `44.0%`，`2513.HK` 也回到 `45.0%`
- `round23` 则说明：继续全局放宽 `催化后高波动整理型`，虽然能维持 `AAOI / 2513.HK` 的改善，但会重新伤到 `MU`，全主题回落到 `41.8%`
- `round24` 进一步证明：真正有效的不是“改分型”，而是“在结构化辅助层之上，给特定坏样本语境加极窄 tie-breaker”。这轮把 `MU` 修回到 `47.8%`，全主题来到 `47.0%`，是结构化路线里最接近 `round11/13` 的一轮
- `round25` 也进一步说明：并不是所有“局部语境”都值得显式规则化。把 `AAOI` 的“极端超买、严禁追高”抽成显式规则后，并没有提升 `AAOI`，反而重新伤到了 `MU / 2513.HK`
- 因此，当前最佳的结构化使用方式已经比较清楚：字段应保留，但只能作为归因层或极窄的局部 tie-breaker，不能再做全局开关
- 这说明 signal-first 路线已经有效，但距离主题目标 `55%` 仍有明显差距

## 角色分工

- `MU`：美股主样本，重点观察弱证据下是否过早给出 `择机买入`
- `AAOI`：美股高波动对照样本，重点观察 `sell` 是否不足
- `2513.HK`：港股 guardrail，重点防止 prompt 被压得过度保守

## round 结论迁移

### round03

- 类型：`full_round`
- 作用：建立多标的 baseline，并沉淀后续 `decision_only_round` 复用的 `1_analysts`
- 结论：
  - `MU`：买入偏多，平均收益明显为负，说明当前买入门槛偏松
  - `AAOI`：整体接近平衡，但 `sell` 明显偏少
  - `2513.HK`：两头分布较自然，适合充当港股 guardrail

### round04

- 类型：`decision_only_round`
- baseline：`round03`
- 结论：
  - `MU`：买入从 `12` 收到 `8`，卖出从 `4` 升到 `5`，方向正确但仍偏弱
  - `AAOI`：收益从 `-0.0198` 提升到 `8.0742`，本轮改善最明显
  - `2513.HK`：买入从 `8` 压到 `3`，实际成交降到 `0`，出现过度保守副作用

## 当前判断

- round13 之后，这个主题已经进入“围绕 50% 向 55% 冲刺，但全局 prompt 改写开始互相牵制”的阶段
- `round14 -> round16` 已证明：同一条 `buy/hold` guardrail 很难同时兼顾 `MU / AAOI / 2513.HK`
- `round17` 进一步说明：显式分型思路本身有价值，但如果直接把它变成所有样本的第一判断层，仍会重新引入跨标的副作用
- `round18 -> round20` 则进一步证明：即使回到 `round13` 重新出发，继续用 prompt 级 tie-breaker 去补 MU 或 AAOI 的局部缺口，也很难在不伤到其余样本的前提下带来净提升
- `round21` 又补了一层新结论：结构化输出本身值得保留，但它更适合作为“可归因中间层”，而不是当前阶段直接接管所有动作判断
- `round22 -> round23` 进一步补充了路径经验：结构化字段作为辅助层是正确方向，但任何针对 `催化后高波动整理型` 的放宽，只要还是全局生效，就会继续对 `MU` 外溢
- `round24` 则把下一步路径又收窄了一层：后续优化更适合沿“保留结构化字段 + 只修单一坏样本语境”的方式继续推进，而不是再动分型定义或分型级规则
- `round25` 又补充了一条负面约束：即便是“单一坏样本语境”，只要这条语境容易被其他 ticker 共用，也不适合显式上升为 prompt 规则
- 后续 round 的优先级仍应服从 `55%` 主题目标，但更合理的推进方式是回到 `round13` candidate 或 `round11` 稳定 baseline，保留 `round21` 的结构化输出能力，再做更窄、更分群的 bad-case 修正，把分型只作为局部 tie-breaker 使用
- 当纯信号方向准确率真正稳定突破当前平台期后，再进入价格区间与执行质量优化阶段

## 目录说明

- `rounds/round03/`：从旧目录 `2026-0421-round03` 迁移的 baseline 结果
- `rounds/round04/`：从旧目录 `2026-0421-round04` 迁移的 decision-only 结果
- 每个 round 下新增 `reports/` 作为原始报告批次归档区，后续 report 必须直接落在 round 目录下
- 主题目录现在是唯一正式入口，旧的平铺 round 目录已不再作为主路径使用

### round 内部推荐结构

```text
roundXX/
  reports/
    MU/
      <batch_dir>/
    AAOI/
      <batch_dir>/
    2513.HK/
      <batch_dir>/
  tickers/
    <ticker>/
      batch/
      result/
      signal_case_labels.md
      notes.md
  compare.md
  compare_summary.md
  compare_summary.json
  experiment_meta.json
```

说明：

- `reports/` 存放该 round 的原始 backtest batch，包含 `signals.csv / trades.csv / summary.json / *-bt.png / reports/...`
- `tickers/<ticker>/result/` 继续保留为便于浏览的收编副本
- 后续所有新 round，都应先把 report 产物直接归档到 `roundXX/reports/`，不要再只放在 `backtest/output/`
