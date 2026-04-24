## 本轮目标

- 作为 guardrail，验证专修 `AAOI` 不会把 round10 已经改善的 `MU` 再次推坏。

## 改动内容

- 与其他样本一致，沿用 round10 的 signal-first 骨架，只增加一条针对“公司级催化后高位整理”不应机械降级的窄规则。

## 观察结论

- `MU` 没有被专修 `AAOI` 牵连，反而从 round10 的 `10/10/6` 继续改善到 `11/10/5`。
- 这轮主要增益来自两类修正：
- `2026-03-04`、`2026-03-06`：从 `buy_on_pullback unclear` 收回到 `hold good_case`
- `2026-03-13`：从 `hold bad_case` 修到 `buy_on_pullback good_case`
- 也有局部回撤，例如：
- `2026-03-25`：`sell good_case -> hold bad_case`
- `2026-04-06`：`buy_on_pullback good_case -> hold unclear`
- 动作分布从 round10 的 `17/2/7` 收回到 `13/7/6`，说明这轮没有继续放大 `MU` 的过度偏多问题。
- 执行层平均收益略回落到 `-5.7768`，但纯信号层仍是改善的。

## 下一步

- `MU` 现在已经不是主短板，下一轮不宜再为它做大幅定制化放宽。
- 更适合把它继续当作回归测试样本，防止为了修 `AAOI` 再次把 `MU` 的健康回调误判打乱。
