---
name: daily-deploy
description: Execute the routine InsightTrader remote production deployment workflow using the repository's established continuous deploy process. Use when the user asks to execute a remote deploy, deploy production, deploy the backend, deploy the frontend, or deploy the current changes to the production host. If deployment fails, do not auto-fix anything; only report the result, the failing step, and concrete next-step suggestions.
---

# Daily Deploy

Use this skill for routine InsightTrader deployment work that follows the repository's established production process.

## Scope

This skill covers:

- backend-only deploys
- frontend-only deploys
- combined frontend and backend deploys
- environment-file refreshes
- routine deploy status checks and conclusion reporting

This skill does not cover:

- infra redesign
- Dockerfile refactors
- Nginx redesign
- certificate rotation planning
- automatic remediation after a failed deploy

## Source Of Truth

Read this doc before executing deployment steps:

- [deploy/CONTINUOUS_DEPLOY.md](../../../deploy/CONTINUOUS_DEPLOY.md)

## Core Rules

1. Use the existing repository deployment flow first.
   Prefer the checked-in scripts and commands already referenced in the deploy docs.
2. Keep deployment mode explicit.
   Decide whether the change is backend-only, frontend-only, combined, env-only, or nginx-only before running anything.
3. Update the deploy version file before a normal deploy.
   Follow the documented `deploy/VERSION` convention when the deploy docs call for it.
4. Treat `uv.lock` as a deployment input.
   If dependency definitions changed, make sure the committed `uv.lock` is current before deployment.
5. Do not improvise auto-fixes.
   If deployment fails, stop at diagnosis. Report what failed, where it failed, and what should be checked next.
6. Do not claim success without the documented verification step.
   Follow the deploy doc's final verification command for the chosen scenario.
7. Deploy with progress visibility.
   For remote or long-running deployment steps, do not silently wait for completion. Start the documented deploy command, then keep checking status signals and report progress during the run.

## Progress Reporting

When a deploy may take more than a brief moment, especially remote Docker builds:

- start the documented deploy step first
- then periodically check the most relevant status signals for that scenario
- send concise progress updates while the deploy is running
- if the user interrupts, resume from the last verified state instead of blindly re-running everything

Typical checks include:

- remote process status
- build or service logs
- image timestamps
- `docker compose ps`
- health endpoints such as `/health`

The default habit is:

- deploy
- check
- report
- repeat until success or failure is clear

## Failure Policy

If a deployment step fails:

- do not patch code automatically
- do not edit remote configuration automatically unless the user explicitly asks
- do not retry with ad hoc command changes just to “make it work”
- return:
  - overall result: failed
  - exact failing step
  - relevant error lines
  - likely cause
  - concrete next-step suggestions

The default posture is report-and-stop, not auto-fix.

## Typical Workflow

1. Classify the deploy scope.
2. Read the matching section in [deploy/CONTINUOUS_DEPLOY.md](../../../deploy/CONTINUOUS_DEPLOY.md).
3. Run the documented commands in order.
4. For remote or long-running steps, keep checking progress and report intermediate status.
5. Run the documented verification command.
6. Return a short deployment summary.

## Output Expectations

For a successful deploy, report:

- deploy scope
- commands or script path used
- verification result
- final conclusion: success

For a failed deploy, report:

- deploy scope
- failing step
- key error output
- final conclusion: failed
- suggested next checks
