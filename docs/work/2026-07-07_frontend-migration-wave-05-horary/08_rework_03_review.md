# Architect Review: Wave 05 Rework 03 `/readings/horary`

Date: 2026-07-07
Status: ACCEPTED
Reviewed branch: `wave-05-horary-visual-migration`
Reviewed commit: `474677f`
Base review: `docs/work/2026-07-07_frontend-migration-wave-05-horary/06_rework_02_review.md`
Rework TZ: `docs/work/2026-07-07_frontend-migration-wave-05-horary/07_rework_03_TZ.md`

## Verdict

Wave 05 is accepted.

The rework resolves the blocking issues from previous reviews:

- `horary-screen` is now present across `loading`, `error`, and `ready` states with the required `data-state` contract.
- `horary-load-error` is rendered as an alert with a retry path.
- The retry unit test now keeps API mocks in error until the test explicitly clicks retry, then verifies recovery to `ready`.
- Submit accessibility follows the accepted contract: invalid submit remains clickable with `aria-disabled` and blocked-reason feedback; submitting uses native `disabled`.
- `horary-blocked-reason` and submit API errors expose `role="alert"`.
- Mock visual e2e coverage for `/readings/horary` exists and passes.
- Real horary API flow is preserved: quota/profile/history load, create with idempotency/location/client time fields, polling, and auto-navigation.
- No runtime mocks, MSW, mock-preview API routes, demo horary data, static charts/answers, backend contracts, payment, systemd, nginx, bot, or `3002` changes were introduced.

## Accepted Scope

Accepted implementation commits:

- `9d043c5` — initial Wave 05 `/readings/horary` visual/semantic migration.
- `c304a71` — Rework 01 root state contract, load-error retry tests, submit accessibility.
- `fa8215c` — Rework 02 TypeScript `afterEach` import and report update.
- `474677f` — Rework 03 stable retry test using explicit `allowSuccess` gate.

Accepted docs commits:

- `df22ab7` — Wave 05 TZ.
- `3330305` — Wave 05 initial rework request.
- `8450ef2` — Wave 05 Rework 02 request.
- `e395269` — Wave 05 Rework 03 request.

Note: the agent report's Rework 03 section still names an intermediate local commit SHA and contains a stale parenthetical about YooKassa. Architect verification below supersedes that report detail; the accepted reviewed commit is `474677f`.

## Fresh Verification

Architect ran these checks on `474677f`:

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
npx vitest run __tests__/horary/horary-screen-flow.test.tsx __tests__/horary/horary-form-submit.test.tsx __tests__/horary/horary-time-confirm.test.tsx __tests__/horary/horary-quota-bar.test.tsx __tests__/horary/horary-question-card.test.tsx __tests__/horary/horary-processing-card.test.tsx __tests__/horary/horary-purchase-sheet.test.tsx __tests__/contracts/horary.test.ts
```

Result: 8 files passed, 130 tests passed.

```bash
npx vitest run
```

Result: 85 files passed, 891 tests passed. Existing unrelated React `act(...)` warnings appeared in older tests.

```bash
E2E_BASE_URL=http://localhost:3000 pnpm exec playwright test e2e/mock-visual/calendar.spec.ts:82 --project=mobile
```

Result: 1 passed.

```bash
E2E_BASE_URL=http://localhost:3000 pnpm exec playwright test e2e/mock-visual --project=mobile
```

Result: 20 passed.

Note: the first full `e2e/mock-visual` run during review had one transient failure in the pre-existing `/calendar` moon-mode test because `/api/_log` was recorded as a missing mock fixture. The same test passed on isolated rerun, and the full mock-visual suite passed on a clean rerun.

## Notes For Next Wave

Wave 05 intentionally did not migrate:

- `/readings/horary/[id]` answer detail page;
- horary chart/answer renderer;
- `/readings/natal`;
- `/readings/natal/[id]`;
- `/readings/natal/generating`.

Next frontend migration wave can proceed to `/readings/natal` overview/create/generating surface while preserving existing real natal report contracts and avoiding mock-preview static astrology.
