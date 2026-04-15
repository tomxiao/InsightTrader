---
name: prd-writer
description: Draft or refine product requirement documents (PRDs) in a structured, engineering-ready style. Use when Codex needs to write a new PRD, upgrade an existing requirement doc, normalize a rough brief into PRD format, or keep product, frontend, backend, design, and test audiences aligned with clear scope, rules, interface needs, acceptance criteria, and risks.
---

# PRD Writer

Write PRDs in a stable, implementation-friendly structure modeled after the InsightTrader requirement docs.

## Workflow

1. Read the source material first.
   Source material may be an existing PRD, a brief, chat notes, a feature request, or code context.
2. Classify the request.
   Decide whether the user needs:
   - a brand-new PRD,
   - an upgraded version of an existing PRD,
   - a partial rewrite of one section,
   - or a normalization pass that turns informal notes into PRD format.
3. Preserve document intent.
   Keep the product positioning, version goal, and explicit non-goals stable unless the user asks to change them.
4. Write in canonical PRD order.
   Use the section order in [references/prd-structure.md](references/prd-structure.md) unless there is a strong reason to omit a section.
5. Make each section decision-bearing.
   Avoid generic filler. Every section should reduce ambiguity for product, engineering, design, or testing.
6. Add engineering hooks.
   When the change touches implementation, name affected modules, page scopes, data fields, state rules, integration points, and test expectations.
7. Finish with quality checks.
   Verify scope boundaries, edge cases, acceptance criteria, and wording consistency before returning the draft.

## Writing Rules

- Use short declarative sentences.
- Prefer stable section headings and numbering.
- Write goals, non-goals, and scope as separate concepts.
- Distinguish user-facing behavior from internal implementation.
- State defaults, exceptions, and fallback behavior explicitly.
- When naming roles, message types, states, or APIs, keep identifiers consistent throughout the document.
- When backend or frontend behavior is constrained, write the rule directly instead of implying it.
- When something should not happen, write it as a concrete prohibition.
- When a requirement depends on runtime conditions, describe the trigger, system behavior, and expected fallback.

## PRD-Specific Heuristics

- Start from product change, not UI chrome.
- Explain why the current version is insufficient before describing the new version.
- Convert vague goals like "improve experience" into observable outcomes.
- Treat "适用范围", "影响范围", and "不受影响范围" as separate decisions.
- For message, state-machine, or workflow products, include mapping tables when rules depend on message types, statuses, stages, or roles.
- For iterative versioning such as `v1.1` or `v1.2`, describe what remains unchanged from the prior version.
- If the document affects engineering handoff, include minimum data/interface requirements and test coverage expectations.

## When To Read References

- Read [references/prd-structure.md](references/prd-structure.md) when drafting a full PRD or normalizing a rough draft into the house style.
- Read [references/prd-checklist.md](references/prd-checklist.md) before finalizing when the document will be used by engineering, design, QA, or cross-functional reviewers.

## Output Expectations

- For a full PRD, return a complete markdown draft with stable headings.
- For a revision, preserve unaffected sections and only rewrite what the new version changes.
- For a review request, identify ambiguity, missing decisions, and handoff risks before proposing edits.
