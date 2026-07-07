# Architect Review: Wave 05 Rework 02 `/readings/horary`

Date: 2026-07-07
Status: REWORK_REQUIRED
Reviewed branch: `wave-05-horary-visual-migration`
Reviewed commit: `fa8215c`
Base review: `docs/work/2026-07-07_frontend-migration-wave-05-horary/04_rework_01_review.md`
Rework TZ: `docs/work/2026-07-07_frontend-migration-wave-05-horary/05_rework_02_TZ.md`

## Verdict

Rework 02 is not accepted because the full Vitest gate fails.

The TypeScript issue from Rework 01 is fixed, targeted horary tests pass, and mock-visual Playwright passes. The remaining blocker is a flaky/incorrect retry unit test that passes in isolation but fails in the full test run.

## Findings

### 1. Blocking: full Vitest fails in the new load-error retry test

Fresh command:

```bash
npx vitest run
```

Result:

```text
Test Files  1 failed | 84 passed (85)
Tests       1 failed | 890 passed (891)

FAIL __tests__/horary/horary-screen-flow.test.tsx > HoraryScreen — load error and retry > retry button re-calls loadData and recovers to ready state
TestingLibraryElementError: Unable to find an accessible element with the role "button" and name `/Попробовать снова/`
```

Evidence:

- `__tests__/horary/horary-screen-flow.test.tsx:376-382`
- `__tests__/horary/horary-screen-flow.test.tsx:390-397`

Why this is happening:

- The retry test currently uses `mockImplementationOnce(...reject...).mockImplementation(...resolve...)`.
- After the first error render, `HoraryScreen` can re-run `loadData()` before the test clicks retry because the mocked `useToast()` returns a fresh `toast` function each render, changing the `loadData` callback dependency.
- That consumes the resolving mock implementation and moves the screen to `ready`, so the retry button is gone by the time the test looks for it.

Required fix:

- Make the retry test deterministic.
- Keep the API mocks rejecting until the test explicitly clicks retry. For example:
  - `let allowSuccess = false`;
  - mocks reject while `allowSuccess === false`;
  - after asserting `data-state="error"` and locating the retry button, set `allowSuccess = true`;
  - click retry;
  - assert `data-state="ready"`.
- Do not hide this by weakening the assertion to accept both error and ready. The test must prove retry recovers from an actual visible error state.

### 2. Minor: Rework 02 report still names the wrong commit

The current report says:

```text
Commit: `d267373`
```

The reviewed branch HEAD and callback commit are:

```text
fa8215c
```

Required fix:

- Update `docs/work/2026-07-07_frontend-migration-wave-05-horary/01_agent_report.md` so Rework 02 names `fa8215c`.
- Add a `Rework 03` section with the new commit SHA, files changed, and fresh gate results.

## Fresh Verification

Architect ran these checks on `fa8215c`:

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

Result: failed, 1 failed test out of 891.

```bash
E2E_BASE_URL=http://localhost:3000 pnpm exec playwright test e2e/mock-visual --project=mobile
```

Result: 20 passed.

## Rework

Rework instructions are in:

```text
docs/work/2026-07-07_frontend-migration-wave-05-horary/07_rework_03_TZ.md
```
