# Report: Solar Sage full-repo GRACE canon adoption

**Status:** PASS
**Date:** 2026-06-12

## Waves executed

| Wave | Scope | Files changed |
|---|---|---|
| W1 | Frontend runtime (`app/`, `components/`, `hooks/`, `lib/`) | 182 |
| W2 | Backend runtime (`apps/api/app/`) | 55 |
| W3 | Sidecar/calculation (`apps/solarsage/`) | 2 |
| W4 | Contracts/facades/logging spine | 7 |
| W5 | Tests (`__tests__/`) | 64 |
| W6 | Tooling/guardrails/project adapter | 30 |
| **Total** | | **~340** |

## Coverage before → after

| Metric | Before | After |
|---|---|---|
| Full GRACE markers | 93 (18.8%) | **458 (92.2%)** |
| Partial markers | 20 (4.0%) | 1 (0.2%) |
| No markers | 383 (77.1%) | **38 (7.6%)** |

## Counts

| Marker | Added/Fixed |
|---|---|
| AI_HEADER | ~400 added |
| MODULE_CONTRACT | ~350 added |
| MODULE_MAP | ~350 added |
| START_BLOCK/END_BLOCK | ~200 added |

## Files skipped (38 remaining, per TZ)
- Alembic migrations (18 files) — generated historical
- e2e tests (6 files) — unmapped, need architect decision
- Config files (eslint, next, postcss, etc.) — framework
- `packages/contracts/_generated.ts` — generated
- `types/telegram-web-app.d.ts` — vendored types
- Bootstrap scripts (astro-ctl, bootstrap*.sh) — tooling

## Gates

| Gate | Result |
|---|---|
| `coverage_audit.py --check` | OK (sentinel checks pass, JSON deterministic) |
| `pnpm test:run` | **756 passed, 1 skipped** ✅ |
| Runtime behavior | Unchanged (only comment markers added) |

## Commits
- W1: `ec904b3`
- W2: `2626cb1`
- W3: `18dade8`
- W4: `d0471fa`
- W5: `f6a8164`
- W6: `9738fa9`
