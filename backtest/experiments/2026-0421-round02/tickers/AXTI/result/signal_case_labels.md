# 0421-0119-AXTI Signal Case Labels

## Labeling Rule

- `buy_on_pullback`: realized return if triggered; otherwise `3`-day future return fallback
- `sell`: `good_case` when `ret_3d <= -2.0%`, `bad_case` when `ret_3d >= 2.0%`
- `hold`: `good_case` when `abs(ret_3d) <= 2.0%`, `bad_case` when `abs(ret_3d) >= 5.0%`

## Summary

- `good_case`: 12
- `bad_case`: 12
- `unclear`: 2

## Daily Labels

| trade_date | action | label | metric | note |
| --- | --- | --- | --- | --- |
| 2026-03-02 | buy_on_pullback | good_case | realized_return_pct=22.70% | Triggered and exited profitable. |
| 2026-03-03 | buy_on_pullback | good_case | realized_return_pct=71.98% | Triggered and exited profitable. |
| 2026-03-04 | buy_on_pullback | bad_case | realized_return_pct=-4.11% | Triggered and lost money. |
| 2026-03-05 | hold | bad_case | ret_3d_pct=13.21% | Hold missed a meaningful move. |
| 2026-03-06 | buy_on_pullback | good_case | ret_3d_pct=22.09% | Buy signal was followed by price appreciation. |
| 2026-03-09 | hold | bad_case | ret_3d_pct=44.36% | Hold missed a meaningful move. |
| 2026-03-10 | hold | bad_case | ret_3d_pct=26.71% | Hold missed a meaningful move. |
| 2026-03-11 | buy_on_pullback | good_case | realized_return_pct=13.65% | Triggered and exited profitable. |
| 2026-03-12 | buy_on_pullback | good_case | realized_return_pct=10.88% | Triggered and exited profitable. |
| 2026-03-13 | buy_on_pullback | good_case | ret_3d_pct=4.34% | Buy signal was followed by price appreciation. |
| 2026-03-16 | buy_on_pullback | good_case | realized_return_pct=2.62% | Triggered and exited profitable. |
| 2026-03-17 | hold | bad_case | ret_3d_pct=12.09% | Hold missed a meaningful move. |
| 2026-03-18 | hold | bad_case | ret_3d_pct=45.27% | Hold missed a meaningful move. |
| 2026-03-19 | buy_on_pullback | good_case | realized_return_pct=2.48% | Triggered and exited profitable. |
| 2026-03-20 | buy_on_pullback | good_case | ret_3d_pct=15.94% | Buy signal was followed by price appreciation. |
| 2026-03-23 | buy_on_pullback | good_case | ret_3d_pct=7.87% | Buy signal was followed by price appreciation. |
| 2026-03-24 | buy_on_pullback | bad_case | ret_3d_pct=-5.91% | Buy signal was followed by price weakness. |
| 2026-03-25 | sell | good_case | ret_3d_pct=-22.95% | Price fell after sell signal. |
| 2026-03-26 | buy_on_pullback | bad_case | realized_return_pct=-17.85% | Triggered and lost money. |
| 2026-03-27 | buy_on_pullback | bad_case | realized_return_pct=-7.24% | Triggered and lost money. |
| 2026-03-30 | buy_on_pullback | bad_case | ret_3d_pct=-12.85% | Buy signal was followed by price weakness. |
| 2026-03-31 | hold | bad_case | ret_3d_pct=-20.37% | Hold missed a meaningful move. |
| 2026-04-01 | hold | bad_case | ret_3d_pct=-20.22% | Hold missed a meaningful move. |
| 2026-04-02 | hold | unclear | ret_3d_pct=-3.56% | Move was moderate; not a clear hold success/failure. |
| 2026-04-06 | sell | good_case | ret_3d_pct=-13.97% | Price fell after sell signal. |
| 2026-04-07 | hold | unclear |  | No future bars in test window. |

## Immediate Bad Cases To Review

- `2026-03-04` `buy_on_pullback`
- `2026-03-05` `hold`
- `2026-03-09` `hold`
- `2026-03-10` `hold`
- `2026-03-17` `hold`
- `2026-03-18` `hold`
- `2026-03-24` `buy_on_pullback`
- `2026-03-26` `buy_on_pullback`
- `2026-03-27` `buy_on_pullback`
- `2026-03-30` `buy_on_pullback`
- `2026-03-31` `hold`
- `2026-04-01` `hold`