---
name: report-backtest
description: Generate historical InsightTrader lite-team reports for a specified ticker, resume interrupted report batches, and run the backtest pipeline under backtest/. Use when the user wants to backtest InsightTrader reports, batch-generate historical analysis reports, rerun a report batch after interruption, or evaluate a ticker with the report-driven backtest workflow.
---

# Report Backtest

Use this skill to run the repository's report-driven backtest workflow in [backtest](../../../backtest).

## Scope

This skill covers:

- generating historical `lite team` reports with [generate_report_batch.py](../../../backtest/generate_report_batch.py)
- resuming interrupted report batches with `--resume-dir`
- running the report backtest with [run_report_backtest.py](../../../backtest/run_report_backtest.py)
- explaining where outputs are written and how to inspect them
- using `deepseek-chat` as the default model for historical report generation

This skill does not cover:

- changing backtest strategy logic unless the user explicitly asks for code changes
- validating live trading performance
- portfolio sizing or capital allocation beyond the current single-signal execution rules

## Required Inputs

Before executing this skill, you must first obtain all three of the following from the user:

1. ticker
2. backtest date range
3. sampling frequency

Valid sampling frequency examples:

- `daily`
- `weekly`

If any one of these three inputs is missing, do not start report generation or backtest execution yet. Ask the user to provide the missing item(s) first.

## Standard Workflow

1. Generate a batch of historical reports for one ticker:
   - choose `--sample-mode weekly` or `--sample-mode daily`
   - use `--step` only with `daily`
2. If the generation was interrupted, resume with:
   - `--resume-dir backtest\output\MMDD-HHmm-TICKER`
3. Read `report_manifest.csv` from the batch output directory and collect each `decision_path`
4. Run the backtest script against those `decision_path` values
5. Report:
   - the batch output directory
   - the backtest output directory
   - high-level summary from `summary.json`
   - notable entries from `trades.csv` when relevant

## Output Conventions

- each batch run writes to `backtest/output/MMdd-HHmm-TICKER/`
- generated reports are copied into `backtest/output/MMdd-HHmm-TICKER/reports/YYYY-MMdd-TICKER/`
- each backtest run also writes to a fresh `backtest/output/MMdd-HHmm-TICKER/`

## Commands

Generate weekly reports:

```powershell
.\.venv\Scripts\python.exe backtest\generate_report_batch.py `
  --ticker AXTI `
  --start-date 2026-01-01 `
  --end-date 2026-04-17 `
  --sample-mode weekly
```

Generate daily reports:

```powershell
.\.venv\Scripts\python.exe backtest\generate_report_batch.py `
  --ticker AXTI `
  --start-date 2026-01-01 `
  --end-date 2026-04-17 `
  --sample-mode daily `
  --step 3
```

Resume an interrupted batch:

```powershell
.\.venv\Scripts\python.exe backtest\generate_report_batch.py `
  --ticker AXTI `
  --start-date 2026-01-01 `
  --end-date 2026-04-17 `
  --sample-mode weekly `
  --resume-dir backtest\output\0419-2234-AXTI
```

Run backtest from generated reports:

```powershell
.\.venv\Scripts\python.exe backtest\run_report_backtest.py `
  --report backtest\output\0419-2234-AXTI\reports\2026-0102-AXTI\2_decision\summary.md `
  --report backtest\output\0419-2234-AXTI\reports\2026-0105-AXTI\2_decision\summary.md `
  --end-date 2026-04-19 `
  --max-holding-days 60
```

## Usage Notes

- Prefer `tushare` as the historical price source unless the user explicitly wants `--ohlcv-csv`
- Historical report generation defaults to `deepseek-chat`
- Batch backtest runs use `username=backtest`
- Keep the ticker explicit in every run
- When resuming, do not create a new batch directory; reuse the exact `--resume-dir`
- When generation finishes, inspect:
  - `batch_metadata.json`
  - `report_manifest.csv`
- When backtest finishes, inspect:
  - `summary.json`
  - `trades.csv`
  - `signals.csv`

## Progress Expectations

During report generation, the script prints report-level progress using:

- `SKIP`
- `RUN`
- `DONE`
- `FAIL`

Reflect that status clearly in your response when summarizing a run.
