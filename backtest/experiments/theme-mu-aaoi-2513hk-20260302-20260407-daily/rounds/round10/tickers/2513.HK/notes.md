## 本轮目标

- 作为港股 guardrail，验证这条窄规则不会把样本重新压回极端保守。

## 改动内容

- 与其他样本一致，使用 round08 骨架，只增加一条“高位强趋势整理不应机械观望”的窄规则。

## 观察结论

- `2513.HK` 是本轮最大惊喜样本。纯信号从 round08 的 `9/11/4` 提升到 `14/8/2`。
- 多个原本的坏样本被修正，例如：
- `2026-03-16`：从 `hold bad_case` 变成 `buy_on_pullback good_case`
- `2026-03-19`：从 `buy_on_pullback bad_case` 变成 `sell good_case`
- `2026-03-23`：从 `hold bad_case` 变成 `buy_on_pullback good_case`
- `2026-03-26`：从 `hold bad_case` 变成 `sell good_case`
- 动作分布为 `buy=8 / hold=5 / sell=11`，虽然 `sell` 仍偏多，但已经不再是 round07/09 那种纯保守形态；执行层也恢复到 `1` 笔正收益交易。

## 下一步

- `2513.HK` 说明这条窄规则对高波动样本并没有外溢性伤害，反而显著改善了方向质量。
- 下一轮应把它继续作为 guardrail，防止专修 `AAOI` 时又重新伤到港股样本。
