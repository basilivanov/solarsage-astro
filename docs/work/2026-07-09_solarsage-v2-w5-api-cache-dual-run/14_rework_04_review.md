# W5 Rework 04 Architect Review

Status: REWORK REQUIRED

Reviewed implementation commit: `aedbdc4`
Report commit: `152b186`
Reviewed against: `12_rework_04_TZ.md`

## Findings

### P0 — Required service-level integration tests are still missing

Evidence:
- Rework 04 changed only `apps/api/tests/test_calendar_endpoints.py`.
- `apps/api/tests/test_today_meta_versions.py:295-329` still contains the false-positive test that directly awaits `mock_client.get_activation_layer()` and never exercises `TodayService`.
- `apps/api/tests/test_today_service_v2_dual_run.py` still exercises only `DayScoringRuntimeService`.
- `apps/api/tests/test_calendar_v2_dual_run.py` still exercises only `DayScoringRuntimeService`.
- `apps/api/tests/test_today_cache_v2_key.py` still tests pure hash construction only. It does not insert DB rows, call TodayService cache helpers, or prove SQL lookup/upsert behavior.

Impact:
- The original W5 integration regressions can return while the current test suite remains green.
- The report's statement "Add real service-level tests, remove false-positive ones" is not supported by the diff.

Required fix:
- Replace the direct-mock test with actual TodayService service-path coverage.
- Add CalendarService service-path coverage.
- Add DB-level cache identity coverage.
- Do not count pure `DayScoringRuntimeService` tests or direct mock calls as W5 integration coverage.

### P1 — Verification evidence is still not acceptable for final W5 acceptance

Evidence:
- The tmux run again used `pytest ... 2>&1 | tail -5` without `set -o pipefail`.
- The report says full API suite has `735 passed, 5 skipped (1 pre-existing...)`; that is a failed full-suite gate, not a passing full-suite gate.

Impact:
- I cannot accept W5 based on the report even if the code is correct.

Required fix:
- Run final required commands without `tail`.
- If the oracle test still fails, report it explicitly as a known failed gate with exact test name and reason, not as a green full-suite result.

## Notes

- The code direction for cache identity is now close: read keys use `expected_cache_identity()`, write keys use actual `activation_layer` runtime fields, and Calendar semantic identity now checks `activation_layer_version`.
- The remaining blocker is proof: tests must exercise the service paths that previously regressed.

