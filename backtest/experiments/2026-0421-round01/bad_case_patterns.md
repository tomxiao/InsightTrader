# 2026-0421-round01 Bad Case Patterns

This note groups the current `bad_case` labels into reusable tuning buckets.

## Cross-Market Summary

The current system is not making one single mistake across all symbols. It is making two repeated classes of mistakes:

- It misreads reversal windows.
- It overuses `hold` when the market is already moving directionally.

Those two issues appear in both `AXTI` and `1347.HK`, but they show up differently:

- `AXTI` fails by becoming too aggressive on pullback buys and too late on directional confirmation.
- `1347.HK` fails by staying too bearish during rebound windows and too passive during fresh directional moves.

## Shared Pattern A: Reversal Misclassification

### Description

The system struggles around short-term reversal windows.  
It often continues the previous regime one step too long:

- still `sell` into an early rebound
- still `hold` after trend has already turned
- still `buy_on_pullback` after the pullback has become a breakdown

### Evidence

#### 1347.HK

- `2026-03-05` `sell` -> `bad_case`
- `2026-03-06` `sell` -> `bad_case`
- `2026-03-11` `sell` -> `bad_case`
- `2026-03-31` `sell` -> `bad_case`

#### AXTI

- `2026-03-05` `sell` -> `bad_case`
- `2026-03-23` `buy_on_pullback` -> `bad_case`
- `2026-03-24` `buy_on_pullback` -> `bad_case`
- `2026-03-30` `buy_on_pullback` -> `bad_case`

### Interpretation

This points to a regime-switch problem rather than a pure action bias.  
The model does not recognize quickly enough when:

- a rebound is strong enough to invalidate a bearish stance
- a pullback has already transitioned into a breakdown

## Shared Pattern B: `hold` Used As A Default Escape Hatch

### Description

When the signal is ambiguous, the system frequently falls back to `hold`.  
That becomes a `bad_case` when price actually enters a meaningful directional move soon after.

### Evidence

#### 1347.HK

- `2026-03-09` `hold` -> `bad_case`
- `2026-03-19` `hold` -> `bad_case`
- `2026-03-23` `hold` -> `bad_case`
- `2026-03-25` `hold` -> `bad_case`

#### AXTI

- `2026-03-04` `hold` -> `bad_case`
- `2026-03-06` `hold` -> `bad_case`
- `2026-03-09` `hold` -> `bad_case`
- `2026-03-10` `hold` -> `bad_case`
- `2026-03-18` `hold` -> `bad_case`
- `2026-03-19` `hold` -> `bad_case`
- `2026-03-31` `hold` -> `bad_case`
- `2026-04-01` `hold` -> `bad_case`
- `2026-04-06` `hold` -> `bad_case`

### Interpretation

This is not random noise.  
The system appears to prefer `hold` when:

- macro and technical signals conflict
- it lacks conviction for `buy`
- it does not want to issue `sell` without a fully formed breakdown narrative

That means `hold` is currently absorbing too many unresolved cases.

## AXTI-Specific Pattern: Catching Falling Knives

### Description

On `AXTI`, the system sometimes converts “high-volatility pullback” into `buy_on_pullback` even when the next move is still lower.

### Evidence

- `2026-03-02` `buy_on_pullback` -> `bad_case`
- `2026-03-03` `buy_on_pullback` -> `bad_case`
- `2026-03-12` `buy_on_pullback` -> `bad_case`
- `2026-03-23` `buy_on_pullback` -> `bad_case`
- `2026-03-24` `buy_on_pullback` -> `bad_case`
- `2026-03-30` `buy_on_pullback` -> `bad_case`

### Interpretation

This is the biggest AXTI-specific problem.  
The system is too willing to treat:

- large drawdowns
- nearby support zones
- “trend not fully broken” language

as sufficient grounds for a low-risk pullback buy.

The real issue is not buy frequency alone.  
It is weak filtering between:

- healthy retracement
- failed bounce
- trend breakdown

## 1347.HK-Specific Pattern: Persistent Bearish Drift

### Description

On `1347.HK`, the system often remains bearish or defensive for too long.

### Evidence

- `2026-03-05` `sell` -> `bad_case`
- `2026-03-06` `sell` -> `bad_case`
- `2026-03-11` `sell` -> `bad_case`
- `2026-03-31` `sell` -> `bad_case`

### Interpretation

The issue here is not overtrading.  
It is stale bearishness. The system seems to anchor too heavily on prior weakness, then underreacts when price begins recovering.

## Priority Order

### Priority 1

Reduce `hold` as a fallback for clearly directional setups.

Reason:

- This appears in both markets.
- It creates the largest concentration of repeat `bad_case` labels.
- It is likely the cleanest place to improve signal quality without making the system hyperactive.

### Priority 2

Improve reversal recognition.

Reason:

- This appears in both bearish-to-bounce and bullish-to-breakdown transitions.
- It should reduce both premature `sell` and low-quality pullback buys.

### Priority 3

Tighten `buy_on_pullback` quality filters for `AXTI`-like names.

Reason:

- This is important, but currently more symbol-specific than the first two problems.
- It should come after the shared issues are handled.

## Suggested Next Tuning Questions

Before changing any code or prompt, the next review should answer:

1. What exact language in the decision summary leads to `hold` instead of action?
2. What exact language causes the model to keep a bearish stance into rebound windows?
3. What exact evidence is being treated as enough to justify `buy_on_pullback` on weakening names?

Those three answers should drive the next prompt or rule change.
