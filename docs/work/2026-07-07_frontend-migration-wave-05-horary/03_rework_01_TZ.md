# Rework 01 TZ: Wave 05 `/readings/horary`

Date: 2026-07-07
Status: ready for coder
Owner: architect
Branch: `wave-05-horary-visual-migration`
Base review: `docs/work/2026-07-07_frontend-migration-wave-05-horary/02_arch_review.md`
Reviewed commit: `9d043c5`

## Goal

Fix the Wave 05 review findings without broadening the wave.

Keep the real `/readings/horary` flow intact:

- `getHoraryQuota()`
- `listHoraryQuestions(20, 0)`
- `getProfile()`
- `createHoraryQuestion()` with idempotency/location/client time fields
- polling via `getHoraryQuestion(id)`
- auto-navigation to `/readings/horary/{id}` after the just-submitted question is answered

Do not add backend contracts, runtime mocks, MSW, mock-preview API routes, payment/YooKassa changes, systemd/nginx/bot changes, or `3002` changes.

## Required Fixes

### 1. Stable root contract for loading, ready, and error

Current problem:

- `horary-screen` exists only in the ready branch.
- Loading returns `horary-loading` without the screen root.
- Error returns `horary-load-error` without the screen root.
- `data-state="error"` is effectively unreachable on `horary-screen`.

Required:

- Loading branch:
  - root `data-testid="horary-screen"`
  - root `data-state="loading"`
  - child `data-testid="horary-loading"`
  - child `role="status"`
- Error branch:
  - root `data-testid="horary-screen"`
  - root `data-state="error"`
  - child `data-testid="horary-load-error"`
  - child `role="alert"`
  - retry button reruns the real `loadData()` path
- Ready branch:
  - keep root `data-testid="horary-screen"`
  - keep root `data-state="ready"`
  - keep root `data-has-credit="true|false"`

Implementation constraints:

- Do not move hooks below conditional returns.
- Prefer setting `setLoading(true)` at the start of `loadData()` so retry visibly re-enters loading before ready/error.
- Do not silently turn initial load failure into no-credit state.

### 2. Add load-error and retry unit coverage

Update existing horary tests, preferably `__tests__/horary/horary-screen-flow.test.tsx`.

Required assertions:

- When one initial API call rejects, `horary-screen` reaches `data-state="error"`.
- `horary-load-error` is present and has `role="alert"`.
- The retry button is visible and calls the same load path.
- If retry mocks resolve, the screen reaches `data-state="ready"`.

Keep tests independent from Tailwind class names.

### 3. Resolve submit accessibility state

Architecture decision:

- Invalid submit remains interactive to preserve the current click-to-explain UX.
- Invalid state uses `aria-disabled="true"` but not native `disabled`.
- Submitting state uses native `disabled` to prevent duplicate create requests.
- `horary-blocked-reason` must expose `role="alert"` or `role="status"`.

Required code/test changes:

- In `HoraryForm`, keep `aria-disabled={!isValid || submitting}`.
- Add `disabled={submitting}` to `horary-submit-btn`.
- Add a role to `horary-blocked-reason`.
- Update `__tests__/horary/horary-form-submit.test.tsx`:
  - invalid button has `aria-disabled="true"`;
  - invalid button is not natively disabled;
  - clicking invalid button still renders `horary-blocked-reason`;
  - blocked reason has the chosen role;
  - submitting button is natively disabled.
- Keep existing real submit behavior green.

### 4. Update the agent report

Update:

```text
docs/work/2026-07-07_frontend-migration-wave-05-horary/01_agent_report.md
```

Add a `Rework 01` section with:

- rework commit SHA;
- files changed;
- exact commands run and results;
- note that the invalid-submit native-disabled clause was intentionally resolved as:
  - native `disabled` for `submitting`;
  - `aria-disabled` plus click-to-explain for invalid;
- visual oracle used: `docs/superpowers/specs/assets/2026-07-07-mock-preview/readings-horary.png`;
- explicit statement that `3002`, systemd, nginx, and bot config were not changed;
- explicit statement that runtime mocks/MSW/mock-preview API/static horary charts/answers/demo data remain not ported.

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

Backend tests are required only if backend code/contracts are changed. Backend changes are not expected for this rework.

## Commit Requirements

Create one new rework commit on `wave-05-horary-visual-migration`.

Likely files:

- `components/readings/horary/horary-screen.tsx`
- `components/readings/horary/horary-form.tsx`
- `__tests__/horary/horary-screen-flow.test.tsx`
- `__tests__/horary/horary-form-submit.test.tsx`
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
  -d '{"prompt":"Wave 05 Rework 01 ready for architect review. Report: docs/work/2026-07-07_frontend-migration-wave-05-horary/01_agent_report.md. Review: docs/work/2026-07-07_frontend-migration-wave-05-horary/02_arch_review.md. Rework TZ: docs/work/2026-07-07_frontend-migration-wave-05-horary/03_rework_01_TZ.md. Branch: wave-05-horary-visual-migration. Commit: <commit_sha>"}'
```

Replace `<commit_sha>` with the actual rework commit SHA.
