# Rework 02 TZ: Wave 06 `/readings/natal`

Date: 2026-07-07
Status: ready for coder
Owner: architect
Branch: `wave-06-natal-visual-migration`
Base review: `docs/work/2026-07-07_frontend-migration-wave-06-natal/04_rework_01_review.md`
Reviewed commit: `e4101d8`

## Goal

Finish the remaining Wave 06 test-contract gaps without broadening the wave.

This rework should be tests/report only unless you discover a direct reason otherwise.

Do not change backend contracts, payment/YooKassa, runtime mocks, MSW, mock-preview API routes, `DEMO_NATAL_RESPONSE`, `lib/demo-data`, `lib/mocks/natal`, systemd, nginx, bot config, or canonical `3002`.

Keep `/readings/natal` on:

- `fetchNatalPreview()`;
- `/api/natal/preview`;
- `NatalPreviewRead`.

## Required Fixes

### 1. Strengthen the `fullReportAvailable=true` component test

Update:

```text
__tests__/natal/natal-component-states.test.tsx
```

In the existing test:

```text
ready state exposes data-full-report-available from real data
```

Keep the fixture with:

```ts
fullReportAvailable: true
```

Add assertions that the CTA button remains product-safe:

```tsx
const cta = screen.getByTestId("natal-full-report-cta")
const button = within(cta).getByRole("button", { name: "Полный отчёт скоро появится" })
expect(button).toBeDisabled()
expect(button).toHaveAttribute("aria-disabled", "true")
```

Import `within` from `@testing-library/react` if needed.

Do not enable payment/fulfillment.

### 2. Assert `natal-hero-badges`

The product selector exists after Rework 01. Now lock it in tests.

Required:

- Add a component assertion that `natal-hero-badges` is present in ready state when badge data exists.
- Add a mock-visual ready-state assertion:

```ts
await expect(page.getByTestId("natal-hero-badges")).toBeVisible()
```

This is a semantic/test contract assertion, not a Tailwind/style assertion.

### 3. Fix the agent report

Update:

```text
docs/work/2026-07-07_frontend-migration-wave-06-natal/01_agent_report.md
```

Required:

- Change Rework 01 commit from `a865cfc` to `e4101d8`.
- Add `natal-hero-badges` to the UI Semantic/Test Contract table.
- Add a `Rework 02` section with:
  - new commit SHA;
  - files changed;
  - exact commands run and results;
  - explicit statement that `fetchNatalPreview()` and `NatalPreviewRead` remain preserved;
  - explicit statement that CTA fulfillment/payment remains disabled;
  - explicit statement that runtime mocks/MSW/mock-preview API/static natal charts/reports/`DEMO_NATAL_RESPONSE`/demo data remain not ported;
  - explicit statement that `3002`, systemd, nginx, and bot config were not changed.

## Required Tests And Gates

Run and report exact results:

```bash
git diff --check main..HEAD
git diff --check
pnpm exec tsc --noEmit --pretty false
npx vitest run __tests__/natal/natal-component-states.test.tsx __tests__/api/natal-report.test.ts __tests__/contracts/natal.test.ts __tests__/guardrails/no-runtime-mocks.test.ts
npx vitest run
E2E_BASE_URL=http://localhost:3000 pnpm exec playwright test e2e/mock-visual --project=mobile
```

Use the local dev server on `3000` if needed.

Do not restart or replace canonical `3002`.

Backend tests are required only if backend code/contracts are changed. Backend changes are not expected for this rework.

## Commit Requirements

Create one new rework commit on `wave-06-natal-visual-migration`.

Expected files:

- `__tests__/natal/natal-component-states.test.tsx`
- `e2e/mock-visual/natal.spec.ts`
- `docs/work/2026-07-07_frontend-migration-wave-06-natal/01_agent_report.md`

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
  -d '{"prompt":"Wave 06 Rework 02 ready for architect review. Report: docs/work/2026-07-07_frontend-migration-wave-06-natal/01_agent_report.md. Review: docs/work/2026-07-07_frontend-migration-wave-06-natal/04_rework_01_review.md. Rework TZ: docs/work/2026-07-07_frontend-migration-wave-06-natal/05_rework_02_TZ.md. Branch: wave-06-natal-visual-migration. Commit: <commit_sha>"}'
```

Replace `<commit_sha>` with the actual Rework 02 commit SHA.
