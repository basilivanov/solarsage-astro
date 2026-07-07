---
id: adr-001
title: Headless Testing Strategy
status: active
wave: W-TEST
date: 2026-05-30
last_review: 2026-07-07
---

# ADR-001: Headless Testing Strategy

## Status

Accepted. Updated on 2026-07-07 after the real-data frontend migration discussion.

## Context

SolarSage Astro is currently operated as a dev/staging product, but it already has a canonical app runtime:

- `main` branch.
- `solarsage-frontend.service` on port `3002`.
- Nginx public entrypoint.
- FastAPI on port `8000`.
- Telegram WebApp auth via HMAC.

This canonical runtime is not a mock sandbox. It must behave like the future tagged release runtime even before a production tag exists.

The migration goal is to make the canonical frontend look like the old mock-preview frontend while keeping all product facts backed by real backend/SolarSage contracts.

## Decision

Use a layered headless testing strategy:

1. Unit/component tests for local logic and presentation.
2. Contract tests to keep frontend fixtures and adapters aligned with backend schemas.
3. Mock e2e/visual tests using Playwright route interception.
4. Real e2e tests using real Telegram HMAC auth and real API calls.
5. Guardrail tests proving canonical app runtime does not import runtime mocks.

MSW is not part of this strategy. We do not add a service-worker-style mock runtime for this migration. Mocking for e2e is test-only and lives in Playwright `page.route('/api/**', ...)` handlers.

## Testing Layers

### 1. Unit And Component Tests

Tools:

- Vitest for frontend logic/components.
- Pytest for backend services/endpoints.

Purpose:

- Pure functions, adapters, reducers, hooks.
- Component states with stable props.
- Backend service behavior and endpoint contracts.

Mocking boundary:

- Use `vi.mock(...)`, `global.fetch = vi.fn()`, pytest fixtures, and service mocks only inside tests.
- Do not import runtime demo data into product paths.

### 2. Contract Tests

Purpose:

- Prove generated contracts and frontend adapters match backend schemas.
- Prove mock fixtures used by e2e represent real contract shapes.

Required checks:

- `pnpm contracts:check` when contracts change.
- Vitest contract tests under `__tests__/contracts/`.
- Adapter tests for any API shape converted into view models.
- Backend pytest for schema/service changes.

Rule:

Mock fixtures are allowed only if they validate against the same contract shape expected from the real API.

### 3. Mock E2E / Visual Parity Tests

Tool:

- Playwright with `page.route('/api/**', ...)`.

Purpose:

- Validate frontend presentation on stable API payloads.
- Catch missing migrated UI blocks.
- Exercise hard-to-reproduce states: loading, error, empty, locked, quota exhausted, report generating.
- Produce stable visual regression baselines.

Non-purpose:

- Does not prove Telegram auth works.
- Does not prove backend/sidecar/API integration works.
- Does not prove cache, systemd, nginx, or database behavior.

Recommended Playwright project name:

- `mock-visual` or `mock-parity`.

Implementation rules:

- Route handlers live under `e2e/` or test-only fixtures.
- Do not use MSW.
- Do not add mock branches to `lib/api/*`.
- Keep dynamic text masked or asserted structurally.

Example:

```ts
test.beforeEach(async ({ page }) => {
  await page.route("**/api/**", async (route) => {
    const url = new URL(route.request().url())
    if (url.pathname === "/api/day/2026-07-05") {
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(dayFixture),
      })
    }
    return route.fallback()
  })
})
```

### 4. Real E2E Tests

Tool:

- Playwright with the existing real Telegram auth fixtures.

Purpose:

- Prove canonical runtime works end to end.
- Exercise Telegram HMAC initData, session cookies, API, backend read models, and frontend rendering.

Current pattern:

- `e2e/fixtures.ts` generates signed Telegram initData via `scripts/generate-telegram-test-initdata.py`.
- Tests run against `E2E_BASE_URL`, defaulting to `http://localhost:3002`.

Rule:

Real e2e must not use route interception for `/api/**`.

### 5. Visual Regression

Visual regression is required but scoped.

Use it for key screens and states:

- `/day/:date`
- `/calendar`
- `/profile`
- `/readings`
- `/readings/horary`
- `/readings/natal`
- locked
- empty
- loading/error
- generating

Avoid pixel-perfect coverage for every component and every dynamic text variant.

Dynamic regions should be:

- masked;
- replaced by stable fixtures in mock e2e;
- or asserted structurally with roles/test ids instead of screenshot pixels.

### 6. Runtime Mock Guardrail

Canonical app runtime means:

- `main`.
- `3002`.
- Telegram WebApp public URL.
- Future production tag/runtime.

This runtime must not import or execute runtime mocks:

- no `lib/mocks/*` imports from product paths;
- no `lib/demo-data.ts` fallback in product paths;
- no mock Next catch-all API in the canonical app;
- no "if API fails, show demo data" behavior.

Mocks may exist only in:

- tests;
- Playwright route handlers;
- test fixtures;
- archived visual reference worktrees.

## Temporary Visual Oracle

`/opt/solarsage-astro-mock-preview` on port `3001` may be used temporarily as a visual oracle while migrating UI to `main`.

This is a migration aid only.

It is not:

- a product runtime;
- a merge target;
- a source of API behavior;
- an acceptance gate after visual baselines exist.

After migration, the source of truth becomes:

- contract-valid fixtures;
- visual snapshots;
- real e2e;
- no-runtime-mocks guardrails.

## UI Semantic/Test Contract

Frontend must expose a stable DOM/accessibility contract:

- stable root `data-testid` per major screen;
- `data-state` for loading/ready/empty/error/locked states;
- `data-status` for domain status enums;
- `aria-current`, `aria-expanded`, `aria-busy`, `aria-invalid`, `aria-pressed`;
- `role="status"`, `role="alert"`, `role="dialog"` where appropriate;
- accessible names for icon-only buttons.

Tests should prefer roles and public DOM attributes over CSS classes or React internals.

## Merge Gate For Frontend Migration

Minimum gate for merging visual migration into `main`:

```text
unit/component tests
+ contract tests
+ mock visual/structural e2e
+ real e2e
+ no-runtime-mocks guardrail
```

The mock e2e layer can prove the frontend looks correct on known data. The real e2e layer proves the product works on real data.

## Consequences

Positive:

- Visual migration can be tested deterministically.
- Mock data remains isolated from canonical runtime.
- Real e2e remains close to how users open the Telegram Mini App.
- Regression failures are easier to classify: presentation vs contract vs runtime.

Negative:

- There are two e2e modes to maintain.
- Visual baselines require review when UI changes intentionally.
- Fixtures must be kept contract-valid.

Mitigations:

- Keep fixtures small and route-specific.
- Validate fixture shapes in contract tests.
- Use masks for dynamic text.
- Keep mock e2e as visual/structural, not as the final product gate.

## References

- `playwright.config.ts`
- `e2e/fixtures.ts`
- `scripts/generate-telegram-test-initdata.py`
- `__tests__/guardrails/no-runtime-mocks.test.ts`
- `docs/visual-regression-testing.md`
- `docs/superpowers/specs/2026-07-05-real-data-frontend-migration-design.md`
