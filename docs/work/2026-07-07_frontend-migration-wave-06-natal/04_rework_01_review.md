# Architect Review: Wave 06 `/readings/natal` Rework 01

Date: 2026-07-07
Status: REWORK_REQUIRED
Reviewed branch: `wave-06-natal-visual-migration`
Reviewed commit: `e4101d8`
Base rework TZ: `docs/work/2026-07-07_frontend-migration-wave-06-natal/03_rework_01_TZ.md`
Agent report: `docs/work/2026-07-07_frontend-migration-wave-06-natal/01_agent_report.md`

## Verdict

Rework 01 fixed the product-side issues:

- `data-full-report-available` is now derived from `state.data.fullReportAvailable`;
- `natal-hero-badges` is present in the real hero badges container;
- profile-incomplete e2e coverage was added;
- the implementation remains on the real `fetchNatalPreview()` / `NatalPreviewRead` flow.

Acceptance is still blocked by incomplete test-contract assertions and an inaccurate report SHA.

## Findings

### 1. Important: `fullReportAvailable=true` component test does not assert CTA disabled state

Rework 01 TZ explicitly required the component test with `fullReportAvailable: true` to assert:

- `natal-preview-screen` has `data-full-report-available="true"`;
- `natal-full-report-cta` exists;
- the CTA button is natively disabled;
- the CTA button has `aria-disabled="true"`.

Current test includes the comment but only asserts the wrapper exists.

Evidence:

- `__tests__/natal/natal-component-states.test.tsx:261-282`

Required fix:

- In the existing `fullReportAvailable: true` component test, assert the actual button under `natal-full-report-cta`:

```tsx
const button = within(cta).getByRole("button", { name: "Полный отчёт скоро появится" })
expect(button).toBeDisabled()
expect(button).toHaveAttribute("aria-disabled", "true")
```

- Import `within` from `@testing-library/react` if needed.
- Keep payment/fulfillment disabled.

### 2. Important: `natal-hero-badges` is not asserted by any test

The selector is now present in product code, but the rework TZ required an assertion proving it is present when the preview contains badge data.

Evidence:

- Product selector exists at `components/readings/natal-preview/hero-section.tsx:69`
- Component test ready-state assertions do not check `natal-hero-badges`
- Mock visual ready-state test checks `natal-hero`, but not `natal-hero-badges`: `e2e/mock-visual/natal.spec.ts:49-50`

Required fix:

- Add an assertion in either the component ready-state test or the mock-visual ready-state test.
- Prefer both, because this selector is part of the UI Semantic/Test Contract and is cheap to cover:
  - component: `screen.getByTestId("natal-hero-badges")`;
  - e2e: `await expect(page.getByTestId("natal-hero-badges")).toBeVisible()`.

### 3. Important: agent report records the wrong rework commit SHA

The callback and git history identify Rework 01 commit as `e4101d8`, but the report says `a865cfc`.

Evidence:

- `docs/work/2026-07-07_frontend-migration-wave-06-natal/01_agent_report.md:106`
- `git log --oneline -1` returned `e4101d8`

Required fix:

- Update the Rework 01 section to record `e4101d8`.
- Add a Rework 02 section with the new commit SHA and exact gates.
- Add `natal-hero-badges` to the UI Semantic/Test Contract table.

## Fresh Verification

Architect ran these checks on `e4101d8`:

```bash
git diff --check 19cb541..e4101d8
git diff --check main..HEAD
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

Result: 4 files passed, 63 tests passed.

I did not rerun full Vitest or Playwright after identifying the blocking assertion gaps above.

## Rework

Rework instructions are in:

```text
docs/work/2026-07-07_frontend-migration-wave-06-natal/05_rework_02_TZ.md
```
