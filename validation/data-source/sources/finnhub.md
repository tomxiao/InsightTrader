# Source Profile: finnhub

## Summary

- Source type: hosted market + fundamentals + alternative data API
- Official / unofficial: official platform + official Python client
- Auth model: API token
- Pricing: tiered; endpoint access depends heavily on plan
- Main markets: US strongest in current token validation
- Best fit: company profile, reported financials, macro news, insider transactions
- Main limitations: candle / market coverage permissions depend on subscription; current token cannot access stock candles or non-US symbol catalogs

## Market Coverage

| Market | Supported | Notes |
| --- | --- | --- |
| China A-shares | Partial / plan-gated | `stock_symbols('SS'/'SZ')` returned 401 with current token |
| Hong Kong | Partial / plan-gated | `stock_symbols('HK')` returned 401 with current token |
| US equities | Yes | `company_profile2`, `financials_reported`, `stock_insider_transactions`, symbol catalog all worked |
| ETFs | Likely | Not directly validated |
| Indices | Partial | Not directly validated |
| Macro / economy | Yes | `general_news('general')` worked well for global / macro style headlines |
| Crypto / FX | Unknown | Not validated in this round |

## Tool Coverage

| TradingAgents tool | Supported | Native or derived | Notes |
| --- | --- | --- | --- |
| `get_stock_data` | Partial / gated | Native | Current token got 403 on `stock_candles` |
| `get_indicators` | Partial / gated | Native or derived | Viable only if candle access is available |
| `get_fundamentals` | Yes | Native | `company_profile2` plus other reference / metric endpoints can form overview |
| `get_balance_sheet` | Yes | Native | `financials_reported` returns structured balance sheet items |
| `get_cashflow` | Yes | Native | `financials_reported` returns structured cash-flow items |
| `get_income_statement` | Yes | Native | `financials_reported` returns structured income statement items |
| `get_news` | Partial | Native | `company_news('AAPL', ...)` worked syntactically but returned zero items for tested range |
| `get_global_news` | Yes | Native | `general_news('general')` returned rich market headlines |
| `get_insider_transactions` | Yes | Native | `stock_insider_transactions` returned usable records |

## Output Normalization Notes

### OHLCV

- Native fields: Finnhub candle endpoint can provide OHLCV arrays
- Missing fields: current token cannot access candle data, so normalization cannot be relied on yet
- Can normalize to current `get_stock_data` output: Yes in theory, not safe with current token

### Technical Indicators

- Native indicators: available on some plans / endpoints
- If not native, can derive from OHLCV: Yes if candle access exists
- Can normalize to current `get_indicators` output: Potentially, but blocked by candle permission in current validation

### Fundamentals

- Overview fields: `company_profile2` returned country, exchange, industry, IPO date, market cap, ticker, etc.
- Statement fields: `financials_reported` returned structured `bs`, `ic`, `cf` sections with labels and values
- Frequency support: annual confirmed
- Can normalize to current `fundamental_data` outputs: Yes

### News

- Ticker news: company-news endpoint exists, but tested request returned zero items
- Macro/global news: strong
- Insider transactions: strong
- Can normalize to current `news_data` outputs: Partially to strongly, depending on use case

## Agent Compatibility

| Agent | Usable | Why |
| --- | --- | --- |
| Market analyst | Partial | Blocked by candle permission on current token |
| Fundamentals analyst | Yes | Profile + reported statements are rich and structured |
| News analyst | Yes | Global news and insider transactions worked well; ticker-news depth needs more sampling |
| Full pipeline | Partial | Strong for fundamentals/news, weak for market analysis under current plan |

## Integration Notes

- Proposed vendor id: `finnhub`
- Proposed env var: `FINNHUB_TOKEN`
- Fallback strategy: use `finnhub` for fundamentals/news and pair with `yfinance` or another vendor for OHLCV when candle access is missing
- Caching recommendation: Yes, especially financials, symbol catalogs, insider transactions, and news snapshots
- Symbol normalization needed: Yes, especially if later using non-US exchanges
- Main implementation files to add:
  - `tradingagents/dataflows/finnhub_common.py`
  - `tradingagents/dataflows/finnhub_fundamentals.py`
  - `tradingagents/dataflows/finnhub_news.py`
  - optionally `tradingagents/dataflows/finnhub_stock.py`

## Validation Notes

- Verified with real token from local `.env`
- Successful probes:
  - `company_profile2('AAPL')`
  - `general_news('general')`
  - `financials_reported('AAPL', freq='annual')`
  - `stock_insider_transactions('AAPL', ...)`
  - `stock_symbols('US')`
- Observed failures / caveats:
  - `stock_candles('AAPL', ...)` returned 403: no access under current token
  - `stock_symbols('HK'/'SS'/'SZ')` returned 401 / no access under current token
  - `company_news('AAPL', 2024-01-01..2024-01-05)` returned zero items in tested window

## Final Verdict

- Recommended: Yes, but not as a standalone replacement for all categories
- Recommended categories: `fundamental_data`, `news_data`, optionally `get_insider_transactions`
- Do not use for: primary `core_stock_apis` or `technical_indicators` until candle permission is confirmed
- Confidence: High for fundamentals and insider/news usefulness, medium-low for market-data fit under current token
