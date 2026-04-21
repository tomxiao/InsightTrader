# 2026-0421-round03

## 本轮目标

- 建立 `MU / AAOI / 2513.HK` 多标的 baseline。
- 先看当前 `decision manager` 在美股主样本、美股高波动样本、港股 guardrail 上的动作分布和坏样本结构。
- 为后续 `decision_only_round` 提供固定的 `1_analysts` 基线输入。

## 跨标的总结

- `MU`：`buy/hold/sell = 12/10/4`，平均收益 `-5.5512`，说明当前买入门槛偏松，弱证据下仍容易给出 `择机买入`。
- `AAOI`：`buy/hold/sell = 14/11/1`，平均收益 `-0.0198`，整体接近平衡，但 `sell` 明显偏少，风险主导识别不足。
- `2513.HK`：`buy/hold/sell = 8/9/7`，仅 1 笔实际成交但收益较好，说明港股样本当前分布较两头，适合充当 guardrail。
- 结论：round03 作为 baseline 可用；下一轮应在不重跑 analyst 的前提下，只调 `decision manager`，重点是“收紧 `MU` 的偏弱买入，补足 `AAOI` 的风险主导卖出，同时观察 `2513.HK` 是否被压得过度保守”。
