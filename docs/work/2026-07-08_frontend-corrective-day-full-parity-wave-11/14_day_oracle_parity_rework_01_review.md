# Wave 11 Day Oracle Parity Rework 01 Review

Status: **ACCEPTED**

Reviewed commits:

- Implementation rework: `99cbcce6d8a3be05e3f169542a2253018260b13d`
- Report/current head at review time: `8bfe134`

Architect verification:

```bash
npx vitest run __tests__/lib/display/sphere-labels.test.ts
# 8 passed

npx vitest run __tests__/components/TodayScreen.test.tsx
# 14 passed

E2E_BASE_URL=http://127.0.0.1:7777 npx playwright test e2e/mock-visual/day.spec.ts
# 8 passed
```

## Accepted Findings

### Day summary shell

The day summary card now uses the 3001 compact structure:

- date/weekday inside the card header;
- real day status on the right side of the header;
- one-line real status below;
- compact real-data fact rows below the divider.

The large standalone emoji/title stack from the rejected version is gone.

### Concrete advice contract

The concrete advice section now:

- builds 12 canonical product rows in fixed oracle order;
- maps backend sphere keys through explicit product bucket keys, not display label comparison;
- maps `home_family_roots` and `home_family` into canonical buckets instead of dropping them into a non-oracle `Семья` row;
- marks buckets without real score as unavailable instead of fabricating neutral scored advice;
- counts only real scored rows for `благоприятно` / `осторожно`;
- keeps raw/debug labels out of the UI.

### Unknown sphere fallback

`getSphereLabel()` now uses safe Russian generic fallback text instead of title-cased English. The unit tests cover this.

### Day chart

The chart keeps the 3001 visual shell, Russian aspect legend, interactive popover, and now uses Russian sign labels in accessibility labels as well.

### History widget

The full-scroll evidence and `summary-implementation.json` show the 3001-style `БЛИЖАЙШИЕ ДНИ` card with the curated space-history event.

## Non-Blocking Notes

`candidate-05-reading-why-week-history.png` still starts around chart/reading rather than fully centered on week/history. This is not blocking this acceptance because:

- `candidate-00-full-scroll.png` contains the bottom/history section;
- `summary-implementation.json` includes the parsed history heading/card text;
- product code and e2e behavior are verified.

For future visual baselines, capture scripts should make section screenshots stricter so file names always match the visible section.

## Decision

Wave 11 `/day` oracle parity is accepted for the current scope. The implementation can move to deployment/restart or the next frontend oracle wave.

