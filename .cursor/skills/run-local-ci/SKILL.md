---
name: run-local-ci
description: Run the TradingAgents local CI workflow through `scripts/local_ci.py`, which now auto-fixes by default, summarize lint, unittest, and build results, and optionally continue through commit-message drafting and `git commit` when the user explicitly asks to submit changes. Use when the user asks to 跑本地CI, 执行本地检查, 跑 lint/test/build, 验证提交前检查, run local CI, fix local CI failures, or wants a commit-ready workflow after CI.
---

# Run Local CI

## Purpose
Execute the repository's standard local CI workflow and report the outcome in a concise, actionable way.
When the user explicitly asks to commit as part of the same request, continue through commit-message drafting and `git commit` after CI passes.

## Default behavior
- Run from the repo root.
- Prefer the existing script `python scripts/local_ci.py`.
- `python scripts/local_ci.py` now enables auto-fix by default.
- Use `python scripts/local_ci.py --no-fix` only if the user explicitly asks for a check-only run without modifying files.
- Do not invent alternate lint/test/build command chains unless the script itself is broken.
- Do not create a git commit unless the user explicitly asks to commit.

## Before running
1. Check whether another local CI command is already running in an existing terminal.
2. If a duplicate run is already active, inspect that run first instead of starting a second one.
3. If the script fails because dev dependencies are missing, install them with:

```bash
python -m pip install -e ".[dev]"
```

4. After installing missing dependencies, rerun the same local CI command.

## Command choices
Use one of these commands:

```bash
python scripts/local_ci.py
```

```bash
python scripts/local_ci.py --no-fix
```

## What the workflow covers
The script is the source of truth. Today it runs:
- `ruff check`
- `python -m unittest discover -s tests -p "test_*.py"`
- `python -m build`

By default, it first runs:
- `ruff format`
- `ruff check --fix --select E4,E7,E9,F,I`

## If the run fails
1. Identify the first failing stage: lint, tests, or build.
2. Summarize the concrete failing file, test, or error message.
3. Distinguish between:
   - new failure caused by the current changes
   - pre-existing failure in the repository
4. Only start editing files if the user asked to fix the failure.
5. After a fix, rerun local CI to confirm the result.

## Post-CI commit flow
Use this section only when the user explicitly asks to commit, submit, or create a git commit as part of the local CI workflow.

1. Run the local CI workflow first.
2. Only continue to commit creation if local CI passes.
3. Before committing, inspect repository state with:
   - `git status --short`
   - `git diff --staged`
   - `git diff`
   - `git log -5 --oneline`
4. Draft a concise commit message that matches repository style and explains the purpose of the change.
5. Stage the intended files.
6. Create the commit.
7. Run `git status --short` again and report whether the commit succeeded.
8. If commit hooks modify files or reject the commit, fix the issue, rerun local CI if needed, and then create a new commit according to the active git safety rules.

## Commit response format
When a commit was requested, also include:
- drafted commit message
- whether the commit was created
- post-commit git status
- first blocker if commit creation failed

## Response format
Reply in Chinese and keep it compact. Include:
- command used
- whether auto-fix was used
- lint result
- test result
- build result
- overall status
- first failure cause if any
- if applicable, commit message and commit status

## Notes
- Prefer reporting the first actionable failure instead of dumping the full command output.
- If build passes but tests fail, still say build was not reached by the script unless you ran it separately.
- If you run an extra verification command outside `scripts/local_ci.py`, say so explicitly.
