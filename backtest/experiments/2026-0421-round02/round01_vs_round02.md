# Round01 vs Round02

Round 2 uses the updated `decision_manager` prompt that:

- makes `保持观望` harder to justify
- prevents macro risk / information vacuum from acting as an automatic veto
- requires stronger stabilization evidence before `择机买入`

## Cross-Ticker Diff

| ticker | metric | round01 | round02 | delta |
| --- | --- | --- | --- | --- |
| AXTI | buy_signals | 11 | 15 | +4 |
| AXTI | hold_signals | 10 | 9 | -1 |
| AXTI | sell_signals | 5 | 2 | -3 |
| AXTI | trade_count | 6 | 9 | +3 |
| AXTI | triggered_trade_count | 6 | 11 | +5 |
| AXTI | win_rate | 50.0 | 66.6667 | +16.6667 |
| AXTI | avg_return | -1.638 | 10.567 | +12.205 |
| AXTI | good_case | 8 | 12 | +4 |
| AXTI | bad_case | 16 | 12 | -4 |
| 1347.HK | buy_signals | 1 | 0 | -1 |
| 1347.HK | hold_signals | 6 | 15 | +9 |
| 1347.HK | sell_signals | 16 | 8 | -8 |
| 1347.HK | trade_count | 1 | 0 | -1 |
| 1347.HK | triggered_trade_count | 2 | 0 | -2 |
| 1347.HK | good_case | 6 | 6 | 0 |
| 1347.HK | bad_case | 8 | 10 | +2 |
| 1347.HK | unclear | 9 | 7 | -2 |

## Reading

### AXTI

Round 2 clearly moved in the intended direction for this symbol:

- fewer `sell`
- slightly fewer `hold`
- more `buy_on_pullback`
- more completed trades
- higher win rate
- positive average return
- fewer `bad_case`

This means the new prompt did reduce stale bearishness and did reduce part of the old `hold` overuse on AXTI.

### 1347.HK

Round 2 moved in the wrong direction for this symbol:

- `sell` dropped sharply
- `hold` expanded from 6 to 15
- `buy_on_pullback` disappeared
- no trades were triggered
- `bad_case` increased from 8 to 10

This means the new prompt over-corrected on the HK sample:

- it removed some stale bearishness
- but replaced it with excessive `hold`

## Main Conclusion

The round 2 prompt change improved AXTI materially but did not generalize well to 1347.HK.

So the current revision is not ready to be treated as a stable cross-market improvement.

## What Likely Happened

The prompt change successfully discouraged:

- lazy `sell`
- macro-risk-only bearish calls

But it also made the model too cautious about taking directional action in weaker, slower, more ambiguous names.

In practice, that means:

- AXTI benefited because it needed less stale bearishness
- 1347.HK degraded because `hold` remained the easiest escape hatch once `sell` got harder

## Recommended Next Step

The next revision should **not** simply push harder in the same direction.

It should specifically refine the `保持观望` gate:

1. `保持观望` should stay hard to use.
2. But when price is already in a weak directional move and there is no stabilization evidence, the prompt must still allow `风险主导 -> 建议卖出`.
3. The prompt should distinguish:
   - bearish thesis is stale
   - bearish thesis is still current

That is the next lever to tune.
