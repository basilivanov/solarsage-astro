# Rework 01 TZ: Wave 06 `/readings/natal`

Date: 2026-07-07
Status: ready for coder
Owner: architect
Branch: `wave-06-natal-visual-migration`
Base review: `docs/work/2026-07-07_frontend-migration-wave-06-natal/02_arch_review.md`
Reviewed commit: `44dd537`

## Goal

Fix the Wave 06 review findings without broadening the wave.

Keep `/readings/natal` on the real preview flow:

- `fetchNatalPreview()`
- `/api/natal/preview`
- `NatalPreviewRead`

Do not add backend contracts, runtime mocks, MSW, mock-preview API routes, `DEMO_NATAL_RESPONSE`, `lib/demo-data`, `lib/mocks/natal`, payment/YooKassa, systemd/nginx/bot changes, or canonical `3002` changes.

## Required Fixes

### 1. Make `data-full-report-available` truthful

Current problem:

- Root `data-full-report-available` is hardcoded to `"false"` whenever the screen is ready.

Required:

- When `state.status === "ready"`, set:

```tsx
data-full-report-available={String(state.data.fullReportAvailable)}
```

- For non-ready states, omit the attribute or leave it `undefined`.
- Keep `CtaButton disabled` in this wave. Do not enable payment/fulfillment.

Required test:

- Add a component test where preview data has `fullReportAvailable: true`.
- Assert:
  - `natal-preview-screen` has `data-full-report-available="true"`;
  - `natal-full-report-cta` exists;
  - the CTA's button is still natively disabled and has `aria-disabled="true"`.

### 2. Add `natal-hero-badges`

Required:

- Add `data-testid="natal-hero-badges"` to the real badges container in `components/readings/natal-preview/hero-section.tsx`, or an equivalent stable wrapper that is present when badges are rendered.
- Keep badge values derived from real props only:
  - `ascSign`;
  - Sun/Moon highlights passed by the page;
  - `birthCity`.

Required test:

- Assert `natal-hero-badges` is present when the ready preview contains badge data.

### 3. Add missing component tests

Update:

```text
__tests__/natal/natal-component-states.test.tsx
```

Required tests:

- loading state:
  - mock `fetchNatalPreview()` as pending;
  - assert `natal-preview-screen data-state="loading"`;
  - assert `natal-preview-loading role="status"`.
- ready state:
  - assert `natal-preview-screen data-state="ready"`;
  - assert `natal-preview-content`;
  - assert `data-full-report-available` reflects the fixture.
- error + retry:
  - mock `fetchNatalPreview()` to reject/error through the existing API-client return shape;
  - assert `natal-preview-error role="alert"`;
  - use an explicit `allowSuccess` gate before clicking retry so the test cannot recover before the click;
  - assert retry reaches ready state.
- profile-incomplete:
  - mock `{ ok: false, error: { type: "profile_incomplete", message, missingFields } }`;
  - assert `natal-preview-screen data-state="profile_incomplete"`;
  - assert `natal-profile-incomplete` is visible and has the selected role.
- chart unavailable:
  - render ready preview with `chart: null`;
  - assert `natal-chart-unavailable`.

Do not rely on Tailwind class names.

### 4. Add profile-incomplete mock visual e2e

Update:

```text
e2e/mock-visual/natal.spec.ts
```

Required:

- Add a test for profile-incomplete state.
- Fixture route:

```ts
"/api/natal/preview": {
  status: 409,
  body: {
    detail: {
      message: "Profile incomplete",
      missingFields: ["birthDate", "birthCity"]
    }
  }
}
```

- Assert:
  - `natal-preview-screen` has `data-state="profile_incomplete"`;
  - `natal-profile-incomplete` is visible;
  - no missing API fixtures after quiet wait.

### 5. Update the agent report

Update:

```text
docs/work/2026-07-07_frontend-migration-wave-06-natal/01_agent_report.md
```

Add a `Rework 01` section with:

- rework commit SHA;
- files changed;
- exact commands run and results;
- explicit statement that `fetchNatalPreview()` and `NatalPreviewRead` real-data flow remain preserved;
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

Likely files:

- `app/(grace)/readings/natal/page.tsx`
- `components/readings/natal-preview/hero-section.tsx`
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
  -d '{"prompt":"Wave 06 Rework 01 ready for architect review. Report: docs/work/2026-07-07_frontend-migration-wave-06-natal/01_agent_report.md. Review: docs/work/2026-07-07_frontend-migration-wave-06-natal/02_arch_review.md. Rework TZ: docs/work/2026-07-07_frontend-migration-wave-06-natal/03_rework_01_TZ.md. Branch: wave-06-natal-visual-migration. Commit: <commit_sha>"}'
```

Replace `<commit_sha>` with the actual rework commit SHA.
