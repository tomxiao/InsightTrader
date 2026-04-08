# Source Profile: futu

## Summary

- Source type: broker / trading platform API with local gateway
- Official / unofficial: official
- Auth model: platform account login through local `OpenD` gateway
- Python package: install `moomoo-api`, import as `moomoo`
- Pricing: API itself is not separately charged, but market-data permissions and account entitlements apply
- Main markets: Hong Kong, US, A-share market data; also supports more products in the Futu ecosystem
- Best fit: broker-grade quote and historical OHLCV access for markets already enabled on the logged-in account
- Main limitations: requires local or remote `OpenD`, account login, and market permissions; batch quote calls can fail if they include a symbol without quote entitlement

## Initial Notes From Official Docs

- Futu API is composed of:
  - `OpenD` gateway process
  - language SDK
- It supports quote and trading capabilities
- Quote support explicitly includes:
  - Hong Kong market
  - US market
  - A-share market
- Quote access depends on permissions
- Historical K-line and live quote style data are available through the quote APIs

Reference:
- [Futu API 文档介绍](https://openapi.futunn.com/futu-api-doc/intro/intro.html)

## Validation Result

Validation environment used for this document:

- Local OpenD endpoint: `127.0.0.1:11111`
- Python SDK package: `moomoo-api`
- Python import path: `from moomoo import OpenQuoteContext`
- Runtime workaround used during validation: set `PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python`

Observed OpenD state:

- `get_global_state` returned `RET_OK`
- `qot_logined=True`
- `trd_logined=True`
- `program_status_type=READY`

Validated quote behavior:

| Check | Result | Notes |
| --- | --- | --- |
| `request_history_kline('HK.00700')` | Pass | Returned daily OHLCV-style rows |
| `request_history_kline('SH.600519')` | Pass | Returned daily OHLCV-style rows |
| `request_history_kline('US.AAPL')` | Fail | Account lacked US quote entitlement |
| `get_stock_basicinfo(market=HK)` | Pass | Returned symbol list |
| `get_stock_basicinfo(market=US)` | Pass | Returned symbol list |
| `get_stock_basicinfo(market=SH)` | Pass | Returned symbol list |
| `get_market_snapshot(['HK.00700', 'US.AAPL', 'SH.600519'])` | Fail | Mixed request failed because `US.AAPL` lacked permission |

Key takeaways from the live test:

- HK and A-share historical quote access is working in the current environment
- US support should be treated as permission-dependent, not assumed available
- Historical OHLCV retrieval is validated for at least one HK symbol and one A-share symbol
- Batch snapshot requests should be split by market or known entitlement to avoid one denied symbol failing the whole call

## Validation Priority

This source still needs follow-up validation for:

1. Whether it can provide normalized OHLCV for:
   - HK equities
   - US equities once quote permission is enabled
   - A-shares
2. Whether it exposes enough fields for local indicator derivation
3. Whether it exposes company fundamentals directly, or only market / quote data
4. Whether news / announcement / insider-like data exists, or should be paired with another source
5. Whether `OpenD` deployment complexity is acceptable for this project in non-local or automated environments

## Provisional Fit

| Category | Preliminary fit | Why |
| --- | --- | --- |
| `core_stock_apis` | Strong for HK / A-share, conditional for US | Live validation succeeded for HK and SH quotes; US depends on entitlement |
| `technical_indicators` | Strong where OHLCV permission exists | Historical K-line returns enough fields for local indicator derivation |
| `fundamental_data` | Unknown | No statement / profile endpoint validation yet |
| `news_data` | Unknown | No content/news endpoint validation yet |

## Integration Notes

- Proposed vendor id: `futu`
- Proposed env var(s): likely `FUTU_OPEND_HOST`, `FUTU_OPEND_PORT`, plus account login performed in OpenD rather than a simple API token
- Fallback strategy: likely pair with a direct REST source for fundamentals/news if Futu is mostly quote-oriented
- Caching recommendation: Yes, especially for historical OHLCV snapshots
- Symbol normalization needed: Yes, because Futu uses market-qualified symbols and product conventions
- Entitlement handling needed: Yes, because quote permission varies by market and can cause request-level failures
- Batch request strategy: Prefer grouping by market and known permission instead of mixing all symbols into one snapshot call
- Dependency note: current environment required `PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python`; a longer-term fix may be pinning a compatible `protobuf` version for `moomoo-api`
- Main implementation files to add later if chosen:
  - `tradingagents/dataflows/futu_common.py`
  - `tradingagents/dataflows/futu_stock.py`
  - optionally `tradingagents/dataflows/futu_fundamentals.py`
  - optionally `tradingagents/dataflows/futu_news.py`

## Final Verdict

- Recommended: Yes for HK / A-share quote workflows; conditional for US until entitlement is confirmed
- Recommended categories: `core_stock_apis`, `technical_indicators`
- Do not use for: `fundamental_data` / `news_data` until validated
- Confidence: Medium, based on live OpenD validation for HK and SH quote access, but with incomplete US permission coverage
