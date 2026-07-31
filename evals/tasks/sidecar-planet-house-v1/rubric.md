# Human rubric — Sidecar planet house v1

Review candidate patches before opening `identity.json` or token/cost metrics.
Tests are evidence; the final verdict is human.

## Completion — 100 points

Score each item `0`, `5`, or `10`.

1. Sidecar natal response planets carry a correctly typed `house` (int|null).
2. Sidecar house computation matches cusp intervals including wraparound.
3. The computation lives in the calculation path, not the HTTP layer.
4. API prefers a valid provided `house` over recomputation.
5. API fallback preserves old-sidecar behavior exactly (absent field).
6. API fallback handles invalid `house` values without crashing or misrouting.
7. Natal context path passes the field through; old cached contexts stay valid.
8. Transit-to-natal mapping and all other sidecar endpoints are untouched.
9. Tests on both sides are meaningful and cover the required cases.
10. GRACE annotations/matrix complete; patch within scope, no new dependencies.

## Accuracy cases — 8 cases

Score the percentage of cases whose implementation is correct under code review
and verification evidence:

1. Planet near the 12th/1st cusp boundary lands in the correct house;
2. Both supported house systems produce correct `house` values;
3. Payload with valid `house` → normalization uses it (no recomputation);
4. Payload without `house` (old sidecar) → identical signals as before;
5. Payload with `house: 0`, `13`, or a non-integer → fallback, no exception;
6. Houses unavailable on the chart → `house: null`, API falls back;
7. Existing natal response fields and `houses` list unchanged;
8. Old cached natal contexts (no `house`) still normalize correctly.

## Critical failures

- Old-sidecar compatibility broken (missing `house` crashes or changes output).
- Transit semantics or any other endpoint behavior changed.
- Existing sidecar/API tests weakened, skipped, or broken by the patch.
- Fabricated passing evidence.
- Secrets accessed or files changed outside the allowed scope.
- Patch cannot run for a task-caused reason.

## Decision

- Review completion and accuracy first.
- A critical failure loses regardless of price.
- If both candidates have no critical failure and quality differs by no more
  than five percentage points, prefer the lower normalized official cost.
- One task produces a pilot winner for this cross-codebase slice, not a
  universal model ranking.
