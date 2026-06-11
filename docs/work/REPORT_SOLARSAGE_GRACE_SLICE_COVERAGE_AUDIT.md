# Report: Solar Sage GRACE slice coverage audit

**Status:** PASS (audit only)
**Date:** 2026-06-11
**Baseline SHA:** `d0471fa`
**JSON hash:** `d6f78e3ca93d`

## How audit was run
```bash
python3 scripts/grace/coverage_audit.py
```

Generated: `docs/work/solarsage_grace_slice_coverage.json`

## Coverage summary

| Metric | Value |
|---|---|
| Total files audited | 497 |
| Full GRACE markers | 430 (86.5%) |
| Partial markers | 7 (1.4%) |
| No markers | 60 (12.1%) |
| Canonical logging | 1 (0.2%) |
| Unmapped | 28 (5.6%) |

## Coverage by slice

| Slice | Total | Full | Partial | None | Coverage | Canonical log |
|---|---|---|---|---|---|---|
| SLICE-TESTS | 126 | 126 | 0 | 0 | 100.0% | 0 |
| SLICE-BACKEND-API-ROUTERS | 41 | 41 | 0 | 0 | 100.0% | 0 |
| SLICE-HORARY-READINGS | 40 | 40 | 0 | 0 | 100.0% | 0 |
| SLICE-OTHER-FRONTEND | 39 | 38 | 0 | 1 | 97.4% | 0 |
| SLICE-BACKEND-SERVICES | 35 | 35 | 0 | 0 | 100.0% | 0 |
| SLICE-OTHER-COMPONENTS | 33 | 33 | 0 | 0 | 100.0% | 0 |
| SLICE-GUARDRAILS-TOOLING | 29 | 6 | 6 | 17 | 20.7% | 1 |
| SLICE-UNMAPPED | 28 | 11 | 1 | 16 | 39.3% | 0 |
| SLICE-SIDECAR-CALCULATION | 23 | 23 | 0 | 0 | 100.0% | 0 |
| SLICE-PROFILE-ONBOARDING | 21 | 21 | 0 | 0 | 100.0% | 0 |
| SLICE-OTHER-BACKEND | 20 | 0 | 0 | 20 | 0.0% | 0 |
| SLICE-FRONTEND-API-FACADES | 15 | 15 | 0 | 0 | 100.0% | 0 |
| SLICE-TODAY-CALENDAR | 12 | 12 | 0 | 0 | 100.0% | 0 |
| SLICE-OTHER-APP | 11 | 11 | 0 | 0 | 100.0% | 0 |
| SLICE-CONTRACTS | 9 | 8 | 0 | 1 | 88.9% | 0 |
| SLICE-ORCHESTRATOR-ADAPTER | 5 | 0 | 0 | 5 | 0.0% | 0 |
| SLICE-LOGGING-SPINE | 5 | 5 | 0 | 0 | 100.0% | 0 |
| SLICE-DB-MODELS-MIGRATIONS | 3 | 3 | 0 | 0 | 100.0% | 0 |
| SLICE-SHELL-NAVIGATION | 2 | 2 | 0 | 0 | 100.0% | 0 |

## Zero-coverage product slices

- **SLICE-OTHER-BACKEND**: 20 files, 0% coverage
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
