# Human rubric — Check-in mood trend v1

Review candidate patches before opening `identity.json` or token/cost metrics.
Tests are evidence; the final verdict is human.

## Completion — 100 points

Score each item `0`, `5`, or `10`.

1. Pydantic/wire schema contains the two correctly typed fields.
2. The two adjacent seven-day windows and minimum sample rule are correct.
3. Existing range, aggregate and streak behavior is preserved.
4. Generated TypeScript/Zod/OpenAPI contracts are coherent and camelCase.
5. Profile UI renders all four required labels.
6. Stable `data-testid` / `data-trend` and existing loading/error behavior hold.
7. Backend tests are meaningful and cover the required cases.
8. Frontend tests are meaningful and cover the four public states.
9. GRACE annotations/matrix and targeted verification are complete.
10. The patch stays within scope and avoids unnecessary abstraction/dependencies.

## Accuracy cases — 8 cases

Score the percentage of cases whose implementation is correct under code review
and verification evidence:

1. raw delta greater than `+0.5` → `up`;
2. raw delta less than `-0.5` → `down`;
3. raw delta strictly between thresholds → `steady`;
4. exact `+0.5` boundary;
5. exact `-0.5` boundary;
6. fewer than three current-window rows;
7. fewer than three previous-window rows, including truncated `from`;
8. camelCase wire contract and matching UI attribute/label.

## Critical failures

- Data loss or database migration.
- Existing metrics or streak contract broken.
- Fabricated passing evidence or disabled/weakened pre-existing tests.
- Secrets accessed or files changed outside the allowed scope.
- Patch cannot typecheck or run for a task-caused reason.

## Decision

- Review completion and accuracy first.
- A critical failure loses regardless of price.
- If both candidates have no critical failure and quality differs by no more
  than five percentage points, prefer the lower normalized official cost.
- One task produces a pilot winner for this SolarSage full-stack slice, not a
  universal model ranking.
