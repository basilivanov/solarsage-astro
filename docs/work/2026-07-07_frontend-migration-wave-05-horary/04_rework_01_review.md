# Architect Review: Wave 05 Rework 01 `/readings/horary`

Date: 2026-07-07
Status: REWORK_REQUIRED
Reviewed branch: `wave-05-horary-visual-migration`
Reviewed commit: `c304a71`
Base review: `docs/work/2026-07-07_frontend-migration-wave-05-horary/02_arch_review.md`
Rework TZ: `docs/work/2026-07-07_frontend-migration-wave-05-horary/03_rework_01_TZ.md`

## Verdict

Rework 01 is not accepted because the TypeScript gate fails.

The functional rework is otherwise on the right track: `horary-screen` is now present across loading/error/ready states, load-error retry tests were added, and submit accessibility was resolved as `aria-disabled` for invalid plus native `disabled` for submitting.

## Findings

### 1. Blocking: TypeScript fails because `afterEach` is used but not imported

`__tests__/horary/horary-screen-flow.test.tsx` imports:

```ts
import { describe, it, expect, vi, beforeEach } from "vitest";
```

The new load-error test block uses `afterEach(...)`, but `afterEach` is not imported. Vitest still ran the test file, but `pnpm exec tsc --noEmit --pretty false` correctly fails.

Evidence:

- `__tests__/horary/horary-screen-flow.test.tsx:22`
- `__tests__/horary/horary-screen-flow.test.tsx:332`

Fresh command result:

```bash
pnpm exec tsc --noEmit --pretty false
```

Result:

```text
__tests__/horary/horary-screen-flow.test.tsx(332,3): error TS2304: Cannot find name 'afterEach'.
```

Required fix:

- Import `afterEach` from `vitest`, or remove the `afterEach` block if it is not necessary.
- Re-run the full required gate set from `05_rework_02_TZ.md`.

### 2. Minor: report still has a placeholder commit value

The report's `Rework 01` section says:

```text
Commit: `[this commit]`
```

Required fix:

- Replace it with the actual Rework 01 commit SHA: `c304a71`.
- Add a `Rework 02` note with the new commit SHA and gate results.

## Fresh Verification

Architect ran these checks on `c304a71`:

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

Result: failed, exit code 2, missing `afterEach` import.

```bash
npx vitest run __tests__/horary/horary-screen-flow.test.tsx __tests__/horary/horary-form-submit.test.tsx __tests__/horary/horary-time-confirm.test.tsx __tests__/horary/horary-quota-bar.test.tsx __tests__/horary/horary-question-card.test.tsx __tests__/horary/horary-processing-card.test.tsx __tests__/horary/horary-purchase-sheet.test.tsx __tests__/contracts/horary.test.ts
```

Result: 8 files passed, 130 tests passed.

I did not run full Vitest or Playwright after the TypeScript gate failed.

## Rework

Rework instructions are in:

```text
docs/work/2026-07-07_frontend-migration-wave-05-horary/05_rework_02_TZ.md
```
