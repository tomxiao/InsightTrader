# InsightTrader

InsightTrader is a multi-agent trading research project that includes:

- `ta_service`: FastAPI backend for mobile chat, task orchestration, and API contracts
- `mobile_h5`: mobile web frontend
- `tradingagents`: trading analysis and report generation runtime

This repository is deployed with Docker in production. Backend image builds rely on:

- `pyproject.toml`
- `uv.lock`
- this `README.md`

If dependency definitions change, update `uv.lock` before deployment so `uv sync --frozen` can reproduce the intended runtime environment.
