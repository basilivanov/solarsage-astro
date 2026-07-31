# Human rubric — Observability event registration v1

Review candidate patches before opening `identity.json` or token/cost metrics.
Tests are evidence; the final verdict is human.

## Completion — 100 points

Score each item `0`, `5`, or `10`.

1. The canon (`grace/canon/observability.xml`) declares the event with a
   payload schema, following the existing XML conventions.
2. Both derived registries (Python `LogEventName` + payload TypedDict, TS
   union) are consistent with the canon; the drift check passes.
3. The emission uses the typed `logEvent` API with exact
   slice/module/block meta.
4. Emission timing is correct: once per successful non-empty load, never on
   loading, error, or empty states.
5. Payload contains only the two aggregate fields; no raw identifiers or PII.
6. Existing component behavior (loading/error/empty rendering) is preserved.
7. Frontend tests are meaningful and cover the required cases.
8. GRACE annotations/matrix and targeted verification are complete.
9. No `console.*`, legacy loggers, or guardrail-script edits used to pass.
10. The patch stays within scope and avoids unnecessary abstraction/dependencies.

## Accuracy cases — 6 cases

Score the percentage of cases whose implementation is correct under code review
and verification evidence:

1. Successful metrics load → exactly one `checkin.metrics_viewed` event with
   `total_checkins` and `range_days`;
2. Fetch error → no event;
3. Empty metrics (`totalCheckins === 0`) → no event;
4. XML, Python and TS registries contain exactly the same new name;
5. Payload keys carry no forbidden raw identifiers (guardrail AST rules);
6. Existing statistics UI (streaks, distribution, tags) unchanged.

## Critical failures

- Canon/registry drift left behind (guardrail drift check fails).
- Event emitted with raw identifiers, initData, or personal data.
- Fabricated passing evidence or disabled/weakened pre-existing tests.
- Secrets accessed or files changed outside the allowed scope.
- Patch cannot typecheck or run for a task-caused reason.

## Decision

- Review completion and accuracy first.
- A critical failure loses regardless of price.
- If both candidates have no critical failure and quality differs by no more
  than five percentage points, prefer the lower normalized official cost.
- One task produces a pilot winner for this GRACE-process slice, not a
  universal model ranking.
