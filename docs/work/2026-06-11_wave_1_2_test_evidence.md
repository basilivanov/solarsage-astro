# Wave 1–2 Test Evidence

**Date:** 2026-06-11
**Commit:** post-f7c25bda (legacy cleanup)
**Branch:** feat/natal-full-report
**Verdict:** 68 passed, 0 failed, 0 errors

## Test Suites

| Suite | Tests | Status |
|-------|-------|--------|
| test_natal_context_service.py | 24 | All passed |
| test_natal_full_report_api.py | 10 | All passed |
| test_natal_report_service.py | 24 | All passed |
| test_natal_preview.py | 10 | All passed |
| **Total** | **68** | **All passed** |

## Coverage by Feature

### NatalContextService (24 tests)
- `compute_profile_hash` — determinism, sensitivity to each birth field (7 tests)
- Cache hit/miss — sidecar call on miss, reuse on hit, 409 on incomplete profile (3 tests)
- Invalidation — marks invalidated_at, causes sidecar recall (2 tests)
- Sidecar validation — rejects empty planets/houses, accepts valid responses (5 tests)
- No transit contamination — never calls get_transits, no Transit_ in context (2 tests)
- Context data structure — contains angles, sphere_scores, elements_balance, dominants (4 tests)

### Full Report API (10 tests)
- Feature flag gating — 501 on generate/report/report-by-id/section when NATAL_REPORT_ENABLED=False (4 tests)
- Generate with flag — returns report_id, idempotent on repeat, 409 on incomplete profile (3 tests)
- Report retrieval — 404 when no report, 404 for nonexistent report_id (2 tests)
- Preview coexistence — preview works with flag disabled (1 test)

### Report Service (24 tests)
- Block parsing — all 8 block types + fallback + malformed + empty (11 tests)
- Section validation — missing section, empty blocks, empty text, all 8 valid (4 tests)
- Required sections — exactly 8, correct IDs (2 tests)
- LLM input building — valid JSON, contains all planets, no transit planets (3 tests)
- Context hash — deterministic, changes on context change (2 tests)
- Section prompt instructions — all sections have instructions, unknown fallback (2 tests)

### Preview (10 tests)
- Profile validation — 409 without gender, 409 without birth coords (2 tests)
- Sidecar error — 502 with SOLARSAGE_UNAVAILABLE code, no raw leak (1 test)
- Response structure — price 99900, male wording, female wording (3 tests)
- Calculation stats — 350+ bucket, exact count (2 tests)
- Content — 8 chapters, at least 5 spheres (2 tests)

## Environment
- Python 3.12.13
- SQLite in-memory (test DB)
- Sidecar mocked via `unittest.mock.patch`
- No external services required

## Changes Since Acceptance Review (f7c25bda)
- Removed legacy endpoints `GET /api/natal/overview` and `GET /api/natal/section/{section_id}`
- Removed `NatalService.get_natal_reading()` method and unused imports
- Removed `tests/test_natal.py` (tested only legacy endpoints)
- Updated `test_natal_preview.py` to mock `natal_context_service.get_solarsage_client` (was `natal_service.get_solarsage_client`)
- Updated `test_natal_full_report_api.py` coexistence test to remove stale mock patch
- Updated module contracts in `natal.py` and `natal_service.py`
