# Agent Report: Wave 05 — `/readings/horary` Real-Data Visual Migration

Date: 2026-07-07
Agent: coding-executor (DeepSeek 4.2 Flash)
Branch: `wave-05-horary-visual-migration`
Base: `df22ab7`

## Summary

Wave 05 migrates the `/readings/horary` ask/create/history screen presentation closer to the mock-preview oracle while preserving the real horary API flow: quota, questions, profile, create, polling, auto-navigation.

No backend contracts were changed. No runtime mocks, MSW, static charts, or demo data were introduced.

## Changes Made

### Modified files

| File | Change |
|------|--------|
| `components/readings/horary/horary-screen.tsx` | Added `data-testid="horary-screen"`, `data-state`, `data-has-credit` on root; added `data-testid="horary-loading"` + `role="status"` on loading state; added load-error block with `data-testid="horary-load-error"` + `role="alert"` + retry button; added section testids (`horary-header`, `horary-back-link`, `horary-quota-section`, `horary-form-section`, `horary-no-credit-card`, `horary-history-section`, `horary-empty-history`) |
| `components/readings/horary/horary-form.tsx` | Added `data-testid="horary-form"` on form element; added `aria-pressed` on category buttons; added `role="alert"` on submit error; added `aria-disabled` on submit button |
| `e2e/mock-visual/horary.spec.ts` | New: 4 e2e tests (ready-state, no-credit, overflow, negative-proof) |
| `e2e/mock-visual/fixtures/horary.ts` | New: contract-valid fixtures for horary quota, questions, profile |
| `__tests__/horary/horary-screen-flow.test.tsx` | Added 4 new DOM contract tests (loading state, ready state, empty history, no-credit) |

### Preserved

- Real API flow: `getHoraryQuota()`, `listHoraryQuestions()`, `getProfile()`, `createHoraryQuestion()` with idempotency, polling, auto-navigation
- Existing error handling from `HoraryApiError`
- Existing `HoraryForm`, `HoraryTimeConfirm`, `HoraryQuotaBar`, `HoraryQuestionCard`, `HoraryProcessingCard`, `HoraryPurchaseSheet` behavior
- No `SynastryDemo`, `CelebrityCompatibility`, static charts, or mock-preview API routes

## UI Semantic/Test Contract

| Attribute | Present | Location |
|-----------|---------|----------|
| `data-testid="horary-screen"` | ✅ | Root div |
| `data-state="loading\|ready\|error"` | ✅ | Root div |
| `data-has-credit="true\|false"` | ✅ | Root div (ready state) |
| `data-testid="horary-loading"` + `role="status"` | ✅ | Loading state |
| `data-testid="horary-load-error"` + `role="alert"` | ✅ | Load error state with retry |
| `data-testid="horary-back-link"` | ✅ | Back link |
| `data-testid="horary-header"` | ✅ | Header |
| `data-testid="horary-quota-section"` | ✅ | Quota section |
| `data-testid="horary-quota-bar"` | ✅ | Quota bar (existing) |
| `data-testid="horary-form-section"` | ✅ | Form section |
| `data-testid="horary-form"` | ✅ | Form element |
| `data-testid="horary-question-input"` | ✅ | Textarea (existing) |
| `data-testid="horary-category-{key}"` + `aria-pressed` | ✅ | Category chips |
| `data-testid="horary-submit-btn"` + `aria-disabled` | ✅ | Submit button |
| `data-testid="horary-submit-error"` + `role="alert"` | ✅ | Submit API error |
| `data-testid="horary-blocked-reason"` | ✅ | Validation reason (existing) |
| `data-testid="horary-no-credit-card"` | ✅ | No-credit state |
| `data-testid="horary-history-section"` | ✅ | History section |
| `data-testid="horary-empty-history"` | ✅ | Empty history |
| `data-testid="horary-question-card"` | ✅ | Question cards (existing) |
| `data-testid="horary-processing-card"` | ✅ | Processing card (existing) |

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

### `npx vitest run __tests__/horary/`
```
Test Files  10 passed (10)
     Tests  187 passed (187)
```

### `npx vitest run`
```
Test Files  85 passed (85)
     Tests  886 passed (886)
```

### `E2E_BASE_URL=http://localhost:3000 pnpm exec playwright test e2e/mock-visual --project=mobile`
```
20 passed (1.3m)
```

## No-Op Statement

Canonical port `3002`, systemd, nginx, and bot config were **not** changed. Runtime mocks, MSW, mock-preview API routes, static horary charts/answers, demo data, `SynastryDemo`, and `CelebrityCompatibility` remain **not ported**.

Submit/polling/idempotency/location real API flow was **preserved**.
