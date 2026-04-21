# 2026-0421-round01 Decision Summary Patterns

This note focuses on the language patterns inside `2_decision/summary.md` that are repeatedly associated with `bad_case` labels.

## Main Finding

The bad cases are not random.  
They are strongly associated with a few repeated summary templates.

Those templates are currently overpowering price-action evidence.

## Pattern 1: Macro Risk Overrides Near-Term Reversal Evidence

### Typical Language

- “地缘冲突升级压制风险偏好”
- “宏观风险主导”
- “公司处于新闻静默期 / 信息真空”
- “缺乏自身催化剂”

### Where It Shows Up

#### 1347.HK

- `2026-03-05` `sell`
- `2026-03-09` `hold`
- `2026-03-11` `sell`
- `2026-03-23` `hold`

#### AXTI

- `2026-03-09` `hold`
- `2026-03-31` `hold`

### Why It Fails

This language is being used as a veto.

Instead of saying:

- macro risk is a headwind, but price is starting to recover

the summary often says:

- macro risk exists, therefore no bullish action is allowed

That makes the system slow to recognize:

- rebound setups
- sentiment repair
- price-led reversals that happen before new fundamentals or news arrive

### Tuning Implication

The prompt should explicitly forbid macro risk from fully vetoing a signal when:

- price has already reclaimed short-term structure
- sell-side evidence is stale
- the proposed action horizon is only 1 to 2 weeks

## Pattern 2: “Information Vacuum” Is Treated As Directional Evidence

### Typical Language

- “公司层面信息真空”
- “无公司特异性利好”
- “缺乏短期催化剂”
- “无法形成完整、可执行的交易计划”

### Where It Shows Up

#### 1347.HK

- `2026-03-09` `hold`
- `2026-03-23` `hold`

#### AXTI

- `2026-03-31` `hold`

### Why It Fails

No new company-specific catalyst is not the same thing as no tradable signal.

This language repeatedly pushes the model toward:

- `hold`
- “wait for confirmation”
- “cannot form executable plan”

even when the chart already offers:

- clear support/resistance
- volatility-defined risk
- an obvious short-term directional move

### Tuning Implication

The prompt should separate:

- “no fresh company news”

from

- “no short-term trading plan”

These are not equivalent.

## Pattern 3: “Long-Term Trend Not Broken” Leads To Overly Optimistic Pullback Buys

### Typical Language

- “长期趋势未破坏”
- “均线多头排列”
- “上涨结构未破坏”
- “趋势延续中的谨慎参与”
- “等待回调至关键支撑区域分批买入”

### Where It Shows Up

#### AXTI

- `2026-03-03` `buy_on_pullback`
- `2026-03-23` `buy_on_pullback`
- `2026-03-24` `buy_on_pullback`

### Why It Fails

This pattern treats:

- still-elevated long-term structure
- intact higher-timeframe moving averages
- vague “support zone” reasoning

as enough evidence for `buy_on_pullback`.

But in the bad cases, those conditions coexisted with:

- momentum decay
- elevated volatility
- unstable support
- macro-led de-risking

The summaries are too willing to convert “not broken yet” into “buyable pullback”.

### Tuning Implication

The prompt should require stronger evidence before `buy_on_pullback` is allowed, for example:

- actual stabilization signal
- at least one short-term reclaim or failed breakdown
- clear evidence that support is holding, not just nearby

## Pattern 4: “Not Enough For Sell, Not Enough For Buy” Defaults To Hold

### Typical Language

- “多空因素拉扯，方向未明”
- “不足以构成完整交易计划”
- “当前不足以给出可执行的入场或离场计划”
- “等待确认”

### Where It Shows Up

#### 1347.HK

- `2026-03-09` `hold`
- `2026-03-19` `hold`
- `2026-03-23` `hold`
- `2026-03-25` `hold`

#### AXTI

- `2026-03-04` `hold`
- `2026-03-06` `hold`
- `2026-03-09` `hold`
- `2026-03-10` `hold`
- `2026-03-18` `hold`
- `2026-03-19` `hold`
- `2026-03-31` `hold`
- `2026-04-01` `hold`
- `2026-04-06` `hold`

### Why It Fails

This is the single biggest summary-level failure mode.

The model appears to use `hold` as the fallback when:

- the bull case is imperfect
- the bear case is imperfect
- macro and technical signals disagree

But many of these situations were not truly neutral.  
They were already directional enough to justify either:

- a tactical `sell`
- or a defined `buy_on_pullback`

### Tuning Implication

The prompt should make `hold` harder to justify.

Specifically, it should require the model to explain:

1. why the setup is genuinely non-directional over the next 1 to 2 weeks
2. why neither `sell` nor `buy_on_pullback` is executable
3. what exact future condition would flip the action

If it cannot do that concretely, `hold` should be disfavored.

## Pattern 5: Support-Zone Logic Is Too Abstract

### Typical Language

- “接近关键支撑”
- “等待企稳”
- “回调到支撑区再布局”
- “若转多需观察支撑区出现信号”

### Where It Shows Up

#### AXTI

- `2026-03-03` `buy_on_pullback`
- `2026-03-23` `buy_on_pullback`
- `2026-03-24` `buy_on_pullback`

#### 1347.HK

- `2026-03-23` `hold`

### Why It Fails

The summaries often identify support zones correctly, but they use them too loosely.

The model often behaves as if:

- “support exists nearby”

already implies:

- “a valid pullback plan exists”

That is not enough.  
Nearby support without stabilization is not yet a trade plan.

### Tuning Implication

The prompt should force a distinction between:

- support area exists
- support has been tested
- support has held
- support has produced a tradable reversal

Only the last two should unlock actionable pullback language.

## Immediate Prompt-Level Changes To Test

The next prompt revision should likely include these constraints:

1. `hold` is only valid if the next 1 to 2 week direction is genuinely low-conviction and the summary can state concrete invalidation for both bull and bear alternatives.
2. Macro risk and lack of company news cannot by themselves justify `hold` or `sell` if price has already reclaimed short-term structure.
3. `buy_on_pullback` requires actual stabilization evidence, not just a nearby support zone or “long-term trend not broken”.
4. When price is in a rebound window, stale bearish evidence must be discounted unless the summary can cite fresh breakdown confirmation.

## Most Important Thing To Fix First

Fix `hold` first.

Reason:

- It is the biggest repeated language pattern across both symbols.
- It affects both up-move misses and down-move misses.
- Tightening `hold` should improve signal quality without automatically making the system too aggressive.
