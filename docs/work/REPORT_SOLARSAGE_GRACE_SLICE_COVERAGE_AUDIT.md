# Report: Solar Sage GRACE slice coverage audit

**Status:** PASS (audit only)
**Date:** 2026-06-11
**Baseline SHA:** `9dedaf9`
**JSON hash:** `5b8c0d8e625a`

## How audit was run
```bash
python3 scripts/grace/coverage_audit.py
```

Generated: `docs/work/solarsage_grace_slice_coverage.json`

## Coverage summary

| Metric | Value |
|---|---|
| Total files audited | 497 |
| Full GRACE markers | 276 (55.5%) |
| Partial markers | 12 (2.4%) |
| No markers | 209 (42.1%) |
| Canonical logging | 1 (0.2%) |
| Unmapped | 28 (5.6%) |

## Coverage by slice

| Slice | Total | Full | Partial | None | Coverage | Canonical log |
|---|---|---|---|---|---|---|
| SLICE-TESTS | 126 | 5 | 5 | 116 | 4.0% | 0 |
| SLICE-BACKEND-API-ROUTERS | 41 | 39 | 0 | 2 | 95.1% | 0 |
| SLICE-HORARY-READINGS | 40 | 40 | 0 | 0 | 100.0% | 0 |
| SLICE-OTHER-FRONTEND | 39 | 38 | 0 | 1 | 97.4% | 0 |
| SLICE-BACKEND-SERVICES | 35 | 34 | 0 | 1 | 97.1% | 0 |
| SLICE-OTHER-COMPONENTS | 33 | 33 | 0 | 0 | 100.0% | 0 |
| SLICE-GUARDRAILS-TOOLING | 29 | 6 | 6 | 17 | 20.7% | 1 |
| SLICE-UNMAPPED | 28 | 11 | 1 | 16 | 39.3% | 0 |
| SLICE-SIDECAR-CALCULATION | 23 | 0 | 0 | 23 | 0.0% | 0 |
| SLICE-PROFILE-ONBOARDING | 21 | 21 | 0 | 0 | 100.0% | 0 |
| SLICE-OTHER-BACKEND | 20 | 0 | 0 | 20 | 0.0% | 0 |
| SLICE-FRONTEND-API-FACADES | 15 | 15 | 0 | 0 | 100.0% | 0 |
| SLICE-TODAY-CALENDAR | 12 | 12 | 0 | 0 | 100.0% | 0 |
| SLICE-OTHER-APP | 11 | 11 | 0 | 0 | 100.0% | 0 |
| SLICE-CONTRACTS | 9 | 1 | 0 | 8 | 11.1% | 0 |
| SLICE-ORCHESTRATOR-ADAPTER | 5 | 0 | 0 | 5 | 0.0% | 0 |
| SLICE-LOGGING-SPINE | 5 | 5 | 0 | 0 | 100.0% | 0 |
| SLICE-DB-MODELS-MIGRATIONS | 3 | 3 | 0 | 0 | 100.0% | 0 |
| SLICE-SHELL-NAVIGATION | 2 | 2 | 0 | 0 | 100.0% | 0 |

## Zero-coverage product slices

- **SLICE-SIDECAR-CALCULATION**: 23 files, 0% coverage
- **SLICE-OTHER-BACKEND**: 20 files, 0% coverage
- **SLICE-ORCHESTRATOR-ADAPTER**: 5 files, 0% coverage

## Sentinel files

- `__tests__/api/access.test.ts` — SLICE-TESTS: no markers, no logging
- `__tests__/api/calendar.test.ts` — SLICE-TESTS: no markers, no logging
- `__tests__/api/cities.test.ts` — SLICE-TESTS: no markers, no logging
- `__tests__/api/geo.test.ts` — SLICE-TESTS: no markers, no logging
- `__tests__/api/grace-client.test.ts` — SLICE-TESTS: no markers, no logging
- `__tests__/api/natal-report.test.ts` — SLICE-TESTS: no markers, no logging
- `__tests__/api/onboarding-payload.test.ts` — SLICE-TESTS: no markers, no logging
- `__tests__/api/profile-meta.test.ts` — SLICE-TESTS: no markers, no logging
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
