# ESLint Debt Cleanup Report

## Before

| Metric | Value |
|--------|-------|
| Errors | 298 |
| Warnings | 2 |
| Files affected | 75 |
| Rules broken | 5 |

**Rule breakdown:**
- `no-undef`: 227 (browser/DOM/React globals not configured for flat config)
- `no-unused-vars`: 60 (imports, callback params, variables, type params)
- `no-empty`: 10 (empty `catch {}` blocks in `telegram-init.tsx`)
- `react-hooks/exhaustive-deps`: 2 (pre-existing warnings, not fixed)
- `@next/next/no-img-element`: 1

## After

| Metric | Value |
|--------|-------|
| Errors | **0** |
| Warnings | 2 (pre-existing `exhaustive-deps`) |
| Files affected | 0 |

## What Changed

### `eslint.config.mjs` — 3 changes

1. **`languageOptions.globals`** block with 30 browser/DOM/React/event globals (`window`, `document`, `fetch`, `console`, `React`, `HTMLElement`, `KeyboardEvent`, etc.) — eliminated all 227 `no-undef` errors.
2. **`no-unused-vars` ignore patterns** — `argsIgnorePattern: "^_"` and `varsIgnorePattern: "^_"` so TypeScript `_`-prefixed unused params are accepted.
3. **`apps/solarsage/**` added to ignores** (Python venv JS files).

### 32 source files batch-fixed

| Pattern | Files | Count |
|---------|-------|-------|
| Unused imports removed (`fireEvent`, `Sparkles`, `HelpCircle`, `Calendar`, `Edit2`, `afterEach`) | 6 | ~12 errors |
| Unused callback params renamed with `_` prefix | 15 | ~28 errors |
| Unused destructured vars removed (`name` from `HeroSection`) | 3 | ~5 errors |
| Unused consts removed/commented | 3 | ~4 errors |
| Unused type params renamed with `_` prefix (`[k in string]` → `[_k in string]`) | 3 | ~6 errors |
| Commented-out `useCallback` body properly commented | 1 | 1 parse error |
| `catch {}` → `catch { /* noop */ }` | 10 blocks in 1 file | 10 errors |
| Stale `eslint-disable` directives removed | 2 files (`avatar.tsx`, `production-guard.mjs`) | 1 error |

### Files not modified

- `react-hooks/exhaustive-deps` warnings (2 files) — left as-is
- No type definitions changed — all fixes are surface-level (names, comments, config)
- No global rule disables, no blanket `eslint-disable`, no new dependencies, no reformatting

## Verification

- `pnpm lint` — 0 errors, 2 warnings
- `pnpm typecheck` (tsc --noEmit) — passes
- `pnpm test:run` — 746 passed, 1 skipped (same as before)

## Branch

`chore/eslint-debt-cleanup` (pushed to origin). PR: https://github.com/basilivanov/solarsage-astro/pull/new/chore/eslint-debt-cleanup
