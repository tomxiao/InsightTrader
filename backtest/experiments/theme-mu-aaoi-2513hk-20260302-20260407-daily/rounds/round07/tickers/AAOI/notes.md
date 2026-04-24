## 本轮目标

- 观察 signal-first prompt 是否会破坏 `AAOI` 在 round04 已经相对稳定的方向判断。

## 改动内容

- 复用 round03 的 analyst 报告，只替换 `decision manager` 的 prompt 为 signal-first 版本。
- 新 prompt 让 `buy / hold / sell` 先按方向判断落地，再把入场区和失效条件作为附加输出。

## 观察结论

- 动作分布从 round04 的 `11/13/2` 变成 `9/13/4`，即 `buy` 小幅减少、`sell` 小幅增加。
- 纯信号标签为 `good/bad/unclear = 5/20/1`，和 round04 完全一致，说明这轮对 `AAOI` 的方向质量基本持平。
- 但执行层明显恶化：实际成交 `6` 次，平均收益 `-10.0406`，远弱于 round04 的 `8.0742`。
- 这进一步证明 signal-first prompt 已经把“方向判断”和“交易计划结果”拆开了；对 `AAOI` 来说，这轮更像是信号层持平、执行层失真。

## 下一步

- 后续 round 不需要再把 `AAOI` 当成主攻样本。
- 只要下一轮修正 `sell` 边界时不伤到当前的 `5/20` 纯信号水平，就可以把更多精力放在 `MU` 和 `2513.HK` 的平衡上。
