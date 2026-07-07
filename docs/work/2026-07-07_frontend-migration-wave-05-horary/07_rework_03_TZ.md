# Rework 03 TZ: Wave 05 `/readings/horary`

Date: 2026-07-07
Status: ready for coder
Owner: architect
Branch: `wave-05-horary-visual-migration`
Base review: `docs/work/2026-07-07_frontend-migration-wave-05-horary/06_rework_02_review.md`
Reviewed commit: `fa8215c`

## Goal

Fix the full Vitest failure from Rework 02 without broadening Wave 05.

Do not change backend, contracts, payment, runtime mocks/MSW, mock-preview API, systemd, nginx, bot config, or canonical `3002`.

## Required Fixes

### 1. Stabilize the load-error retry test

Current failing test:

```text
__tests__/horary/horary-screen-flow.test.tsx
HoraryScreen — load error and retry > retry button re-calls loadData and recovers to ready state
```

Problem:

- The test uses first-call reject / subsequent-call resolve mocks.
- In the full suite, the screen can reach `ready` before the test clicks the retry button.
- The test then fails because the retry button is no longer rendered.

Required:

- Keep mocks rejecting until the test explicitly decides retry may succeed.
- Recommended shape:

```ts
let allowSuccess = false

mockQuota.mockImplementation(() => {
  if (!allowSuccess) return Promise.reject(new Error("API error"))
  return Promise.resolve(successPayload)
})

// same for list/profile

await waitFor(() => {
  expect(screen.getByTestId("horary-screen").getAttribute("data-state")).toBe("error")
})

const retryBtn = screen.getByRole("button", { name: /Попробовать снова/ })
allowSuccess = true
fireEvent.click(retryBtn)

await waitFor(() => {
  expect(screen.getByTestId("horary-screen").getAttribute("data-state")).toBe("ready")
})
```

Do not weaken the test to pass if the screen skips the visible error state. The test must prove:

- visible `error` state exists;
- retry button is visible in that state;
- clicking retry can recover to `ready`.

### 2. Update the agent report

Update:

```text
docs/work/2026-07-07_frontend-migration-wave-05-horary/01_agent_report.md
```

Required:

- Replace Rework 02 commit `d267373` with the reviewed commit `fa8215c`.
- Add a `Rework 03` section with:
  - new commit SHA;
  - files changed;
  - exact gate results.

## Required Tests And Gates

Run and report exact results:

```bash
git diff --check main..HEAD
git diff --check
pnpm exec tsc --noEmit --pretty false
npx vitest run __tests__/horary/horary-screen-flow.test.tsx __tests__/horary/horary-form-submit.test.tsx __tests__/horary/horary-time-confirm.test.tsx __tests__/horary/horary-quota-bar.test.tsx __tests__/horary/horary-question-card.test.tsx __tests__/horary/horary-processing-card.test.tsx __tests__/horary/horary-purchase-sheet.test.tsx __tests__/contracts/horary.test.ts
npx vitest run
E2E_BASE_URL=http://localhost:3000 pnpm exec playwright test e2e/mock-visual --project=mobile
```

Use the local dev server on `3000` if needed.

Do not restart or replace canonical `3002`.

## Commit Requirements

Create one new rework commit on `wave-05-horary-visual-migration`.

Likely files:

- `__tests__/horary/horary-screen-flow.test.tsx`
- `docs/work/2026-07-07_frontend-migration-wave-05-horary/01_agent_report.md`

Do not commit:

- `.grace/`
- `grace.db`
- `skills/`
- `docs/superpowers/plans/2026-07-05-fix-day-route-auth-build.md`
- generated screenshots/reports
- unrelated files
- `next-env.d.ts` generated churn

## Required Callback

At the very end, after writing the report and committing the rework, run this callback from the repo root:

```bash
curl --max-time 10 -X POST http://127.0.0.1:18765/trigger \
  -H "Authorization: Bearer 324b0306c32ffc5f6a64e16076c8c9ac0ee12fbba925cfd3" \
  -H "Content-Type: application/json" \
  -d '{"prompt":"Wave 05 Rework 03 ready for architect review. Report: docs/work/2026-07-07_frontend-migration-wave-05-horary/01_agent_report.md. Review: docs/work/2026-07-07_frontend-migration-wave-05-horary/06_rework_02_review.md. Rework TZ: docs/work/2026-07-07_frontend-migration-wave-05-horary/07_rework_03_TZ.md. Branch: wave-05-horary-visual-migration. Commit: <commit_sha>"}'
```

Replace `<commit_sha>` with the actual Rework 03 commit SHA.
