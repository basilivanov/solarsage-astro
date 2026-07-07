# Rework 01 TZ: Frontend Migration Wave 02 Calendar

Date: 2026-07-07
Status: ready for coder
Scope: fix only the blockers from `02_arch_review.md`

## Fix Only These Findings

### 1. Make the calendar moon-mode e2e selector unambiguous

Current failing selector:

```ts
await page.getByRole("button", { name: "Луна" }).click();
```

It matches both the segmented control and a lunar-strip day button with accessible name containing `Убывающая Луна`.

Fix this by adding stable semantics, for example:

- `data-testid="calendar-view-day"` on the `Дни` segment;
- `data-testid="calendar-view-moon"` on the `Луна` segment.

Then update the e2e to click:

```ts
await page.getByTestId("calendar-view-moon").click();
```

Keep `aria-pressed` and accessible labels. Do not weaken lunar-strip accessibility.

### 2. Make moon-mode assertions deterministic

The test currently assumes the selected day is `2026-07-05`, but `CalendarScreen` initializes selection from `TODAY = new Date()`.

Fix the test so it deterministically selects the day it asserts:

```ts
await page.getByTestId("calendar-day-2026-07-05").click();
await page.getByTestId("calendar-view-moon").click();
await expect(page.getByTestId("calendar-selected-summary")).toContainText("Убывающая Луна");
await expect(page.getByTestId("calendar-selected-summary")).toContainText("63%");
```

If the order needs to be moon first then day, use the order that matches the component behavior. The key rule: the asserted date must be selected explicitly by the test.

### 3. Strengthen the ready-state mock-visual assertions

In `e2e/mock-visual/calendar.spec.ts`:

- assert the month header is visible, preferably through a stable test id such as `calendar-month-header`;
- assert `data-testid="lunar-calendar-strip"` is visible for the positive fixture;
- do not accept `lunar-calendar-unavailable` in the positive fixture test.

If you add `calendar-month-header`, put it on the actual month/title area, not on a decorative wrapper.

### 4. Make the branch handoff-safe

Resolve the uncommitted tracked change:

```text
M e2e/mock-visual/day.spec.ts
```

Either:

- include this shared-helper import cleanup in the rework commit; or
- revert it if you decide not to share `expectNoMissingApiFixtures()`.

Final handoff must have no uncommitted tracked files.

Do not commit unrelated:

- `.grace/`
- `grace.db`
- `skills/`
- `docs/superpowers/plans/2026-07-05-fix-day-route-auth-build.md`
- Playwright report/test-results artifacts

### 5. Update report with actual gate evidence

Update:

```text
docs/work/2026-07-07_frontend-migration-wave-02-calendar/01_agent_report.md
```

Required:

- include exact Playwright result for `E2E_BASE_URL=http://localhost:3000 pnpm exec playwright test e2e/mock-visual --project=mobile`;
- remove the "Ready to run" wording after actually running it;
- remove contradictory "passed but YooKassa fails" wording unless a command actually failed, in which case report the exact failure.

### 6. Update shared helper metadata

In `e2e/mock-visual/route-interception.ts`, update the module map/comment metadata to include:

```text
expectNoMissingApiFixtures
```

This is not a product behavior change.

## Required Gates

Run and report exact results in `01_agent_report.md`:

```bash
git diff --check main..HEAD
git diff --check
pnpm exec tsc --noEmit --pretty false
npx vitest run __tests__/components/CalendarScreen.test.tsx __tests__/api/calendar.test.ts __tests__/contracts/calendar.test.ts __tests__/lib/calendar.test.ts
npx vitest run
E2E_BASE_URL=http://localhost:3000 pnpm exec playwright test e2e/mock-visual --project=mobile
```

Use a local dev server on `3000` for Playwright verification.

Do not restart or replace canonical `3002`.

If `next dev` changes `next-env.d.ts`, revert only that generated edit before committing.

## Commit Requirements

Create one new commit on `wave-02-calendar-visual-migration`.

Commit must include:

- e2e selector/determinism fixes;
- stronger calendar ready-state assertions;
- any required semantic test ids;
- `e2e/mock-visual/day.spec.ts` only if keeping the shared-helper cleanup;
- updated `route-interception.ts` metadata;
- updated `01_agent_report.md`.

Do not rewrite or squash `35eb10d` unless the architect explicitly asks.

## Acceptance For Rework 01

Rework is acceptable when:

- full mock-visual Playwright gate passes;
- calendar e2e moon-mode test is deterministic;
- ready-state e2e cannot pass with missing lunar data in the positive fixture;
- branch has no uncommitted tracked files;
- report contains exact fresh gate evidence;
- no runtime mocks/demo data/client-side astrology calculations are introduced into product code.

## Callback Requirement

After committing and writing the updated report, run:

```bash
curl --max-time 10 -X POST http://127.0.0.1:18765/trigger \
  -H "Authorization: Bearer 324b0306c32ffc5f6a64e16076c8c9ac0ee12fbba925cfd3" \
  -H "Content-Type: application/json" \
  -d '{"prompt":"Wave 02 Rework 01 ready for architect review. Report: docs/work/2026-07-07_frontend-migration-wave-02-calendar/01_agent_report.md. Review: docs/work/2026-07-07_frontend-migration-wave-02-calendar/02_arch_review.md. Rework TZ: docs/work/2026-07-07_frontend-migration-wave-02-calendar/03_rework_01_TZ.md. Branch: wave-02-calendar-visual-migration. Commit: <PUT_COMMIT_SHA_HERE>"}'
```

Replace `<PUT_COMMIT_SHA_HERE>` with the actual new commit SHA.
