## 本轮目标

- 作为港股 guardrail，验证 `AAOI` 专用的支撑测试规则不会把高波动港股样本重新压回过度保守。

## 改动内容

- 与其他样本一致，使用 round11 骨架，只额外加入“当前价位未进入认可支撑区时，不要轻易继续给 buy”的窄规则。

## 观察结论

- `2513.HK` 是本轮受伤最重的样本，从 round11 的 `12/7/5` 直接退回 `8/13/3`。
- 动作分布从 `13/3/8` 变成 `3/14/7`，说明模型几乎把整条反弹参与逻辑重新压回了 `hold`。
- 多个原本正确的买入信号被压成 `hold bad_case`：
- `2026-03-06`：`buy_on_pullback good_case -> hold bad_case`
- `2026-03-16`：`buy_on_pullback good_case -> hold bad_case`
- `2026-03-23`：`buy_on_pullback good_case -> hold bad_case`
- `2026-03-24`：`buy_on_pullback good_case -> hold bad_case`
- 执行层也从 round11 的 `20.0955` 大幅回落到 `4.8077`。
- 这说明 round12 的新规则对港股高波动样本有很强的外溢保守效应。

## 下一步

- round13 必须回到 round11 baseline，不能继续保留这条支撑测试 gating 规则。
- `2513.HK` 继续作为港股 guardrail，用来拦截任何会把反弹期买点机械压回 `hold` 的改动。
