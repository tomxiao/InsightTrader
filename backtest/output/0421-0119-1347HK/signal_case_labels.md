# 0421-0119-1347HK Signal Case Labels

## Labeling Rule

- `buy_on_pullback`: realized return if triggered; otherwise `3`-day future return fallback
- `sell`: `good_case` when `ret_3d <= -2.0%`, `bad_case` when `ret_3d >= 2.0%`
- `hold`: `good_case` when `abs(ret_3d) <= 2.0%`, `bad_case` when `abs(ret_3d) >= 5.0%`

## Summary

- `good_case`: 6
- `bad_case`: 10
- `unclear`: 7

## Daily Labels

| trade_date | action | label | metric | note |
| --- | --- | --- | --- | --- |
| 2026-03-02 | hold | bad_case | ret_3d_pct=-9.82% | Hold missed a meaningful move. |
| 2026-03-03 | sell | good_case | ret_3d_pct=-5.33% | Price fell after sell signal. |
| 2026-03-04 | sell | unclear | ret_3d_pct=-0.57% | Post-signal move was too small to judge. |
| 2026-03-05 | sell | bad_case | ret_3d_pct=5.10% | Price rose after sell signal. |
| 2026-03-06 | sell | bad_case | ret_3d_pct=5.16% | Price rose after sell signal. |
| 2026-03-09 | sell | bad_case | ret_3d_pct=7.95% | Price rose after sell signal. |
| 2026-03-10 | hold | good_case | ret_3d_pct=0.80% | Hold matched sideways price action. |
| 2026-03-11 | hold | unclear | ret_3d_pct=4.25% | Move was moderate; not a clear hold success/failure. |
| 2026-03-12 | hold | good_case | ret_3d_pct=-0.44% | Hold matched sideways price action. |
| 2026-03-13 | hold | good_case | ret_3d_pct=-0.16% | Hold matched sideways price action. |
| 2026-03-16 | hold | unclear | ret_3d_pct=-2.68% | Move was moderate; not a clear hold success/failure. |
| 2026-03-17 | hold | bad_case | ret_3d_pct=-6.46% | Hold missed a meaningful move. |
| 2026-03-18 | hold | bad_case | ret_3d_pct=-8.81% | Hold missed a meaningful move. |
| 2026-03-19 | hold | bad_case | ret_3d_pct=-8.43% | Hold missed a meaningful move. |
| 2026-03-20 | hold | good_case | ret_3d_pct=-0.84% | Hold matched sideways price action. |
| 2026-03-23 | hold | bad_case | ret_3d_pct=-5.94% | Hold missed a meaningful move. |
| 2026-03-24 | hold | good_case | ret_3d_pct=-0.60% | Hold matched sideways price action. |
| 2026-03-25 | hold | bad_case | ret_3d_pct=-6.16% | Hold missed a meaningful move. |
| 2026-03-26 | hold | bad_case | ret_3d_pct=-12.41% | Hold missed a meaningful move. |
| 2026-03-27 | sell | unclear | ret_3d_pct=0.60% | Post-signal move was too small to judge. |
| 2026-03-30 | sell | unclear | ret_3d_pct=1.03% | Post-signal move was too small to judge. |
| 2026-03-31 | hold | unclear | ret_3d_pct=2.64% | Move was moderate; not a clear hold success/failure. |
| 2026-04-01 | sell | unclear |  | No future bars in test window. |

## Immediate Bad Cases To Review

- `2026-03-02` `hold`
- `2026-03-05` `sell`
- `2026-03-06` `sell`
- `2026-03-09` `sell`
- `2026-03-17` `hold`
- `2026-03-18` `hold`
- `2026-03-19` `hold`
- `2026-03-23` `hold`
- `2026-03-25` `hold`
- `2026-03-26` `hold`