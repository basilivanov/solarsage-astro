# Human rubric — UI semantic contract disclosure v1

Review candidate patches before opening `identity.json` or token/cost metrics.
Tests are evidence; the final verdict is human.

## Completion — 100 points

Score each item `0`, `5`, or `10`.

1. All three rendered states expose the root testid and correct `data-state`.
2. Loading keeps `role="status"`/`aria-busy`, error keeps `role="alert"`.
3. Empty state intentionally renders nothing (no invented card).
4. Disclosure button has the exact label, testid, `aria-expanded`,
   `aria-controls` and starts collapsed.
5. Disclosure region has the matching id/testid and is hidden while collapsed.
6. The three static methodology facts are present and accurate.
7. Existing visual layout and rendered content are preserved.
8. Tests are meaningful: they assert the DOM contract, not CSS or snapshots.
9. GRACE annotations/matrix and targeted verification are complete.
10. The patch stays within scope and avoids unnecessary abstraction/dependencies.

## Accuracy cases — 7 cases

Score the percentage of cases whose implementation is correct under code review
and verification evidence:

1. Loading state exposes `data-state="loading"` with `role="status"`;
2. Error state exposes `data-state="error"` with `role="alert"`;
3. Ready state exposes `data-state="ready"` with all existing content;
4. Default render: toggle has `aria-expanded="false"`, region hidden;
5. After click: `aria-expanded="true"`, region visible; second click collapses;
6. `aria-controls="checkin-stats-methodology"` resolves to the region's id;
7. Methodology text mentions the 30-day window, the 1–5 mood scale and the
   consecutive-day streak rule.

## Critical failures

- Existing rendered behavior or other screens broken.
- Tests asserting LLM/dynamic text, CSS classes, or React internals instead of
  the public contract.
- Fabricated passing evidence or disabled/weakened pre-existing tests.
- Secrets accessed or files changed outside the allowed scope.
- Patch cannot typecheck or run for a task-caused reason.

## Decision

- Review completion and accuracy first.
- A critical failure loses regardless of price.
- If both candidates have no critical failure and quality differs by no more
  than five percentage points, prefer the lower normalized official cost.
- One task produces a pilot winner for this UI-contract slice, not a universal
  model ranking.
