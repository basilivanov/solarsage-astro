# Rework 01 TZ: Wave 03 `/profile`

Date: 2026-07-07
Status: ready for coder
Owner: architect
Branch: `wave-03-profile-visual-migration`
Base implementation commit: `76f36ab`
Review: `docs/work/2026-07-07_frontend-migration-wave-03-profile/02_arch_review.md`

## Goal

Resolve the Wave 03 architect review findings without broadening scope.

This is a focused rework. Do not migrate other screens and do not add new product features.

## Read First

Read:

- `docs/work/2026-07-07_frontend-migration-wave-03-profile/00_TZ.md`
- `docs/work/2026-07-07_frontend-migration-wave-03-profile/02_arch_review.md`
- `components/profile/profile-screen.tsx`
- `components/profile/checkin-statistics.tsx`
- `components/profile/edit-sheet.tsx`
- `__tests__/components/ProfileScreen.test.tsx`
- `__tests__/api/profile-meta.test.ts`
- `e2e/mock-visual/profile.spec.ts`
- `e2e/mock-visual/fixtures/profile.ts`

## Required Fixes

### 1. Fix profile root `data-state`

In `components/profile/profile-screen.tsx`, root `data-state` must represent profile hydration state, not save-error state.

Required behavior:

- `loaded === true` -> `data-state="ready"`, even when `error` contains a later save error.
- `loaded === false && error` -> `data-state="error"`.
- `loaded === false && !error` -> `data-state="loading"`.

Recommended implementation:

```ts
const screenState = loaded ? "ready" : error ? "error" : "loading"
```

Add/update tests in `__tests__/components/ProfileScreen.test.tsx` to prove this behavior.

### 2. Add required loading/error roles

Add DOM semantics required by the UI Semantic/Test Contract:

- Profile loading hint: `role="status"`.
- Profile load error: `role="alert"`.
- Check-in statistics loading state: `role="status"` and/or `aria-busy="true"`.
- Check-in statistics error state: `role="alert"`.
- Edit sheet save error: `role="alert"`.

Add or update tests where practical:

- component test should assert the profile loading hint is a status;
- component test should assert profile load error is an alert;
- edit sheet save error should be assertable through role alert, either in existing edit sheet tests or profile screen tests.

Do not add visible implementation/testing explanation text to the app UI.

### 3. Strengthen referral reward-day tests

`lib/api/profile-meta.ts` may keep its current implementation if it already maps `daysPerInvite` correctly, but tests must prove it.

Update `__tests__/api/profile-meta.test.ts`:

- Add a case where `/api/referral` returns `totalInvited: 3` and `daysPerInvite: 21`.
- Assert:
  - `result.referral.rewardDays === 21`;
  - `result.referral.bonusDays === 63`.
- Keep or add a fallback assertion where missing `daysPerInvite` defaults to `14`.

Update `e2e/mock-visual/profile.spec.ts`:

- In the ready-state test, assert `profile-referral-card` contains the fixture-backed visible copy with `14` reward days, for example `14 дней доступа`.

### 4. Add GRACE module blocks for new e2e files

Add concise `START_MODULE_CONTRACT` and `START_MODULE_MAP` blocks to:

- `e2e/mock-visual/profile.spec.ts`
- `e2e/mock-visual/fixtures/profile.ts`

Use the existing shape from:

- `e2e/mock-visual/day.spec.ts`
- `e2e/mock-visual/calendar.spec.ts`
- `e2e/mock-visual/route-interception.ts`

Do not over-expand comments. Keep them accurate and short.

### 5. Update the agent report

Update:

```text
docs/work/2026-07-07_frontend-migration-wave-03-profile/01_agent_report.md
```

Required additions:

- latest implementation commit SHA after this rework;
- short rework summary;
- fresh gate results;
- screenshot/path evidence if used, or explicit statement:

```text
Screenshots: not captured; visual comparison used source + mock-preview oracle only.
```

## Required Gates

Run and report exact results:

```bash
git diff --check main..HEAD
git diff --check
pnpm exec tsc --noEmit --pretty false
npx vitest run __tests__/components/ProfileScreen.test.tsx __tests__/api/profile-meta.test.ts
npx vitest run __tests__/components/ProfileScreen.test.tsx __tests__/hooks/useProfile.test.ts __tests__/api/profile-meta.test.ts __tests__/api/access.test.ts __tests__/contracts/profile.test.ts __tests__/contracts/access.test.ts __tests__/lib/profile.test.ts __tests__/lib/access.test.ts
npx vitest run
E2E_BASE_URL=http://localhost:3000 pnpm exec playwright test e2e/mock-visual --project=mobile
```

Use a local dev server on `3000` for Playwright.

Do not restart or replace canonical `3002`.

If `next dev` changes `next-env.d.ts`, revert only that generated edit before committing.

## Commit Requirements

Create one new rework commit on `wave-03-profile-visual-migration`.

Expected commit message:

```text
wave-03 rework-01: fix profile semantic contract and reward-day assertions
```

Do not commit:

- `.grace/`
- `grace.db`
- `skills/`
- `docs/superpowers/plans/2026-07-05-fix-day-route-auth-build.md`
- generated Playwright report artifacts
- unrelated files
- `next-env.d.ts` generated path churn

## Required Callback

At the very end, after writing the report and committing the rework, run:

```bash
curl --max-time 10 -X POST http://127.0.0.1:18765/trigger \
  -H "Authorization: Bearer 324b0306c32ffc5f6a64e16076c8c9ac0ee12fbba925cfd3" \
  -H "Content-Type: application/json" \
  -d '{"prompt":"Wave 03 Rework 01 ready for architect review. Report: docs/work/2026-07-07_frontend-migration-wave-03-profile/01_agent_report.md. Review: docs/work/2026-07-07_frontend-migration-wave-03-profile/02_arch_review.md. Rework TZ: docs/work/2026-07-07_frontend-migration-wave-03-profile/03_rework_01_TZ.md. Branch: wave-03-profile-visual-migration. Commit: <commit_sha>"}'
```

Replace `<commit_sha>` with the actual latest commit SHA.
