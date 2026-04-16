# Source Profile: akshare

## Summary

- Source type: community-maintained Python data wrapper over public financial websites
- Official / unofficial: unofficial
- Auth model: no token required for the validated endpoints
- Pricing: free public-data access, but upstream sites may rate-limit or change behavior
- Main markets: China A-shares, Hong Kong, US equities; also broader macro and market data coverage across the library
- Best fit: broad market-data and financial-statement validation when a fast, no-key source is preferred
- Main limitations: heavily depends on upstream web endpoints, field names are source-specific, and network / proxy configuration can break requests

## Market Coverage

| Market | Supported | Notes |
| --- | --- | --- |
| China A-shares | Yes | Daily history and structured statements validated |
| Hong Kong | Yes | Daily history and HK financial report endpoint validated |
| US equities | Yes | Daily history and US financial report endpoint validated |
| ETFs | Unknown | Library likely supports some ETF endpoints, but not validated here |
| Indices | Unknown | Library likely supports index endpoints, but not validated here |
| Macro / economy | Partial | `news_cctv` worked; broader macro coverage exists in function list but was not deeply validated |
| Crypto / FX | Unknown | Not validated |

## Tool Coverage

| TradingAgents tool | Supported | Native or derived | Notes |
| --- | --- | --- | --- |
| `get_stock_data` | Yes | Native | `stock_zh_a_hist`, `stock_hk_hist`, and `stock_us_hist` all returned daily OHLCV-style tables |
| `get_indicators` | Yes | Derived | Indicators can be computed locally from returned OHLCV history |
| `get_fundamentals` | Partial | Native | A-share financial abstract validated; deeper company-profile normalization still needs review |
| `get_balance_sheet` | Yes | Native | A-share balance sheet plus HK/US report endpoints validated |
| `get_cashflow` | Yes | Native | A-share cash-flow statement validated |
| `get_income_statement` | Yes | Native | A-share profit / income statement validated |
| `get_news` | Partial | Native | `stock_news_em` failed in current environment, but other news endpoints worked |
| `get_global_news` | Yes | Native | `stock_news_main_cx` and `news_cctv` returned readable article lists |
| `get_insider_transactions` | No | Unknown | No insider endpoint validated |

## Output Normalization Notes

### OHLCV

- Native fields: dated OHLCV-style tables with open, high, low, close, volume, turnover, amplitude, and change columns
- Missing fields: column names are Chinese and vary by endpoint, so normalization is required
- Can normalize to current `get_stock_data` output: Yes

### Technical Indicators

- Native indicators: not validated in this pass
- If not native, can derive from OHLCV: Yes
- Can normalize to current `get_indicators` output: Yes, via local derivation

### Fundamentals

- Overview fields: A-share `stock_financial_abstract` returned multi-period key indicators
- Statement fields: A-share balance sheet, cash flow, and profit sheet validated; HK and US balance-sheet-style report endpoints also validated
- Frequency support: multiple report dates and report types were returned
- Can normalize to current `fundamental_data` outputs: Yes for statements, partial for overview/profile standardization

### News

- Ticker news: Partial; `stock_news_em(symbol='600519')` failed with an `ArrowInvalid` regex error in the tested version
- Macro/global news: Yes; `stock_news_main_cx()` and `news_cctv(date=...)` both returned article lists
- Insider transactions: Not validated
- Can normalize to current `news_data` outputs: Partial

## Validation Result

Validation environment used for this document:

- Python package: `akshare`
- Tested package version: `1.18.46`
- Important runtime note: requests inherited a local proxy by default and several endpoints only worked after clearing proxy-related environment variables

Validated live calls:

| Check | Result | Notes |
| --- | --- | --- |
| `stock_zh_a_hist('000001')` | Pass | Returned 22 rows of A-share daily history |
| `stock_hk_hist('00700')` | Pass | Returned 22 rows of HK daily history |
| `stock_us_hist('105.MSFT')` | Pass | Returned 22 rows of US daily history |
| `stock_financial_abstract('600519')` | Pass | Returned multi-period key metrics |
| `stock_balance_sheet_by_report_em('SH600519')` | Pass | Returned 100 structured balance-sheet rows |
| `stock_cash_flow_sheet_by_report_em('SH600519')` | Pass | Returned 96 structured cash-flow rows |
| `stock_profit_sheet_by_report_em('SH600519')` | Pass | Returned 100 structured profit-sheet rows |
| `stock_financial_hk_report_em('00700', ...)` | Pass | HK report endpoint returned structured rows |
| `stock_financial_us_report_em('TSLA', ...)` | Pass | US report endpoint returned structured rows |
| `stock_news_main_cx()` | Pass | Returned 100 news items with summary and URL |
| `news_cctv('20260408')` | Pass | Returned 15 macro/news items |
| `stock_news_em('600519')` | Fail | Raised `ArrowInvalid` due to invalid regex escape handling |

Key takeaways from the live test:

- A-share, HK, and US daily stock history are all usable in the current environment
- The source is strong for locally derived technical indicators because OHLCV history is available across the tested markets
- A-share structured fundamentals are strong, while HK and US statement support is present but still needs fuller field-mapping review
- News support is mixed: macro/general news works, but at least one ticker-news endpoint is currently broken
- Proxy inheritance matters operationally; clearing proxy environment variables materially improved request reliability

## Agent Compatibility

| Agent | Usable | Why |
| --- | --- | --- |
| Market analyst | Yes | A/H/US OHLCV history validated and indicators can be derived locally |
| Fundamentals analyst | Yes | A-share abstract and three statements validated; HK/US report endpoints also returned structured data |
| News analyst | Partial | General and macro news worked, but the tested ticker-news endpoint failed |
| Full pipeline | Partial | Market and fundamentals are strong, but news reliability and scraper stability need care |

## Integration Notes

- Proposed vendor id: `akshare`
- Proposed env var: none for the validated endpoints, but runtime may need proxy control
- Fallback strategy: pair with a more stable official API for production-critical or news-heavy workflows
- Caching recommendation: Yes, especially for slow statement endpoints and repeated historical pulls
- Symbol normalization needed: Yes, because A-share, HK, and US endpoints use different symbol formats
- Network note: clear `HTTP_PROXY`, `HTTPS_PROXY`, and related proxy variables when upstream requests fail unexpectedly
- Main implementation files to add:
  - `tradingagents/dataflows/akshare_common.py`
  - `tradingagents/dataflows/akshare_stock.py`
  - `tradingagents/dataflows/akshare_fundamentals.py`
  - optionally `tradingagents/dataflows/akshare_news.py`

## Final Verdict

- Recommended: Yes for market data and fundamentals prototyping; conditional for production news workflows
- Recommended categories: `core_stock_apis`, `technical_indicators`, `fundamental_data`
- Do not use for: ticker-news-dependent workflows without adding retries, fallbacks, or endpoint-specific guards
- Confidence: Medium-high, based on live validation across A/H/US market history and multiple fundamentals endpoints, with known scraper and news-endpoint fragility
