# Agent Input Checklist

Use this checklist before declaring any data source safe for production integration.

## Market Analyst

- Can fetch historical OHLCV for the target market
- Date filtering is supported without look-ahead bias
- Fields can be normalized to: `Date, Open, High, Low, Close, Volume`
- Either:
  - native technical indicators are available, or
  - OHLCV is rich enough to derive indicators locally
- Supports exchange-qualified symbols or can be normalized reliably

## Fundamentals Analyst

- Can return a readable company overview or key/value fundamentals block
- Can return balance sheet data
- Can return cash flow data
- Can return income statement data
- Statement dates can be filtered to `curr_date` to avoid future leakage
- Output can be normalized to a stable table-like text format

## News Analyst

- Can return ticker-specific news
- Can return broader market / macro news
- Source timestamps are available or inferable
- Output can include source/title/link/summary cleanly
- Optional: insider transaction or similar event feed exists

## Operational Checks

- Authentication model is understood
- Rate limits are documented
- Error modes are predictable enough for fallback logic
- Response format is stable enough for LLM consumption
- Caching strategy is clear

## Decision Rules

- Mark `usable now` only if required data exists and normalization is straightforward
- Mark `usable with derivation` if raw data exists but indicators / summaries must be computed locally
- Mark `not suitable` if major categories are missing or formats are too unstable
