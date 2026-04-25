## 本轮目标

- 作为新时间外主题的 baseline 样本，验证 `MU` 在不做额外调优时是否仍能维持较高方向准确率。

## 改动内容

- 本轮不做针对性调优。
- 完整沿用当前代码里的 `decision manager` prompt、evidence schema 与 `decision_rules.py`，以 full-round 方式重新生成报告并建立 baseline。

## 观察结论

- `MU` 本轮为 `10 / 7 / 11`，方向准确率 **58.8%**。
- 这明显高于来源主题里很多历史 round，也高于 `50%` 泛化门槛。
- 说明当前这套 `evidence + rules` 体系在 `MU` 上的时间外稳定性很好。
- 同时，`MU` 在这个新时间窗里几乎全部落到 `buy_on_pullback`，但坏样本数量仍控制在 `7`，说明信号偏多并未明显失真。

## 下一步

- `MU` 在本主题里更适合作为稳定样本与 guardrail 保留，不需要优先成为调优对象。
