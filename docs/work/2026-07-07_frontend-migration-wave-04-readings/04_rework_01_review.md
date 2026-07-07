# Architect Review: Wave 04 Rework 01 `/readings` Overview

Date: 2026-07-07
Status: ACCEPTED
Reviewed branch: `wave-04-readings-visual-migration`
Reviewed commit: `84ebc85`
Base review: `docs/work/2026-07-07_frontend-migration-wave-04-readings/02_arch_review.md`
Rework TZ: `docs/work/2026-07-07_frontend-migration-wave-04-readings/03_rework_01_TZ.md`

## Verdict

Wave 04 is accepted.

The rework resolves the blocking findings from `02_arch_review.md`:

- Coming cards now use stable key-based selectors from the product catalog: `readings-card-month`, `readings-card-year`, `readings-card-synastry`.
- Unit and e2e tests no longer depend on localized Russian card titles for public selectors.
- `__tests__/components/ReadingsScreen.test.tsx` now has GRACE `AI_HEADER`, `START_MODULE_CONTRACT`, and `START_MODULE_MAP`.
- `/readings` has a visible, narrowly scoped presentation delta: gradient heading treatment and available-card surface/glow polish.
- CSS changes are limited to `/readings` helpers in `app/globals.css`; no root layout/theme/system runtime changes were made.
- The agent report now explicitly states that `3002`, systemd, nginx, and bot config were not changed.
- Runtime mock guardrails remain intact: no MSW, runtime mock mode, mock-preview API, `DEMO_NATAL_RESPONSE`, `SynastryDemo`, `CelebrityCompatibility`, hardcoded compatibility calculators, or `lib/mocks/*` product imports were introduced.

## Fresh Verification

Architect reran these gates on `84ebc85`:

```bash
git diff --check main..HEAD
```

Result: passed, exit code 0.

```bash
git diff --check
```

Result: passed, exit code 0.

```bash
pnpm exec tsc --noEmit --pretty false
```

Result: passed, exit code 0.

```bash
npx vitest run __tests__/components/ReadingsScreen.test.tsx __tests__/api/readings.test.ts __tests__/guardrails/no-runtime-mocks.test.ts
```

Result: 3 files passed, 15 tests passed.

```bash
npx vitest run
```

Result: 85 files passed, 882 tests passed. Existing unrelated React `act(...)` warnings appeared in older tests.

```bash
E2E_BASE_URL=http://localhost:3000 pnpm exec playwright test e2e/mock-visual/readings.spec.ts --project=mobile
```

Result: 4 passed.

```bash
E2E_BASE_URL=http://localhost:3000 pnpm exec playwright test e2e/mock-visual/day.spec.ts:225 --project=mobile
```

Result: 1 passed.

```bash
E2E_BASE_URL=http://localhost:3000 pnpm exec playwright test e2e/mock-visual --project=mobile
```

Result: 16 passed.

Note: the first full `e2e/mock-visual` run during review had one transient failure in the pre-existing `/day` negative-proof test. The same test passed on isolated rerun, and the full suite passed on a clean rerun.

## Accepted Scope

Accepted implementation commits:

- `1353b21` — initial Wave 04 `/readings` overview migration.
- `84ebc85` — Rework 01 stable selectors, GRACE header, and visible presentation polish.

Accepted docs commits:

- `5963618` — Wave 04 TZ.
- `f37d010` — Wave 04 review/rework request.

## Notes For Next Wave

Wave 04 intentionally did not migrate `/readings/horary`, `/readings/horary/[id]`, `/readings/natal`, `/readings/natal/[id]`, or `/readings/natal/generating`.

Next frontend migration wave can proceed to a real-data detail flow, preferably `/readings/horary`, while preserving the existing backend horary contracts and polling behavior.
