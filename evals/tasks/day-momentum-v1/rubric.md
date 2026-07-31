# Human rubric — Day support momentum v1

Review candidate patches before opening `identity.json` or token/cost metrics.
Tests are evidence; the final verdict is human.

## Completion — 100 points

Score each item `0`, `5`, or `10`.

1. Schema exposes the two correctly typed fields with camelCase wire names.
2. The two two-day windows and the `<3` insufficient rule are correct.
3. Classification thresholds (`±5.0`, inclusive) use the raw unrounded delta.
4. Momentum works identically in absolute and relative modes.
5. Existing relative-status behavior (hysteresis, overrides, bands) is preserved.
6. Generated TypeScript/Zod/OpenAPI contracts are coherent and camelCase.
7. Backend tests are meaningful and cover the required cases.
8. GRACE annotations/matrix and targeted verification are complete.
9. No caller changes were needed or made; the change is purely additive.
10. The patch stays within scope and avoids unnecessary abstraction/dependencies.

## Accuracy cases — 8 cases

Score the percentage of cases whose implementation is correct under code review
and verification evidence:

1. raw delta greater than `+5.0` → `rising`;
2. raw delta less than `-5.0` → `falling`;
3. raw delta strictly between thresholds → `flat`;
4. exact `+5.0` boundary → `rising`;
5. exact `-5.0` boundary → `falling`;
6. raw `5.004` → `rising` with reported delta `5.0` (rounding never classifies);
7. history of exactly 2 entries → `insufficient` and `null`;
8. history of exactly 3 entries in absolute mode → momentum computed.

## Critical failures

- Existing relative-status behavior, statuses, or wire contract broken.
- Fabricated passing evidence or disabled/weakened pre-existing tests.
- Secrets accessed or files changed outside the allowed scope.
- Patch cannot typecheck or run for a task-caused reason.

## Decision

- Review completion and accuracy first.
- A critical failure loses regardless of price.
- If both candidates have no critical failure and quality differs by no more
  than five percentage points, prefer the lower normalized official cost.
- One task produces a pilot winner for this backend-algorithm slice, not a
  universal model ranking.
