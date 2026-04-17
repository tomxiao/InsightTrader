---
name: local-api-ci
description: Run InsightTrader local CI when the goal is to increase confidence that frontend and backend still start cleanly, while keeping the actual automated test scope limited to ta_service API contracts. Use when validating code changes before handoff, before commit, or before asking someone else to verify the app manually.
---

# Local API CI

Use this skill to run the project-local CI flow without starting any services and without doing real integration validation.

## What This CI Covers

- Backend syntax checks for `ta_service` entrypoints, route files, and the API test suite
- Backend app import sanity check via `from ta_service.main import app`
- `ta_service` API contract tests under [tests/ta_service_api](../../../tests/ta_service_api)
- Frontend type-check and production build to increase confidence that the frontend still starts cleanly

## What This CI Does Not Cover

- Starting backend or frontend services
- Real MongoDB, Redis, LLM, vendor, or worker validation
- Browser-based verification
- End-to-end analysis task execution
- Any automatic code changes, auto-fixes, or opportunistic edits while running the check flow

## Workflow

1. Run the single script: [scripts/local-ci.ps1](../../../scripts/local-ci.ps1)
2. If it fails, report the first failing step and the relevant error lines.
3. If it passes, summarize:
   - backend import check passed
   - `ta_service` API contract tests passed
   - frontend type-check/build passed
4. Do not modify code as part of this skill. The job is limited to checks, confirmation, and result reporting.
5. Do not claim the app was fully verified in a real environment. The result only means the codebase is in a strong pre-start state.

## When To Use

- Before commit when backend API or frontend startup safety matters
- After changing `ta_service` routes, models, deps, or API contracts
- After changing mobile H5 code in a way that could break compile-time startup

## Output Expectations

- Report the exact command/script used
- Report pass/fail by step
- Call out warnings separately from failures
