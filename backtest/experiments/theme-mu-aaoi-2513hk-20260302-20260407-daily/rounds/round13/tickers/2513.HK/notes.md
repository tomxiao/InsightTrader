## 本轮目标

- 作为港股 guardrail，验证这条“假卖出”修正不会重新把高波动港股样本推回保守。

## 改动内容

- 与其他样本一致，沿用 round11 骨架，只增加“催化后首轮过热回撤不要轻易给 sell”的窄规则。

## 观察结论

- `2513.HK` 是本轮同步改善样本，从 round11 的 `12/7/5` 提升到 `15/8/1`。
- 典型修复包括：
- `2026-03-04`：`hold unclear -> buy_on_pullback good_case`
- `2026-03-30`：`hold bad_case -> buy_on_pullback good_case`
- 也有新回撤，例如：
- `2026-03-24`：`buy_on_pullback good_case -> hold bad_case`
- `2026-03-27`：`buy_on_pullback good_case -> hold bad_case`
- 尽管如此，整体方向质量仍更好，而且执行层明显增强到 `3` 笔交易、`28.6635` 的平均收益。
- 动作分布 `buy=9 / hold=8 / sell=7`，说明这轮没有把港股样本推回极端保守。

## 下一步

- round14 若继续推进，应把 `2513.HK` 继续留作港股 guardrail。
- 重点防止为修 `MU` 而重新损伤它已经恢复的反弹期参与能力。
