# Rework 01 TZ: Wave 04 `/readings` Overview

Date: 2026-07-07
Status: ready for coder
Owner: architect
Branch: `wave-04-readings-visual-migration`
Base review: `docs/work/2026-07-07_frontend-migration-wave-04-readings/02_arch_review.md`
Reviewed commit: `1353b21`

## Goal

Fix the Wave 04 review findings without broadening the wave.

Keep `/readings` as a real product catalog that navigates to real existing routes:

- horary -> `/readings/horary`
- natal -> `/readings/natal`

Do not add backend contracts, runtime mocks, MSW, `lib/demo-data.ts`, mock-preview API routes, systemd/nginx/bot changes, or `3002` changes.

## Required Fixes

### 1. Stable key-based coming-card selectors

Problem:

- `ComingCard` currently derives `data-testid` from Russian title text.
- Tests assert `readings-card-прогноз-на-месяц`.

Required:

- Add a stable prop to `ComingCard`, for example `readingKey: ComingReading["key"]` or `cardKey: ComingReading["key"]`.
- In `ReadingsScreen`, pass `r.key` into `ComingCard`.
- Render coming cards as:
  - `data-testid="readings-card-month"`
  - `data-testid="readings-card-year"`
  - `data-testid="readings-card-synastry"` or the actual catalog keys returned by `listReadings()`.
- Update unit tests and e2e tests to use key-based ids only.
- Do not derive public selectors from localized title/copy.

### 2. GRACE header for new unit test file

Add repository-standard GRACE blocks to:

```text
__tests__/components/ReadingsScreen.test.tsx
```

Required blocks:

- `AI_HEADER`
- `START_MODULE_CONTRACT`
- `START_MODULE_MAP`

Keep them concise and accurate. Do not rewrite unrelated old tests just for GRACE formatting.

### 3. Add narrow visible `/readings` presentation migration

Wave 04 must contain a real visible presentation delta, not only test ids.

Required:

- Add a narrow gradient heading treatment for the `/readings` hero title matching the mock-preview oracle's visual direction.
- Add available-card visual treatment matching the oracle direction: relative/overflow card surface, subtle hover/active polish, icon pill scale/soft glow if appropriate.
- Keep the changes product-safe and local to `/readings` presentation.
- If you add CSS helpers in `app/globals.css`, scope/comment them as `/readings` presentation helpers and add `prefers-reduced-motion` handling for animation.
- Do not copy broad mock-preview theme/root CSS.
- Do not port `SynastryDemo`, `CelebrityCompatibility`, `DEMO_NATAL_RESPONSE`, hardcoded celebrity astrology, or any demo score calculators.

Acceptable implementation shapes:

- Add narrowly named classes such as `readings-gradient-heading` and `readings-card-glow` in `app/globals.css`, then use them only in readings components.
- Or use Tailwind-only class changes if they reproduce the visible oracle direction without global CSS.

### 4. Update report

Update:

```text
docs/work/2026-07-07_frontend-migration-wave-04-readings/01_agent_report.md
```

Add a `Rework 01` section with:

- rework commit SHA;
- files changed;
- exact commands run and results;
- explicit statement that `3002`, systemd, nginx, and bot config were not changed;
- explicit statement that runtime mocks/MSW/mock-preview API/demo calculators remain not ported.

## Required Tests And Gates

Run and report exact results:

```bash
git diff --check main..HEAD
git diff --check
pnpm exec tsc --noEmit --pretty false
npx vitest run __tests__/components/ReadingsScreen.test.tsx __tests__/api/readings.test.ts __tests__/guardrails/no-runtime-mocks.test.ts
npx vitest run
E2E_BASE_URL=http://localhost:3000 pnpm exec playwright test e2e/mock-visual --project=mobile
```

Use the local dev server on `3000` if needed.

Do not restart or replace canonical `3002`.

Backend tests are required only if backend code/contracts are changed. Backend changes are not expected for this rework.

## Commit Requirements

Create one new rework commit on `wave-04-readings-visual-migration`.

Likely files:

- `components/readings/readings-screen.tsx`
- `components/readings/available-card.tsx`
- `components/readings/coming-card.tsx`
- `app/globals.css` only if narrow CSS helpers are used
- `__tests__/components/ReadingsScreen.test.tsx`
- `e2e/mock-visual/readings.spec.ts`
- `docs/work/2026-07-07_frontend-migration-wave-04-readings/01_agent_report.md`

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
  -d '{"prompt":"Wave 04 Rework 01 ready for architect review. Report: docs/work/2026-07-07_frontend-migration-wave-04-readings/01_agent_report.md. Review: docs/work/2026-07-07_frontend-migration-wave-04-readings/02_arch_review.md. Rework TZ: docs/work/2026-07-07_frontend-migration-wave-04-readings/03_rework_01_TZ.md. Branch: wave-04-readings-visual-migration. Commit: <commit_sha>"}'
```

Replace `<commit_sha>` with the actual rework commit SHA.
