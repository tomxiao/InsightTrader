# Source Profile: <source_name>

## Summary

- Source type:
- Official / unofficial:
- Auth model:
- Pricing:
- Main markets:
- Best fit:
- Main limitations:

## Market Coverage

| Market | Supported | Notes |
| --- | --- | --- |
| China A-shares |  |  |
| Hong Kong |  |  |
| US equities |  |  |
| ETFs |  |  |
| Indices |  |  |
| Macro / economy |  |  |
| Crypto / FX |  |  |

## Tool Coverage

| TradingAgents tool | Supported | Native or derived | Notes |
| --- | --- | --- | --- |
| `get_stock_data` |  |  |  |
| `get_indicators` |  |  |  |
| `get_fundamentals` |  |  |  |
| `get_balance_sheet` |  |  |  |
| `get_cashflow` |  |  |  |
| `get_income_statement` |  |  |  |
| `get_news` |  |  |  |
| `get_global_news` |  |  |  |
| `get_insider_transactions` |  |  |  |

## Output Normalization Notes

### OHLCV

- Native fields:
- Missing fields:
- Can normalize to current `get_stock_data` output:

### Technical Indicators

- Native indicators:
- If not native, can derive from OHLCV:
- Can normalize to current `get_indicators` output:

### Fundamentals

- Overview fields:
- Statement fields:
- Frequency support:
- Can normalize to current `fundamental_data` outputs:

### News

- Ticker news:
- Macro/global news:
- Insider transactions:
- Can normalize to current `news_data` outputs:

## Agent Compatibility

| Agent | Usable | Why |
| --- | --- | --- |
| Market analyst |  |  |
| Fundamentals analyst |  |  |
| News analyst |  |  |
| Full pipeline |  |  |

## Integration Notes

- Proposed vendor id:
- Proposed env var:
- Fallback strategy:
- Caching recommendation:
- Symbol normalization needed:
- Main implementation files to add:

## Final Verdict

- Recommended:
- Recommended categories:
- Do not use for:
- Confidence:
