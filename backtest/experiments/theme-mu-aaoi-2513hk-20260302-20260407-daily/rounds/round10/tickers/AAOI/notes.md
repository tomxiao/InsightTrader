## 本轮目标

- 尝试修复 `AAOI` 在高位强趋势整理阶段的 `hold` 滥用，让已偏多但不追高的样本更容易落回 `择机买入`。

## 改动内容

- decision manager 回到 round08 骨架，只加了一条针对“高位强趋势整理”不应机械观望的窄规则。

## 观察结论

- `AAOI` 没有改善，反而退步。纯信号从 round08 的 `8/15/3` 回落到 `6/18/2`。
- 几个 round08 的好样本被再次改坏，例如：
- `2026-03-09`：从 `buy_on_pullback good_case` 变成 `sell bad_case`
- `2026-03-19`：从 `buy_on_pullback good_case` 变成 `hold bad_case`
- `2026-04-02`：从 `buy_on_pullback good_case` 变成 `hold bad_case`
- 执行层虽比 round09 好很多，回到 `-1.7202`，但仍不如 round08。
- 这说明本轮的窄规则并没有正中 `AAOI` 的核心误差。

## 下一步

- 如果继续开 round11，`AAOI` 必须成为唯一主攻样本。
- 重点不是笼统减少 `hold`，而是防止把“偏多修复中的等待参与”误切到 `sell` 或重新压回 `hold`。
