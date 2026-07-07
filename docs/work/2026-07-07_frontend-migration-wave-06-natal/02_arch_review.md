# Architect Review: Wave 06 `/readings/natal`

Date: 2026-07-07
Status: REWORK_REQUIRED
Reviewed branch: `wave-06-natal-visual-migration`
Reviewed commit: `44dd537`
Base commit: `d8536f5`
TZ: `docs/work/2026-07-07_frontend-migration-wave-06-natal/00_TZ.md`
Agent report: `docs/work/2026-07-07_frontend-migration-wave-06-natal/01_agent_report.md`

## Verdict

Rework is required before Wave 06 can be accepted.

The implementation is correctly scoped: it does not change backend contracts, systemd/nginx/bot/`3002`, payment, runtime mocks, MSW, `DEMO_NATAL_RESPONSE`, or product mock imports. It also keeps the product page on the real `fetchNatalPreview()` / `NatalPreviewRead` path.

However, several explicit public DOM/test-contract requirements from the TZ are incomplete.

## Findings

### 1. Important: `data-full-report-available` is hardcoded instead of using `NatalPreviewRead`

The root screen sets:

```tsx
data-full-report-available={statusAttr === "ready" ? "false" : undefined}
```

This violates the TZ requirement that the ready root expose real `data-full-report-available="true|false"` from `NatalPreviewRead`.

Evidence:

- `app/(grace)/readings/natal/page.tsx:74`

Required fix:

- Derive the attribute from `state.data.fullReportAvailable` when `state.status === "ready"`.
- Keep CTA fulfillment/payment disabled in this wave. This finding is only about truthful DOM state, not enabling payment.
- Add/adjust a component test with `fullReportAvailable: true` proving the root attribute becomes `"true"` while the CTA remains natively disabled.

### 2. Important: required `natal-hero-badges` selector is missing

The TZ explicitly requires:

```text
data-testid="natal-hero-badges"
```

The implementation added `natal-hero` but did not expose `natal-hero-badges`.

Evidence:

- `app/(grace)/readings/natal/page.tsx:98-104`
- `components/readings/natal-preview/hero-section.tsx` has no `natal-hero-badges`

Required fix:

- Add `data-testid="natal-hero-badges"` to the real badges container in `HeroSection` when badges are rendered, or add an equivalent stable wrapper that is present when the hero has badge data.
- Assert it in unit or mock-visual e2e.

### 3. Important: required component tests were not added

Wave 06 TZ required component coverage for:

- loading root state and `natal-preview-loading role=status`;
- ready root state and `data-full-report-available`;
- error state `natal-preview-error role=alert` plus retry recovery;
- profile-incomplete state `natal-profile-incomplete`;
- chart unavailable when `chart=null`.

The implementation did not modify `__tests__/natal/natal-component-states.test.tsx`, so these requirements are not covered.

Evidence:

- `git diff --name-only d8536f5..44dd537` does not include `__tests__/natal/natal-component-states.test.tsx`.
- Existing tests around `__tests__/natal/natal-component-states.test.tsx:210-240` still only cover chart rendering and disabled CTA.

Required fix:

- Update `__tests__/natal/natal-component-states.test.tsx`.
- Keep tests independent from Tailwind class names.
- For retry, use a deterministic mock gate: reject until the test explicitly clicks retry, then resolve. Do not repeat the horary flake pattern.

### 4. Important: mock visual e2e is missing profile-incomplete coverage

The TZ required:

```text
assert profile-incomplete state renders natal-profile-incomplete for a 409 fixture
```

The new mock visual spec covers ready, chart-unavailable, overflow, and negative-proof, but not profile-incomplete.

Evidence:

- `e2e/mock-visual/natal.spec.ts:28-144`

Required fix:

- Add a profile-incomplete mock visual test.
- Route `/api/natal/preview` with `status: 409` and a contract-like body containing `detail.message` and `detail.missingFields`.
- Assert `natal-preview-screen` has `data-state="profile_incomplete"`.
- Assert `natal-profile-incomplete` is visible and has the chosen alert/status role.
- Assert no missing API fixtures after quiet wait.

## Fresh Verification

Architect ran these checks on `44dd537`:

```bash
git diff --check d8536f5..44dd537
```

Result: passed, exit code 0.

```bash
git diff --check main..HEAD
```

Result: passed, exit code 0.

```bash
git diff --check
```

Result: passed, exit code 0.

```bash
pnpm exec tsc --noEmit --pretty false
```

Result: passed, exit code 0.

```bash
npx vitest run __tests__/natal/natal-component-states.test.tsx __tests__/api/natal-report.test.ts __tests__/contracts/natal.test.ts __tests__/guardrails/no-runtime-mocks.test.ts
```

Result: 4 files passed, 58 tests passed.

I did not rerun full Vitest or Playwright after identifying the blocking contract findings above.

## Rework

Rework instructions are in:

```text
docs/work/2026-07-07_frontend-migration-wave-06-natal/03_rework_01_TZ.md
```
