## 本轮目标

- 验证“公司级催化仍是正文主线时，不要轻易把趋势中的回调降成 hold”能否修回 round13 的 MU 坏样本。

## 改动内容

- 在 round13 骨架上增加一条更偏 MU 的窄规则：若回调主要被描述为宏观噪音、事件前整理或等待更好位置参与，则不要轻易从 `趋势延续 -> 择机买入` 降级。

## 观察结论

- 这条规则没有稳定修好 MU，只把结构打得更乱。
- 正向变化有：
- `2026-03-03`：`hold bad_case -> sell good_case`
- `2026-03-10`：`hold bad_case -> buy_on_pullback good_case`
- 但副作用同样明显：
- `2026-03-02`：`hold unclear -> buy_on_pullback bad_case`
- `2026-03-09`：`buy_on_pullback good_case -> hold bad_case`
- 动作分布变成 `buy=12 / hold=8 / sell=6`，比 round13 更偏多，但没有换来更高准确率，只得到 `8/11/7`。

## 下一步

- 不能继续沿这条更偏多的 MU 规则放大。
- 下一轮若还想保留 MU 修复，只能把条件收得更窄，避免外溢到其他样本。
