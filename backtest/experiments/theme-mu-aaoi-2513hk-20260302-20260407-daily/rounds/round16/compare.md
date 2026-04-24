# round16

## 本轮目标

- 在 `round15` 基础上继续收窄 guardrail，只保留“公司特异性催化 + 技术回调参与”这类样本的偏多例外。
- 核心假设：这样可以保住 `MU / AAOI` 的偏多样本，同时不再误伤 `2513.HK`。

## 跨标的总结

- `round16` 全主题达到 `good/bad = 26/38`，方向准确率仅 `40.6%`，是这次 3-round sprint 中最差的一轮。
- `MU` 单票提升到 `11/9`，但 `AAOI` 直接退到 `6/17`，`2513.HK` 也退到 `9/12`。
- 新坏模式非常清楚：`AAOI` 和 `2513.HK` 被大面积压回 `hold`，说明“公司特异性催化 gating”会把 prompt 推回保守侧，而且只对 `MU` 这类样本有利。
- 结论：这条路径已经被明确证伪，不应继续沿用。
- 这次 `round14 -> round16` 的 3-round sprint 没有产生新的 baseline。后续若继续推进，应回到 `round13` candidate 或 `round11` 稳定 baseline，停止全局性 `buy/hold` guardrail 改写。
