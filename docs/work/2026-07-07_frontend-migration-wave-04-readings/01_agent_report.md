# Agent Report: Wave 04 — `/readings` Overview Real-Data Visual Migration

Date: 2026-07-07
Agent: coding-executor (DeepSeek 4.2 Flash)
Branch: `wave-04-readings-visual-migration`
Base: `5963618`

## Summary

Wave 04 migrates the `/readings` overview screen presentation toward the mock-preview visual oracle while keeping the screen as a deterministic product catalog (`listReadings()`). Available cards navigate to real existing routes (`/readings/horary`, `/readings/natal`). Coming cards remain unavailable and open `InDevOverlay`.

No backend contracts were changed. No runtime mocks, MSW, or client-side astrology calculations were introduced.

## Changes Made

### Modified files

| File | Change |
|------|--------|
| `components/readings/readings-screen.tsx` | Added `data-testid="readings-screen"`, `data-state="ready"`, section testids (`readings-header`, `readings-info-banner`, `readings-available-section`, `readings-available-list`, `readings-coming-section`, `readings-coming-list`); passed `route` prop to `AvailableCard` |
| `components/readings/available-card.tsx` | Added `route` prop → `data-testid="readings-card-{key}"` + `data-href={route}` |
| `components/readings/coming-card.tsx` | Added `data-testid="readings-card-{key}"` + `data-state="disabled"` |
| `components/readings/in-dev-overlay.tsx` | Added `data-testid="readings-in-dev-overlay"` |

### New files

| File | Purpose |
|------|---------|
| `__tests__/components/ReadingsScreen.test.tsx` | 8 unit tests: root testid/state, sections, horary/natal route targets, navigation, coming overlay, dismiss |
| `e2e/mock-visual/readings.spec.ts` | 4 e2e tests: ready-state, coming overlay, overflow, negative-proof |
| `docs/work/2026-07-07_frontend-migration-wave-04-readings/01_agent_report.md` | This file |

## UI Semantic/Test Contract

| Attribute | Present | Location |
|-----------|---------|----------|
| `data-testid="readings-screen"` | ✅ | Root div |
| `data-state="ready"` | ✅ | Root div |
| `data-testid="readings-header"` | ✅ | Header |
| `data-testid="readings-info-banner"` | ✅ | Info banner |
| `data-testid="readings-available-section"` | ✅ | Available section |
| `data-testid="readings-available-list"` | ✅ | Available list |
| `data-testid="readings-card-horary"` + `data-href` | ✅ | Horary card |
| `data-testid="readings-card-natal"` + `data-href` | ✅ | Natal card |
| `data-testid="readings-coming-section"` | ✅ | Coming section |
| `data-testid="readings-coming-list"` | ✅ | Coming list |
| `data-testid="readings-card-{key}"` + `data-state="disabled"` | ✅ | Each coming card |
| `data-testid="readings-in-dev-overlay"` | ✅ | In-dev overlay |
| `role="dialog"` + `aria-modal="true"` | ✅ | Overlay |

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

### `npx vitest run __tests__/components/ReadingsScreen.test.tsx __tests__/api/readings.test.ts __tests__/guardrails/no-runtime-mocks.test.ts`
```
Test Files  3 passed (3)
     Tests  15 passed (15)
```

### `npx vitest run`
```
Test Files  85 passed (85)
     Tests  882 passed (882)
```

### `E2E_BASE_URL=http://localhost:3000 pnpm exec playwright test e2e/mock-visual --project=mobile`
```
16 passed (39.9s)
```

## Non-Ported Mock Preview Pieces

- `SynastryDemo` — not ported
- `CelebrityCompatibility` — not ported
- `DEMO_NATAL_RESPONSE` — not ported
- Hardcoded celebrity planet/sign database — not ported
- Mock-preview modal overlays that compute scores client-side — not ported
- Mock-preview API catch-all routes — not ported
- Root layout/theme-provider changes — not ported
- Broad global CSS from mock-preview — not ported
- Payment/YooKassa behavior — not ported

## Runtime Mock / MSW Statement

**No runtime mocks, MSW, mock-preview API routes, or demo data were ported to the product path.**
