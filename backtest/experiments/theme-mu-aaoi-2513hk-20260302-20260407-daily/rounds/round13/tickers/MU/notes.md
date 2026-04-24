## 本轮目标

- 作为 guardrail，验证专修 `AAOI` 的“假卖出”规则不会明显破坏 `MU`。

## 改动内容

- 与其他样本一致，回到 round11 骨架，只加入“催化后首轮过热回撤不要轻易给 sell”的窄规则。

## 观察结论

- `MU` 是本轮的主要代价样本，从 round11 的 `11/10/5` 回落到 `8/12/6`。
- 主要问题不是乱卖，而是把几个本来正确的偏多样本压回了 `hold`：
- `2026-03-10`：`buy_on_pullback good_case -> hold bad_case`
- `2026-03-13`：`buy_on_pullback good_case -> hold bad_case`
- 也有少量正向变化，如 `2026-04-06`：`hold unclear -> buy_on_pullback good_case`，但不足以抵消整体回撤。
- 动作分布为 `buy=13 / hold=8 / sell=5`，看起来不算极端保守，但坏样本集中在错过趋势继续上冲的几天。
- 执行层平均收益也略差于 round11，来到 `-5.7989`。

## 下一步

- 如果继续开 round14，`MU` 必须成为唯一 guardrail。
- 重点是防止“趋势中的健康回调 + 等待更好位置参与”再次被压成 `hold`。
