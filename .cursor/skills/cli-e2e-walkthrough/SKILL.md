---
name: cli-e2e-walkthrough
description: Run a real TradingAgents CLI end-to-end walkthrough with a user-specified ticker, force agent output language to Chinese, inspect run_trace.jsonl/stage_events.jsonl/route_events.jsonl, and summarize stalls, vendor routing, final outcome, and generated reports. Use when the user asks for CLI 端到端走查, 真实 CLI 验证, 真实 E2E, 跑一遍 CLI, or wants to trace a real analysis run.
---

# CLI E2E Walkthrough

## Purpose
Run a real `cli.main` analysis for this repo without editing source files, then use the generated traces and logs to explain what happened.

## Required input
- The user must provide a `ticker`.
- If the ticker is missing, ask for it before running anything.

## Fixed defaults
- Force `output_language` to `Chinese`.
- Prefer a real run through `cli.main.run_analysis()`, not a mocked graph.
- Script the selection step instead of manually driving interactive prompts.

## Run workflow
1. Check whether a previous CLI run is already active before starting another one.
2. Launch the repo virtualenv Python and monkey-patch `cli.main.get_user_selections()` at runtime.
3. Keep the run real:
   - Use the real graph.
   - Use the real data vendors.
   - Use the real configured LLM provider/backend that already works in this repo unless the user asks otherwise.
4. Set at least these scripted selections:
   - `ticker`: user-provided ticker
   - `analysis_date`: use the user-provided date if any, otherwise today's date
   - `analysts`: `[AnalystType.MARKET, AnalystType.NEWS, AnalystType.FUNDAMENTALS]`
   - `research_depth`: `1` unless the user asks for something else
   - `output_language`: `Chinese`
5. Stub any follow-up `typer.prompt()` confirmations with deterministic answers so the run can finish unattended.
6. Print clear sentinel markers before and after the run so terminal progress is easy to monitor.

## Command pattern
Use an inline Python script piped into the repo virtualenv interpreter. Follow this shape and fill in the ticker/date/provider values from context:

```python
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(".env"))

import cli.main as cli_main
from cli.models import AnalystType

cli_main.get_user_selections = lambda: {
    "ticker": "<TICKER>",
    "analysis_date": "<YYYY-MM-DD>",
    "analysts": [AnalystType.MARKET, AnalystType.NEWS, AnalystType.FUNDAMENTALS],
    "research_depth": 1,
    "llm_provider": "<provider>",
    "backend_url": "<backend_url>",
    "shallow_thinker": "<fast_model>",
    "deep_thinker": "<deep_model>",
    "google_thinking_level": None,
    "openai_reasoning_effort": None,
    "anthropic_effort": None,
    "output_language": "Chinese",
}

responses = iter(["N", "N"])
cli_main.typer.prompt = lambda *args, **kwargs: next(responses)

print("CLI_REAL_E2E_START")
cli_main.run_analysis()
print("CLI_REAL_E2E_DONE")
```

## What to monitor
- Terminal completion status and exit code
- `results/<ticker>_<yyyy_mmdd_hhmm>/run_trace.jsonl`
- `results/<ticker>_<yyyy_mmdd_hhmm>/stage_events.jsonl`
- `results/<ticker>_<yyyy_mmdd_hhmm>/route_events.jsonl`
- `results/<ticker>_<yyyy_mmdd_hhmm>/message_tool.log`
- `results/<ticker>_<yyyy_mmdd_hhmm>/reports/*.md`
- If two runs start within the same minute, expect a numeric suffix such as `_02`

## How to analyze the run
1. Capture the final `run_id`.
2. Summarize stage progression in order:
   - `analysts.market`
   - `analysts.news`
   - `analysts.fundamentals`
   - `research.debate`
   - `trader.plan`
   - `risk.debate`
   - `portfolio.decision`
3. Call out any `stage.stalled` events and whether each stage later completed.
4. Inspect route events for:
   - chosen vendor
   - fallback behavior
   - error-like outcomes such as `error`, `error_string`, `rate_limit`, `blocked`, `exhausted`
5. Cross-check route traces against `message_tool.log` to explain user-visible slowdowns or failures.
6. Confirm whether final reports were generated and identify the final portfolio decision.

## Response format
Reply in Chinese and keep the summary concise. Include:
- ticker
- date
- run_id
- exit code
- total elapsed time if available
- completed stages
- stalled stages and whether they recovered
- notable vendor routing findings
- final decision
- key report files written

## Notes
- Do not edit repo files just to run the walkthrough.
- If a run is already active for the same purpose, inspect that run first instead of starting a duplicate.
- If the run hangs, use the trace files to say exactly which stage or vendor call is stuck instead of guessing.
