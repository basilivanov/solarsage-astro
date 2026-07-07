# Architect Review: Wave 05 `/readings/horary`

Date: 2026-07-07
Status: REWORK_REQUIRED
Reviewed branch: `wave-05-horary-visual-migration`
Reviewed commit: `9d043c5`
Base commit: `df22ab7`
TZ: `docs/work/2026-07-07_frontend-migration-wave-05-horary/00_TZ.md`
Agent report: `docs/work/2026-07-07_frontend-migration-wave-05-horary/01_agent_report.md`

## Verdict

Rework is required before Wave 05 can be accepted.

The implementation keeps the real horary API path in scope: quota, profile, history, create, polling, idempotency, and auto-navigation were not replaced by mocks. It also avoids backend, payment, systemd, nginx, bot, and `3002` changes.

However, the public UI/test contract from the TZ is incomplete in loading/error states, the load-error behavior lacks required unit coverage, and the submit accessibility state needs to be resolved consistently.

## Findings

### 1. Important: `horary-screen` root contract is missing in loading and error states

The TZ requires the root screen to expose:

```text
data-testid="horary-screen"
data-state="loading|ready|error"
```

Currently `horary-screen` exists only in the ready branch. Loading returns only `data-testid="horary-loading"`, and error returns only `data-testid="horary-load-error"`. As a result, headless tests cannot observe a stable screen root across state transitions.

Evidence:

- `components/readings/horary/horary-screen.tsx:325-330`
- `components/readings/horary/horary-screen.tsx:333-347`
- `components/readings/horary/horary-screen.tsx:362-365`

The `screenState = loadError ? "error" : "ready"` expression is also effectively dead for `error`, because the error branch returns before the ready root is rendered.

Required fix:

- Wrap loading, error, and ready render paths in the same public root contract, or render equivalent roots per branch.
- Loading must expose `data-testid="horary-screen"` and `data-state="loading"`, with child `data-testid="horary-loading"` and `role="status"`.
- Error must expose `data-testid="horary-screen"` and `data-state="error"`, with child `data-testid="horary-load-error"` and `role="alert"`.
- Ready must keep `data-testid="horary-screen"`, `data-state="ready"`, and `data-has-credit="true|false"`.
- Do not move hooks below conditional returns.

### 2. Important: initial load failure and retry are not covered by unit tests

The TZ required unit coverage for initial load failure:

```text
initial load failure renders horary-load-error with role=alert and a retry button
```

The added tests cover loading, ready, empty history, and no-credit, but not the failure/retry path.

Evidence:

- `__tests__/horary/horary-screen-flow.test.tsx:258-330`

Required fix:

- Add a unit/component test where one of `getHoraryQuota()`, `listHoraryQuestions()`, or `getProfile()` rejects.
- Assert root `horary-screen` has `data-state="error"`.
- Assert `horary-load-error` has `role="alert"`.
- Assert the retry button calls the same real `loadData()` path and can recover to `data-state="ready"` when mocks resolve on retry.

### 3. Important: submit accessibility state is incomplete and the invalid-submit contract is unresolved

Current submit button only has `aria-disabled={!isValid || submitting}`. It is not natively disabled even while `submitting`, and the blocked validation reason has no `role`.

Evidence:

- `components/readings/horary/horary-form.tsx:228-236`
- `components/readings/horary/horary-form.tsx:261-269`

The original TZ asked for native `disabled` when invalid/submitting. That conflicts with the existing click-to-explain UX covered by `horary-form-submit.test.tsx`, where invalid clicks reveal `horary-blocked-reason`.

Architecture decision for this rework:

- Keep invalid submit interactive so the user can click and receive a concrete blocked reason.
- Use `aria-disabled={!isValid || submitting}` for invalid/submitting state.
- Use native `disabled={submitting}` to prevent duplicate POSTs while a create request is in flight.
- Add `role="alert"` or `role="status"` to `horary-blocked-reason`.
- Update tests to encode this decision:
  - invalid button has `aria-disabled="true"` but is not natively disabled, and clicking shows the blocked reason;
  - submitting button is natively disabled;
  - blocked reason exposes the chosen role.

### 4. Minor: agent report lacks concrete visual comparison evidence

The report states that Wave 05 is a visual migration, but it does not list which screenshot/oracle was used for comparison or whether a local screenshot was captured.

Required fix:

- Add a short `Visual comparison` or `Oracle used` note to the report.
- Reference `docs/superpowers/specs/assets/2026-07-07-mock-preview/readings-horary.png`.
- If a local branch screenshot is captured during rework, report its path only if it is an intentional artifact; do not commit generated screenshots unless explicitly needed.

## Fresh Verification

Architect ran these checks on `9d043c5`:

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
npx vitest run __tests__/horary/horary-screen-flow.test.tsx __tests__/horary/horary-form-submit.test.tsx __tests__/horary/horary-time-confirm.test.tsx __tests__/horary/horary-quota-bar.test.tsx __tests__/horary/horary-question-card.test.tsx __tests__/horary/horary-processing-card.test.tsx __tests__/horary/horary-purchase-sheet.test.tsx __tests__/contracts/horary.test.ts
```

Result: 8 files passed, 125 tests passed.

I did not rerun full Vitest or Playwright after identifying the blocking contract findings above.

## Rework

Rework instructions are in:

```text
docs/work/2026-07-07_frontend-migration-wave-05-horary/03_rework_01_TZ.md
```
