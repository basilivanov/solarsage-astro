# Architect Review: Wave 10 Rework 02

Date: 2026-07-07
Branch: `main`
Reviewed commit: `8ada887`
Status: ACCEPTED

## Decision

Accepted.

Rework 02 fixes the remaining visible composition mismatches on `/day/2026-07-05`:

- the non-today check-in placeholder is gone;
- the bottom history widget is present before the disclaimer;
- the screen now has top/middle/bottom evidence for the internal scroll container;
- production/runtime code does not import mock APIs or mock astrology helpers.

## Visual Review

Reviewed artifacts:

- `docs/work/2026-07-07_frontend-corrective-day-migration-wave-10/artifacts/rework-02/3001-day-2026-07-05-top.png`
- `docs/work/2026-07-07_frontend-corrective-day-migration-wave-10/artifacts/rework-02/3001-day-2026-07-05-middle.png`
- `docs/work/2026-07-07_frontend-corrective-day-migration-wave-10/artifacts/rework-02/3001-day-2026-07-05-bottom.png`
- `docs/work/2026-07-07_frontend-corrective-day-migration-wave-10/artifacts/rework-02/main-day-2026-07-05-top.png`
- `docs/work/2026-07-07_frontend-corrective-day-migration-wave-10/artifacts/rework-02/main-day-2026-07-05-middle.png`
- `docs/work/2026-07-07_frontend-corrective-day-migration-wave-10/artifacts/rework-02/main-day-2026-07-05-bottom.png`

Notes:

- 3001 lacks equivalent `data-testid` markers for some sections, so PNG review is the authoritative oracle comparison there.
- Main `summary.json` correctly records `visibleChecks.main.hasCheckin=false`, `visibleChecks.main.hasHistory=true`, and `astro-history-widget` in section order.

## Independent Verification

Commands run by architect:

```bash
npx vitest run __tests__/lib/adapt-payload.test.ts __tests__/components/TodayScreen.test.tsx __tests__/guardrails/no-runtime-mocks.test.ts
```

Result: PASS, 3 files, 37 tests.

```bash
npx tsc --noEmit --pretty false
```

Result: PASS.

```bash
pnpm build
```

Result: PASS. Build changed `next-env.d.ts` to a generated `.next-prod` path; the file was restored to the tracked canonical import before review completion.

```bash
E2E_BASE_URL=http://localhost:4444 npx playwright test e2e/mock-visual/day.spec.ts --project=mobile
```

Result after fresh build: PASS, 4 tests.

The first e2e attempt was rejected as invalid because `localhost:4444` served a stale production build. After running `pnpm build` and restarting the preview server, the same e2e suite passed.

## Residual Notes

- `3002` was not restarted by the worker. Production restart remains a separate deploy step after this accept.
- Unrelated untracked files remain ignored: `.grace/`, `grace.db`, `skills/`, `docs/superpowers/plans/2026-07-05-fix-day-route-auth-build.md`.
