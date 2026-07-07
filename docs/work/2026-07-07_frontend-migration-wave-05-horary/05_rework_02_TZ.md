# Rework 02 TZ: Wave 05 `/readings/horary`

Date: 2026-07-07
Status: ready for coder
Owner: architect
Branch: `wave-05-horary-visual-migration`
Base review: `docs/work/2026-07-07_frontend-migration-wave-05-horary/04_rework_01_review.md`
Reviewed commit: `c304a71`

## Goal

Fix the TypeScript gate failure from Rework 01 without broadening Wave 05.

Do not change backend, contracts, payment, runtime mocks/MSW, mock-preview API, systemd, nginx, bot config, or canonical `3002`.

## Required Fixes

### 1. Fix the TypeScript failure

Problem:

```text
__tests__/horary/horary-screen-flow.test.tsx(332,3): error TS2304: Cannot find name 'afterEach'.
```

Required:

- Either import `afterEach` from `vitest` in `__tests__/horary/horary-screen-flow.test.tsx`, or remove the `afterEach` block if it is unnecessary.
- Prefer the smallest change that keeps the new load-error/retry tests clear.

### 2. Update the agent report

Update:

```text
docs/work/2026-07-07_frontend-migration-wave-05-horary/01_agent_report.md
```

Required:

- Replace `Commit: [this commit]` in `Rework 01` with `Commit: c304a71`.
- Add a short `Rework 02` section with:
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
  -d '{"prompt":"Wave 05 Rework 02 ready for architect review. Report: docs/work/2026-07-07_frontend-migration-wave-05-horary/01_agent_report.md. Review: docs/work/2026-07-07_frontend-migration-wave-05-horary/04_rework_01_review.md. Rework TZ: docs/work/2026-07-07_frontend-migration-wave-05-horary/05_rework_02_TZ.md. Branch: wave-05-horary-visual-migration. Commit: <commit_sha>"}'
```

Replace `<commit_sha>` with the actual Rework 02 commit SHA.
