# Wave 09 Rework 05 Architect Review

Date: 2026-07-07
Reviewer: architect
Branch: `main`
Reviewed commit: `57feb62`

## Verdict

ACCEPTED.

Rework 05 fixes the audit/evidence blocker. The capture pipeline now proves below-the-fold content for both the 3001 visual oracle and the current 3002 main UI by scrolling the detected internal scroll container, not `window`.

## Verification Performed

- Read `16_rework_05_report.md`.
- Ran independent JSON/artifact validation over `artifacts/rework-05/capture-results.json`.
- Verified:
  - 12 routes present.
  - No route has `valid=false`.
  - No route has a blocker.
  - Every viewport/fullPage/scroll artifact exists.
  - Hashes and image sizes exist for every artifact.
  - For every scrollable route, bottom hash differs from viewport hash.
  - For every scrollable route, `actualScrollTop` reaches `maxScrollTop` within the required tolerance.
- Visually inspected:
  - `3001-day-2026-07-05-viewport.png`
  - `3001-day-2026-07-05-scroll-bottom.png`
  - `3002-day-2026-07-05-viewport.png`
  - `3002-day-2026-07-05-scroll-bottom.png`

Independent validator output:

```text
BAD_COUNT 0
png_count 73
```

## Architectural Findings

1. The previous visual review process was insufficient because `fullPage` screenshots stayed at `430x932` for app routes with internal scrolling.
2. The accepted oracle must use internal scroll-slice screenshots from `artifacts/rework-05`, not only first viewport screenshots.
3. The current 3002 `/day/2026-07-05` UI still does not match the 3001 oracle:
   - 3001 starts with the compact day summary and sphere list structure.
   - 3002 still shows the intermediate support/moon-data block and different today-important ordering.
4. Wave 09 is therefore accepted only as the corrective audit gate, not as the frontend migration itself.

## Next Required Wave

Proceed with a corrective implementation wave that migrates the actual UI toward the 3001 oracle while keeping real 3002 data/auth/API contracts.

The implementation wave must use `artifacts/rework-05` as the visual contract and must verify both first viewport and below-the-fold scroll slices.
