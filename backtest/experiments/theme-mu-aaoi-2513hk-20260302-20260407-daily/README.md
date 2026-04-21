# 主题：MU + AAOI + 2513.HK（2026-03-02 ~ 2026-04-07，日频）

## 主题定义

- 样本池：`MU`、`AAOI`、`2513.HK`
- 回测区间：`2026-03-02` ~ `2026-04-07`
- 采样方式：`daily`
- 调优主线：围绕 `decision manager` 做动作边界收敛

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

- round04 说明“收买入、补卖出”的主线对美股样本有效
- 下一轮如果继续沿这个主题迭代，应保留对 `MU / AAOI` 的有效收口，同时专门补一条针对 `2513.HK` 的防过度保守规则

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
