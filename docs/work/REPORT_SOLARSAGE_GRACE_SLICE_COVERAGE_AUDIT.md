# Report: Solar Sage GRACE slice coverage audit

**Status:** PASS (audit only)
**Date:** 2026-06-11
**Baseline SHA:** `ae363c9`
**JSON hash:** `08a50db42ccf`

## How audit was run
```bash
python3 scripts/grace/coverage_audit.py
```

Generated: `docs/work/solarsage_grace_slice_coverage.json`

## Coverage summary

| Metric | Value |
|---|---|
| Total files audited | 497 |
| Full GRACE markers | 117 (23.5%) |
| Partial markers | 342 (68.8%) |
| No markers | 38 (7.6%) |
| Canonical logging | 2 (0.4%) |
| Unmapped | 28 (5.6%) |

## Coverage by slice

| Slice | Total | Full | Partial | None | Coverage | Canonical log |
|---|---|---|---|---|---|---|
| SLICE-TESTS | 126 | 10 | 116 | 0 | 7.9% | 0 |
| SLICE-BACKEND-API-ROUTERS | 41 | 41 | 0 | 0 | 100.0% | 0 |
| SLICE-HORARY-READINGS | 40 | 0 | 40 | 0 | 0.0% | 0 |
| SLICE-OTHER-FRONTEND | 39 | 8 | 30 | 1 | 20.5% | 0 |
| SLICE-BACKEND-SERVICES | 35 | 35 | 0 | 0 | 100.0% | 0 |
| SLICE-OTHER-COMPONENTS | 33 | 0 | 33 | 0 | 0.0% | 0 |
| SLICE-GUARDRAILS-TOOLING | 29 | 12 | 17 | 0 | 41.4% | 2 |
| SLICE-UNMAPPED | 28 | 3 | 9 | 16 | 10.7% | 0 |
| SLICE-SIDECAR-CALCULATION | 23 | 0 | 23 | 0 | 0.0% | 0 |
| SLICE-PROFILE-ONBOARDING | 21 | 0 | 21 | 0 | 0.0% | 0 |
| SLICE-OTHER-BACKEND | 20 | 0 | 0 | 20 | 0.0% | 0 |
| SLICE-FRONTEND-API-FACADES | 15 | 1 | 14 | 0 | 6.7% | 0 |
| SLICE-TODAY-CALENDAR | 12 | 1 | 11 | 0 | 8.3% | 0 |
| SLICE-OTHER-APP | 11 | 0 | 11 | 0 | 0.0% | 0 |
| SLICE-CONTRACTS | 9 | 1 | 7 | 1 | 11.1% | 0 |
| SLICE-ORCHESTRATOR-ADAPTER | 5 | 0 | 5 | 0 | 0.0% | 0 |
| SLICE-LOGGING-SPINE | 5 | 1 | 4 | 0 | 20.0% | 0 |
| SLICE-DB-MODELS-MIGRATIONS | 3 | 3 | 0 | 0 | 100.0% | 0 |
| SLICE-SHELL-NAVIGATION | 2 | 1 | 1 | 0 | 50.0% | 0 |

## Zero-coverage product slices

- **SLICE-HORARY-READINGS**: 40 files, 0% coverage
- **SLICE-OTHER-COMPONENTS**: 33 files, 0% coverage
- **SLICE-SIDECAR-CALCULATION**: 23 files, 0% coverage
- **SLICE-PROFILE-ONBOARDING**: 21 files, 0% coverage
- **SLICE-OTHER-BACKEND**: 20 files, 0% coverage
- **SLICE-OTHER-APP**: 11 files, 0% coverage
- **SLICE-ORCHESTRATOR-ADAPTER**: 5 files, 0% coverage

## Sentinel files

- `apps/api/alembic/env.py` — SLICE-OTHER-BACKEND: no markers, no logging
- `apps/api/alembic/versions/0000_baseline.py` — SLICE-OTHER-BACKEND: no markers, no logging
- `apps/api/alembic/versions/0001_users.py` — SLICE-OTHER-BACKEND: no markers, no logging
- `apps/api/alembic/versions/0002_add_access_ledger.py` — SLICE-OTHER-BACKEND: no markers, no logging
- `apps/api/alembic/versions/0003_add_cache.py` — SLICE-OTHER-BACKEND: no markers, no logging
- `apps/api/alembic/versions/0004_add_semantic.py` — SLICE-OTHER-BACKEND: no markers, no logging
- `apps/api/alembic/versions/0006_add_payments.py` — SLICE-OTHER-BACKEND: no markers, no logging
- `apps/api/alembic/versions/0007_add_evening_checkins.py` — SLICE-OTHER-BACKEND: no markers, no logging
  ... and more

## Recommended adoption waves

| Wave | Priority | Slices |
|---|---|---|
| W-GRACE-SLICE-P0-TODAY-CALENDAR | P0 | Today/Calendar |
| W-GRACE-SLICE-P0-BACKEND-API-SERVICES | P0 | Backend API + services |
| W-GRACE-SLICE-P0-CONTRACTS | P0 | Contracts |
| W-GRACE-SLICE-P1-HORARY-READINGS | P1 | Horary/Readings |
| W-GRACE-SLICE-P1-PROFILE-ONBOARDING | P1 | Profile/Onboarding |
| W-GRACE-SLICE-P1-LOGGING-SPINE | P1 | Logging spine |
| W-GRACE-SLICE-P2-TESTS-TOOLING | P2 | Tests + tooling |
