# PRD Checklist

Run this checklist before finalizing a PRD.

## Scope

- Is the version goal explicit?
- Are goals and non-goals separated cleanly?
- Does the document say what remains unchanged from the prior version?
- Are impacted and non-impacted areas both stated?

## Product Clarity

- Does the background explain what problem exists now, not just what will be built?
- Does each major requirement answer a real ambiguity?
- Are user-facing behaviors written in product language rather than implementation jargon?

## Engineering Handoff

- Are affected modules, services, pages, or files named when needed?
- Are data fields, message types, task states, or identifiers defined consistently?
- Are fallback rules, stale states, failure states, and recovery behavior specified?
- Are interface or event dependencies called out when the feature crosses frontend and backend?

## Interaction Quality

- Does the document distinguish default behavior from deeper or optional behavior?
- Are continuous flows such as polling, status updates, replay, and re-entry described?
- Are edge cases covered for network failure, long-running tasks, and concurrent actions?

## Acceptance Quality

- Can QA derive test cases directly from the acceptance section?
- Are experiential claims translated into observable outcomes?
- Are there any requirements that sound important but cannot be verified?

## Writing Quality

- Are section numbers and headings stable?
- Are terms reused consistently across the document?
- Is there any filler that does not reduce ambiguity?
- Does the final version read like a decision document rather than brainstorming notes?
