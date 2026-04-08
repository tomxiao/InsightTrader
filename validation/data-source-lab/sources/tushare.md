# Source Profile: tushare

## Summary

- Source type: hosted financial data API with Python SDK
- Official / unofficial: official platform + official Python client
- Auth model: token-based
- Pricing: mixed, token / points gated for some endpoints
- Main markets: China A-shares first, also Hong Kong and US market interfaces
- Best fit: multi-market OHLCV plus China-focused fundamentals
- Main limitations: permissions vary by endpoint, some news / announcement endpoints are gated, output normalization will be required

## Market Coverage

| Market | Supported | Notes |
| --- | --- | --- |
| China A-shares | Yes | Directly validated with `stock_basic`, `daily`, `income`, `balancesheet`, `cashflow` |
| Hong Kong | Yes | `hk_basic`, `hk_daily`, `hk_income` exist and returned data |
| US equities | Yes | `us_basic`, `us_daily`, `us_income` exist and returned data |
| ETFs | Partial | Likely via fund interfaces; not validated yet |
| Indices | Partial | `index_basic` exists; not validated yet |
| Macro / economy | Partial | `cctv_news` worked; broader macro dataset coverage not validated yet |
| Crypto / FX | Unknown | Not validated in this round |

## Tool Coverage

| TradingAgents tool | Supported | Native or derived | Notes |
| --- | --- | --- | --- |
| `get_stock_data` | Yes | Native | Strong fit for A/H/US daily OHLCV |
| `get_indicators` | Yes | Derived | Best implemented by computing indicators locally from OHLCV |
| `get_fundamentals` | Yes | Native / derived | Can be assembled from profile + indicator / statement endpoints |
| `get_balance_sheet` | Yes | Native | A-share verified; HK/US interface names exist |
| `get_cashflow` | Yes | Native | A-share verified |
| `get_income_statement` | Yes | Native | A-share verified; HK/US interface names exist |
| `get_news` | Partial | Native | Generic news endpoint works; ticker-specific company news suitability not yet confirmed |
| `get_global_news` | Partial | Native | `cctv_news` and generic news are usable as macro inputs |
| `get_insider_transactions` | No / gated | Unknown | Closest company-announcement style endpoint tested required permissions |

## Output Normalization Notes

### OHLCV

- Native fields: `ts_code`, `trade_date`, `open`, `high`, `low`, `close`, `pre_close`, `change`, `pct_chg`, `vol`, `amount`
- Missing fields: no explicit `adj_close` in the validated sample; may need adjustment-factor handling if required
- Can normalize to current `get_stock_data` output: Yes

### Technical Indicators

- Native indicators: many market metrics exist, but current TradingAgents format is better served by local derivation
- If not native, can derive from OHLCV: Yes
- Can normalize to current `get_indicators` output: Yes

### Fundamentals

- Overview fields: likely available through separate profile / indicator endpoints, but not assembled in this validation round
- Statement fields: confirmed for A-shares; interface names for HK/US also exist
- Frequency support: annual / quarterly style financial periods appear available
- Can normalize to current `fundamental_data` outputs: Yes, but requires a formatter layer

### News

- Ticker news: not yet confirmed as company-specific and exchange-qualified
- Macro/global news: usable
- Insider transactions: not confirmed; announcement-like endpoint appears permission-gated
- Can normalize to current `news_data` outputs: Partial

## Agent Compatibility

| Agent | Usable | Why |
| --- | --- | --- |
| Market analyst | Yes | Daily OHLCV is available for A/H/US and can feed local indicator calculation |
| Fundamentals analyst | Yes | Strong for A-shares; likely usable for HK/US after more field-level validation |
| News analyst | Partial | Generic / macro news works, but ticker-specific news and insider-like data are not yet strong enough |
| Full pipeline | Partial | Market + fundamentals are promising; news layer still needs fallback or hybrid sourcing |

## Integration Notes

- Proposed vendor id: `tushare`
- Proposed env var: `TUSHARE_TOKEN`
- Fallback strategy: `tushare,yfinance` for market/fundamentals; keep `yfinance` or another source for news at first
- Caching recommendation: Yes, especially OHLCV and statement snapshots
- Symbol normalization needed: Yes
- Main implementation files to add:
  - `tradingagents/dataflows/tushare_common.py`
  - `tradingagents/dataflows/tushare_stock.py`
  - `tradingagents/dataflows/tushare_fundamentals.py`
  - optionally `tradingagents/dataflows/tushare_news.py`

## Validation Notes

- Verified with real token from local `.env`
- Successful probes:
  - `stock_basic`
  - `daily`
  - `income`
  - `balancesheet`
  - `cashflow`
  - `hk_basic`
  - `hk_daily`
  - `us_basic`
  - `us_daily`
  - `news`
  - `cctv_news`
- Observed caveats:
  - company-announcement style endpoint required additional permissions
  - some HK/US financial probe responses were sparse in selected fields, so field mapping needs a second pass
  - console output showed Chinese text encoding noise in this shell, but tabular data returned successfully

## Final Verdict

- Recommended: Yes
- Recommended categories: `core_stock_apis`, `technical_indicators`, `fundamental_data`
- Do not use for: initial standalone replacement of `news_data`
- Confidence: Medium-high for market/fundamentals, medium-low for news
