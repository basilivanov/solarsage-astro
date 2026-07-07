# Architecture Review: Frontend Migration Wave 02 Calendar

Date: 2026-07-07
Reviewer: architect
Branch reviewed: `wave-02-calendar-visual-migration`
Commit reviewed: `35eb10d`
Status: `REWORK_REQUIRED`

## Summary

Wave 02 preserves the real-data calendar architecture, but it is not acceptable yet.

The product path still uses `getMonthCalendar()` and `CalendarPayloadReadModel.days`; no runtime mock/demo imports or client-side astrology calculations were found in the calendar product path. However, the required mock-visual Playwright gate is red, the report omits that gate result, and the working tree contains an uncommitted tracked change.

## Findings

### 1. Blocking: required mock-visual e2e gate fails

Fresh command:

```bash
E2E_BASE_URL=http://localhost:3000 pnpm exec playwright test e2e/mock-visual --project=mobile
```

Result:

```text
1 failed, 7 passed
```

Failure:

```text
locator.click: strict mode violation:
getByRole('button', { name: 'Луна' }) resolved to 2 elements
```

Locations:

- `e2e/mock-visual/calendar.spec.ts:84`
- `components/calendar/calendar-screen.tsx:271-282`
- `components/calendar/lunar-calendar-strip.tsx:71-75`

Why this blocks acceptance:

The TZ requires the full mock-visual command to pass. The selector for the `Луна` segment is ambiguous because the lunar strip also contains a button whose accessible name includes `Убывающая Луна`.

Required fix:

Make the e2e selector unambiguous without depending on visual classes. Acceptable options:

- add stable semantic test ids to the segmented controls, for example `calendar-view-day` and `calendar-view-moon`, and use them in the spec; or
- scope the role query to the segmented control container if you add a stable container test id.

Do not make the lunar day buttons inaccessible just to satisfy the test.

### 2. Blocking: moon-mode e2e assertions are date-dependent

Evidence:

- `CalendarScreen` initializes `selected` from `TODAY`, which is `new Date()`.
- On this host the current date is `2026-07-07`.
- The test asserts selected summary values for `2026-07-05`: `Убывающая Луна` and `63%`.
- The fixture has `2026-07-07` with `37%`.

Locations:

- `lib/today.ts:49`
- `components/calendar/calendar-screen.tsx:114`
- `e2e/mock-visual/calendar.spec.ts:96-98`
- `e2e/mock-visual/fixtures/calendar-2026-07.ts:37-39`

Why this blocks acceptance:

The mock-visual test must be deterministic. It should not pass or fail based on the machine date.

Required fix:

Make the test deterministic. Acceptable options:

- freeze browser time to `2026-07-05T12:00:00` before the app initializes; or
- explicitly click/select `calendar-day-2026-07-05` before asserting the selected summary; or
- assert values for the actual selected fixture day after reading/selecting it deterministically.

Prefer an explicit date selection in the test because it also exercises the calendar interaction.

### 3. Blocking: required gate evidence in report is incomplete and contradictory

Evidence:

- `01_agent_report.md` says the e2e command is "Ready to run" instead of reporting its result.
- The same report says `npx vitest run` passed, then says a YooKassa guardrail fails in some environments.

Locations:

- `docs/work/2026-07-07_frontend-migration-wave-02-calendar/01_agent_report.md:88-94`
- `docs/work/2026-07-07_frontend-migration-wave-02-calendar/01_agent_report.md:117`

Why this blocks acceptance:

The protocol requires actual gate results in the handoff report. A missing Playwright result hides exactly the class of failure found in this review.

Required fix:

After rework, rerun all gates from `00_TZ.md` section 7 and update `01_agent_report.md` with exact fresh results, including the Playwright result.

### 4. Important: branch is not handoff-safe

Evidence:

`git status --short --branch` currently shows:

```text
## wave-02-calendar-visual-migration
 M e2e/mock-visual/day.spec.ts
?? .grace/
?? docs/superpowers/plans/2026-07-05-fix-day-route-auth-build.md
?? grace.db
?? skills/
```

The untracked `.grace/`, `grace.db`, `skills/`, and old plan file are pre-existing unrelated artifacts and must remain uncommitted. The tracked `e2e/mock-visual/day.spec.ts` change is part of Wave 02's shared helper refactor, but it was not committed in `35eb10d`.

Required fix:

Either include the `day.spec.ts` shared-helper import cleanup in the rework commit, or revert it if it is unnecessary. Final handoff must have no uncommitted tracked files.

### 5. Important: calendar mock-visual spec weakly asserts required sections

Evidence:

- The spec comment says "Header and grid", but only the grid is asserted.
- The positive fixture contains lunar data, but the spec accepts either `lunar-calendar-strip` or `lunar-calendar-unavailable`.

Locations:

- `e2e/mock-visual/calendar.spec.ts:59-67`

Required fix:

Strengthen the ready-state spec:

- assert the month header is visible by stable role/name or a stable test id;
- assert `lunar-calendar-strip` is visible for the positive fixture;
- keep a separate unavailable-state unit test or future e2e if needed, but do not let the positive mock-visual oracle pass with missing lunar data.

### 6. Minor: module contract metadata lags behind the shared helper export

Evidence:

- `route-interception.ts` exports `expectNoMissingApiFixtures()`.
- Its module map public entrypoints still list only `installMockApiRoutes` and `MissingRequestsTracker`.

Location:

- `e2e/mock-visual/route-interception.ts:24-34`

Required fix:

Update the module map/comment metadata while touching the file. This is minor, but it is cheap and keeps the internal standard consistent.

## Verification Run By Architect

Commands:

```bash
git diff --check main..HEAD
git diff --check
pnpm exec tsc --noEmit --pretty false
npx vitest run __tests__/components/CalendarScreen.test.tsx __tests__/api/calendar.test.ts __tests__/contracts/calendar.test.ts __tests__/lib/calendar.test.ts
npx vitest run
E2E_BASE_URL=http://localhost:3000 pnpm exec playwright test e2e/mock-visual --project=mobile
```

Results:

- `git diff --check main..HEAD`: passed.
- `git diff --check`: passed.
- TypeScript: passed.
- Targeted Vitest: passed, `4` files / `53` tests.
- Full Vitest: passed, `84` files / `867` tests.
- Mock visual e2e: failed, `1` failed / `7` passed.

## Decision

`REWORK_REQUIRED`

Apply `03_rework_01_TZ.md`.
