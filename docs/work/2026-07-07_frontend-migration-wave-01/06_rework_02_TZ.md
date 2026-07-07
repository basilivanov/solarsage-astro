# Rework 02 TZ: Frontend Migration Wave 01

Date: 2026-07-07
Status: ready for coder
Scope: fix only mock-visual e2e fixture coverage, assertion timing, and remaining raw sphere-key UI leakage

## Fix Only These Findings

### 1. Stop overwriting the main `/api/day/2026-07-05` fixture

Current `buildReadyFixtures()` overwrites:

```ts
"/api/day/2026-07-05": { body: dayPayload }
```

with a minimal week-strip payload because `WEEK_STRIP_DATES` also includes `2026-07-05`.

Fix this so the main day request receives a valid full `TodayPayload`.

The simplest acceptable fix:

```ts
for (const dateStr of WEEK_STRIP_DATES) {
  if (dateStr === "2026-07-05") continue;
  ...
}
```

If you choose another approach, keep it simpler than this and explain it in the report.

### 2. Fixture-cover late API calls in all mock visual tests

The route makes late calls after initial render. Mock visual tests must cover them or fail.

Add fixtures for:

- `/api/referral`;
- all actual week-strip dates requested by `/day/2026-07-05`.

In the reviewer run, actual missing week-strip dates were:

```text
2026-06-28
2026-06-29
2026-06-30
2026-07-01
2026-07-02
2026-07-03
2026-07-04
```

Do not rely on the old comment that says Monday-to-Sunday if the actual component uses a different week start.

Apply this to ready, locked, and no-overflow tests.

### 3. Move missing-fixture assertions to the end

Every mock visual test must assert missing fixture coverage after route effects had time to run.

Use a helper, for example:

```ts
async function expectNoMissingApiFixtures(tracker: MissingRequestsTracker): Promise<void> {
  await page.waitForTimeout(500);
  expect(tracker.all).toEqual([]);
}
```

Better: pass `page` into the helper and wait for a short quiet period before asserting.

The important rule:

- no `tracker.count === 0` immediately after `networkidle` if more React effects can still fire.

### 4. Prove the guard works

Add a test-only negative assertion or unit test for `installMockApiRoutes()` showing that an unmocked API call is recorded.

Acceptable options:

- a small Playwright test in `e2e/mock-visual/day.spec.ts` that makes an explicit `fetch("/api/__missing_fixture_probe")` and asserts the tracker records it; or
- a focused unit-style test if easier.

Keep it test-only. Do not add product runtime behavior.

### 5. Apply sphere label mapping to `DayEnergyMeter`

`DayEnergyMeter` is still rendered by `TodayScreen` and currently displays `sphereScores[].key` directly.

Fix:

- update `components/today/day-energy-meter.tsx` to display `getSphereLabel(item.key)`;
- keep raw key only as React key/internal id if needed;
- add/update a unit assertion proving `work_status_achievement` is not visible and the human label is visible.

Do not remove `DayEnergyMeter` just to avoid the issue.

### 6. Use current canon-shaped sphere keys in mock visual fixtures

Update `e2e/mock-visual/fixtures/day-2026-07-05.ts` to use current backend/canon-shaped keys, for example:

- `thinking_speech_learning`;
- `money_security_resources`;
- `home_family_roots`;
- `work_status_achievement`;
- `relationships_partnership`;
- `body_energy_health`.

Then update `lib/display/sphere-labels.ts` mappings and tests so these keys render as human Russian labels.

The point is not exact astrology truth in the fixture; the point is that fixture keys must look like live backend keys so raw-key leakage is caught.

## Do Not Change

- Do not change product UI unless needed for the e2e fix.
- Do not change backend contracts.
- Do not add MSW.
- Do not import `lib/mocks/*` or `lib/demo-data.ts` into product paths.
- Do not touch `.grace/`, `grace.db`, `skills/`, or the old plan file.
- Do not restart or replace canonical `3002`.

## Required Gates

Run and report in:

```text
docs/work/2026-07-07_frontend-migration-wave-01/07_rework_02_report.md
```

Commands:

```bash
git diff --check main..HEAD
pnpm exec tsc --noEmit --pretty false
npx vitest run
E2E_BASE_URL=http://localhost:3000 pnpm exec playwright test e2e/mock-visual --project=mobile
```

Use a local dev server on `3000` for branch verification.

## Commit Requirements

Add a new commit on `wave-01-day-visual-migration`.

The commit must include:

- e2e/spec/fixture fixes;
- remaining sphere-label display fixes;
- `07_rework_02_report.md`.

Do not rewrite or squash `6e1e719` unless the architect explicitly asks.

## Acceptance For Rework 02

Rework 02 is acceptable when:

- ready-state mock visual test receives full `TodayPayload`;
- locked-state and no-overflow tests also have complete fixture coverage;
- a deliberately missing API request is proven to be recorded;
- no rendered Wave 01 day UI shows raw sphere technical keys, including `DayEnergyMeter`;
- mock visual fixtures use current canon-shaped sphere keys;
- all required gates pass;
- no unrelated files are committed.
