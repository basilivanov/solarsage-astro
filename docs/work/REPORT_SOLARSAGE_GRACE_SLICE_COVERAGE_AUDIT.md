# Report: Solar Sage GRACE slice coverage audit

**Status:** PASS (audit only)
**Date:** 2026-06-11

## Baseline SHA
- `fa2b7db`

## How audit was run
```bash
python3 scripts/grace/coverage_audit.py
```

Generated: `docs/work/solarsage_grace_slice_coverage.json` (496 files, 15 slices)

## Coverage summary

| Metric | Value |
|--------|-------|
| Total files audited | 496 |
| Full GRACE markers | 60 (12.1%) |
| Partial markers | 32 (6.5%) |
| No markers | 404 (81.5%) |
| Canonical logging | 1 (0.2%) |
| Unmapped | 109 (22.0%) |

## Coverage by slice

| Slice | Total | Full | Partial | None | Coverage | Canonical log |
|---|---|---|---|---|---|---|
| SLICE-BACKEND-API-ROUTERS | 26 | 24 | 0 | 2 | 92.3% | 0 |
| SLICE-CONTRACTS | 8 | 5 | 0 | 3 | 62.5% | 0 |
| SLICE-ORCHESTRATOR-ADAPTER | 22 | 14 | 8 | 0 | 63.6% | 0 |
| SLICE-GUARDRAILS-TOOLING | 7 | 6 | 0 | 1 | 85.7% | 1 |
| SLICE-TESTS | 3 | 2 | 1 | 0 | 66.7% | 0 |
| SLICE-DB-MODELS-MIGRATIONS | 7 | 4 | 3 | 0 | 57.1% | 0 |
| SLICE-BACKEND-SERVICES | 14 | 3 | 5 | 6 | 21.4% | 0 |
| SLICE-SCORING-SEMANTIC-LLM | 10 | 2 | 4 | 4 | 20.0% | 0 |
| SLICE-SIDECAR-CALCULATION | 2 | 0 | 0 | 2 | 0.0% | 0 |
| SLICE-SHELL-NAVIGATION | 3 | 0 | 0 | 3 | 0.0% | 0 |
| SLICE-TODAY-CALENDAR | 19 | 0 | 0 | 19 | 0.0% | 0 |
| SLICE-FRONTEND-API-FACADES | 12 | 0 | 0 | 12 | 0.0% | 0 |
| SLICE-HORARY-READINGS | 2 | 0 | 0 | 2 | 0.0% | 0 |
| SLICE-PROFILE-ONBOARDING | 3 | 0 | 0 | 3 | 0.0% | 0 |
| SLICE-LOGGING-SPINE | 6 | 0 | 4 | 2 | 0.0% | 0 |
| SLICE-OTHER-BACKEND | 31 | 0 | 7 | 24 | 0.0% | 0 |
| SLICE-UNMAPPED | 109 | 0 | 0 | 109 | 0.0% | 0 |

## Files with markers but no declared logging side-effects
All 60 fully-marked files declare MODULE_CONTRACT but none declare logging in their contract. Only `grace/requirements.xml` mentions logging via `SLICE-LOGGING-SPINE`.

## Slices with zero GRACE markers (product frontend)
These are the main product frontend slices — they need adoption waves:
- **SLICE-SHELL-NAVIGATION**: `components/app-shell.tsx`, `components/today/tab-bar.tsx` (3 files)
- **SLICE-TODAY-CALENDAR**: `components/today/*`, `app/(grace)/today/`, `lib/today.ts` (19 files)
- **SLICE-FRONTEND-API-FACADES**: `lib/api/*`, `lib/access.ts` (12 files)
- **SLICE-HORARY-READINGS**: `components/readings/` (2 files)
- **SLICE-PROFILE-ONBOARDING**: `components/profile/`, `components/onboarding/` (3 files)
- **SLICE-LOGGING-SPINE**: `lib/grace/` (6 files — has some markers but incomplete)

## Recommended adoption waves

| Wave | Priority | Slice | Files | Effort |
|---|---|---|---|---|
| W-GRACE-SLICE-P0-TODAY-CALENDAR | P0 | Today/Calendar | ~19 files | Small |
| W-GRACE-SLICE-P0-BACKEND-API-SERVICES | P0 | Backend services | ~14 files | Medium |
| W-GRACE-SLICE-P0-CONTRACTS | P0 | Contracts | ~8 files | Small |
| W-GRACE-SLICE-P1-HORARY-READINGS | P1 | Horary/Readings | ~2 files | Small |
| W-GRACE-SLICE-P1-PROFILE-ONBOARDING | P1 | Profile/Onboarding | ~3 files | Small |
| W-GRACE-SLICE-P1-LOGGING-SPINE | P1 | Logging spine | ~6 files | Medium |
| W-GRACE-SLICE-P2-TESTS-TOOLING | P2 | Tests + tooling | ~10 files | Medium |

## Gates
- `pnpm test:run` — not required (audit-only, no product code changed)
- Script is deterministic (run twice produces identical JSON)
