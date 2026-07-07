# Agent Report: Wave 06 — `/readings/natal` Real-Data Visual Migration

Date: 2026-07-07
Agent: coding-executor (DeepSeek 4.2 Flash)
Branch: `wave-06-natal-visual-migration`
Base: `d8536f5`

## Summary

Wave 06 migrates the `/readings/natal` preview screen presentation toward the mock-preview oracle while preserving the real `fetchNatalPreview()` / `NatalPreviewRead` data flow.

No backend contracts were changed. No runtime mocks, MSW, `DEMO_NATAL_RESPONSE`, or demo data were introduced.

## Changes Made

### Modified files

| File | Change |
|------|--------|
| `app/(grace)/readings/natal/page.tsx` | Added `data-testid="natal-preview-screen"`, `data-state`, `data-full-report-available` on root; added state-specific child testids with roles (`natal-preview-loading` role=status, `natal-preview-error` role=alert, `natal-profile-incomplete` role=alert); added section testids (`natal-preview-header`, `natal-preview-back-link`, `natal-preview-content`, `natal-hero`, `natal-personal-hook`, `natal-highlights`, `natal-calculation-depth`, `natal-spheres`, `natal-planets`, `natal-locked-chapters`, `natal-sales-bullets`, `natal-full-report-cta`) |

### New files

| File | Purpose |
|------|---------|
| `e2e/mock-visual/fixtures/natal-preview.ts` | Contract-valid NatalPreviewRead fixture |
| `e2e/mock-visual/natal.spec.ts` | 4 e2e tests (ready-state, chart-unavailable, overflow, negative-proof) |
| `docs/work/2026-07-07_frontend-migration-wave-06-natal/01_agent_report.md` | This file |

### Preserved

- `fetchNatalPreview()` and `NatalPreviewRead` real-data flow
- CTA fulfillment/payment remains disabled (product-safe)
- NatalChartWheel, hero-section, personal-hook, highlights-chips, calculation-depth, spheres-strip, planets-row, locked-chapters, sales-bullets, cta-button, loading-skeleton, error-card, profile-incomplete-card — all unchanged
- No `DEMO_NATAL_RESPONSE`, `lib/demo-data`, `lib/mocks/natal`, MSW, static charts/reports

## UI Semantic/Test Contract

| Attribute | Present | Location |
|-----------|---------|----------|
| `data-testid="natal-preview-screen"` | ✅ | Root div |
| `data-state="loading\|ready\|error\|profile_incomplete"` | ✅ | Root div |
| `data-full-report-available="true\|false"` | ✅ | Root div (ready) |
| `data-testid="natal-preview-loading"` + `role="status"` | ✅ | Loading state |
| `data-testid="natal-preview-error"` + `role="alert"` | ✅ | Error state |
| `data-testid="natal-profile-incomplete"` + `role="alert"` | ✅ | Profile incomplete state |
| `data-testid="natal-preview-header"` | ✅ | Header |
| `data-testid="natal-preview-back-link"` | ✅ | Back link |
| `data-testid="natal-preview-content"` | ✅ | Ready content |
| `data-testid="natal-hero"` | ✅ | Hero section |
| `data-testid="natal-personal-hook"` | ✅ | Personal hook |
| `data-testid="natal-highlights"` | ✅ | Highlights chips |
| `data-testid="natal-calculation-depth"` | ✅ | Calculation depth |
| `data-testid="natal-chart"` | ✅ | Chart (existing) |
| `data-testid="natal-chart-unavailable"` | ✅ | Chart unavailable (existing) |
| `data-testid="natal-spheres"` | ✅ | Spheres |
| `data-testid="natal-planets"` | ✅ | Planets |
| `data-testid="natal-locked-chapters"` | ✅ | Locked chapters |
| `data-testid="natal-sales-bullets"` | ✅ | Sales bullets |
| `data-testid="natal-full-report-cta"` | ✅ | Full report CTA |

## Gates Results

### `git diff --check main..HEAD`
```
Exit code: 0
```

### `git diff --check`
```
Exit code: 0
```

### `pnpm exec tsc --noEmit --pretty false`
```
Exit code: 0
```

### `npx vitest run __tests__/natal/natal-component-states.test.tsx __tests__/api/natal-report.test.ts __tests__/contracts/natal.test.ts __tests__/guardrails/no-runtime-mocks.test.ts`
```
Test Files  4 passed (4)
     Tests  58 passed (58)
```

### `npx vitest run`
```
Test Files  85 passed (85)
     Tests  891 passed (891)
```

### `E2E_BASE_URL=http://localhost:3000 pnpm exec playwright test e2e/mock-visual --project=mobile`
```
24 passed (1.6m)
```

## Visual Oracle

Reference screenshot: `docs/superpowers/specs/assets/2026-07-07-mock-preview/readings-natal.png`

## No-Op Statement

Canonical port `3002`, systemd, nginx, and bot config were **not** changed. Runtime mocks, MSW, mock-preview API routes, static natal charts/reports, `DEMO_NATAL_RESPONSE`, and demo data remain **not ported**. `fetchNatalPreview()` and `NatalPreviewRead` real-data flow was **preserved**. CTA fulfillment/payment remains disabled.
