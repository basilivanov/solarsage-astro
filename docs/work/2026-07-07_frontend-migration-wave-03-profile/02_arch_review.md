# Architect Review: Wave 03 `/profile` Real-Data Visual Migration

Date: 2026-07-07
Status: REWORK_REQUIRED
Reviewed branch: `wave-03-profile-visual-migration`
Reviewed commit: `76f36ab`
Base: `b3888ec`
Reviewer: architect
Independent reviewer: `Zeno` (`gpt-5.5`, xhigh)

## Summary

Wave 03 is close, but not accepted yet.

The implementation preserved the key runtime architecture:

- product data still comes from `/api/profile`, `/api/access`, `/api/horary/quota`, `/api/referral`, and `/api/checkin/metrics`;
- no MSW/runtime mock mode/mock-preview API was ported;
- no `DevModeSwitcher`, static `TransitTimeline`, static `LunarNodeWidget`, YooKassa, root layout, systemd, nginx, bot, or `3002` changes were included;
- mock visual e2e uses Playwright route interception only.

However, several explicit Wave 03 TZ requirements are incomplete.

## Fresh Verification Run By Architect

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
npx vitest run __tests__/components/ProfileScreen.test.tsx __tests__/hooks/useProfile.test.ts __tests__/api/profile-meta.test.ts __tests__/api/access.test.ts __tests__/contracts/profile.test.ts __tests__/contracts/access.test.ts __tests__/lib/profile.test.ts __tests__/lib/access.test.ts
```

Result: 8 files passed, 86 tests passed.

```bash
npx vitest run
```

Result: 84 files passed, 867 tests passed. Existing React `act(...)` warnings appeared in unrelated tests.

```bash
E2E_BASE_URL=http://localhost:3000 pnpm exec playwright test e2e/mock-visual --project=mobile
```

Result: 12 passed.

## Findings

### Important 1: Missing required loading/error ARIA semantics

Files:

- `components/profile/profile-screen.tsx:141`
- `components/profile/checkin-statistics.tsx:73`
- `components/profile/checkin-statistics.tsx:87`
- `components/profile/edit-sheet.tsx:463`

The TZ required:

- `role="status"` for loading hints;
- `role="alert"` for terminal profile load/save errors.

Current implementation leaves these states as plain `<p>` or unmarked skeleton sections. That weakens the UI Semantic/Test Contract and makes headless/a11y assertions less reliable.

Required fix:

- Add `role="status"` to profile loading hint.
- Add `role="alert"` to profile load error.
- Add `role="status"` or `aria-busy` to check-in statistics loading state.
- Add `role="alert"` to check-in statistics error state.
- Add `role="alert"` to edit sheet save error.
- Add or update component tests to assert the profile loading/error contract and edit sheet/save error contract where practical.

### Important 2: `profile-screen` `data-state` mixes hydration and save errors

File: `components/profile/profile-screen.tsx:83`

Current code:

```ts
const screenState = error ? "error" : loaded ? "ready" : "loading"
```

`useProfile.update()` stores save failures in the same `error` field after profile hydration. After a failed save, the root screen can become `data-state="error"` even though profile hydration already succeeded. The TZ defined root `data-state` as profile hydration state.

Required fix:

- Derive root screen state as hydration-first:

```ts
const screenState = loaded ? "ready" : error ? "error" : "loading"
```

- Add a component test proving loaded profile + error still renders root `data-state="ready"` while the edit sheet save error is surfaced through an alert.

### Important 3: Referral reward-day mapping is implemented but under-tested

Files:

- `__tests__/api/profile-meta.test.ts:88`
- `e2e/mock-visual/profile.spec.ts:51`

The implementation maps `daysPerInvite`, but tests do not prove the new behavior:

- API test does not include `daysPerInvite` in the successful referral payload and does not assert `rewardDays`.
- Mock visual e2e only checks the referral section is visible; it does not assert the required `14` reward-day text from fixture-backed data.

Required fix:

- Add an API unit test or strengthen the existing referral test with `daysPerInvite`.
- Assert both:
  - `rewardDays` equals backend `daysPerInvite`;
  - `bonusDays` equals `totalInvited * rewardDays`.
- Keep a fallback/default assertion for missing `daysPerInvite` returning `14`.
- In `e2e/mock-visual/profile.spec.ts`, assert the referral card contains `14 дней доступа` or the exact visible copy produced by the fixture.

### Minor 1: New e2e files lack full GRACE module blocks

Files:

- `e2e/mock-visual/profile.spec.ts:1`
- `e2e/mock-visual/fixtures/profile.ts:1`

Both files have `AI_HEADER`, but AGENTS.md asks new code files to preserve `START_MODULE_CONTRACT` and `START_MODULE_MAP`.

Required fix:

- Add concise module contract and module map blocks consistent with existing `e2e/mock-visual/day.spec.ts`, `calendar.spec.ts`, and `route-interception.ts`.

### Minor 2: Agent report is missing required handoff details

File: `docs/work/2026-07-07_frontend-migration-wave-03-profile/01_agent_report.md:5`

The report does not include the implementation head SHA in the header and does not include screenshot/path evidence or an explicit "no screenshots used" note.

Required fix:

- Update `01_agent_report.md` after rework with:
  - latest implementation commit SHA;
  - screenshot/path evidence if used, or explicit `Screenshots: not captured; visual comparison used source + mock-preview oracle only`;
  - rework summary and fresh gate results.

## Verdict

REWORK_REQUIRED.

Do not proceed to Wave 04 until Wave 03 rework passes architect review.
