# W7 Agent Report — CI, Golden Snapshots, Performance, Rollout Gates

## Goal
Implement Wave W7: establish deterministic golden fixtures for V1/V2 scoring and convergence/anti-dominance cases, integrate golden and audit tests into the CI workflow, implement performance budget validation and machine-checkable rollout gates.

## Changed/Created Files
- `.github/workflows/ci.yml` (added golden snapshots, performance budgets, rollout gates, and logging guardrails checks to CI)
- `Makefile` (added `audit-golden` target to run the golden tests suite)
- `apps/api/app/services/today_service.py` (fixed dict-shaped `top_signals` attribute lookup when V2 is active)
- `apps/api/app/services/today_interpretation_service.py` (fixed dict-shaped `top_signals` attribute lookup when V2 is active by normalizing them to `AstroSignal` objects)
- `apps/api/tests/fixtures/golden/basil_2026_07_08_v1.json` (created: Basil V1 TodayPayload golden fixture)
- `apps/api/tests/fixtures/golden/basil_2026_07_08_v2.json` (created: Basil V2 TodayPayload golden fixture)
- `apps/api/tests/fixtures/golden/mercury_convergence_case_v2.json` (created: synthetic V2 convergence golden fixture)
- `apps/api/tests/fixtures/golden/antidominance_case_v2.json` (created: synthetic V2 anti-dominance golden fixture)
- `apps/api/tests/test_golden_basil_2026_07_08.py` (created golden tests verifying Basil V1/V2 against snapshot within W7 tolerances)
- `apps/api/tests/test_golden_v2_convergence.py` (created golden tests verifying convergence technique families and anti-dominance caps)
- `apps/api/tests/test_v2_performance_budgets.py` (created unit test invoking performance budget script)
- `docs/rollout/solarsage_v2_rollout_gates.md` (created rollout gates checklist file)
- `scripts/check_audit_golden.py` (created audit golden test suite runner)
- `scripts/check_solarsage_v2_rollout_gates.py` (created rollout gates checklist validator)
- `scripts/check_v2_performance_budgets.py` (created local performance budget p95 checker)

## Golden Fixtures & Privacy Scrubbing Notes
- Generated Basil V1 and V2 golden fixtures using the real Basil 2026-07-08 raw transits and activations.
- Scrubbed all identity and profile data. The `TodayPayload` response does not contain usernames, birth dates, coordinates, or timezones, making it completely safe and public-CI ready.
- Created `mercury_convergence_case_v2.json` and `antidominance_case_v2.json` as synthetic contract-valid payloads to cleanly isolate technique convergence and anti-dominance cap features.
- Added metadata (`fixture_id`, `source`, `baseline_commit`, `tolerances`, `canon_versions`) inside the meta block of each fixture.

## CI Job / Step Summary
Added the following steps to the `.github/workflows/ci.yml` backend test job:
- **Run audit golden snapshots gate**: runs `pytest` on all golden tests using `check_audit_golden.py`.
- **Run performance budgets gate**: runs `check_v2_performance_budgets.py` to assert that local scoring/semantic p95 is under 50ms.
- **Run rollout gates validation**: runs `check_solarsage_v2_rollout_gates.py` to verify all rollout requirements are set to true.
- **Run logging guardrails check**: runs `check_logging_guardrails.py` to ensure log registries and PII gates are intact.
- The new steps require zero secrets and do not require running a live production DB or sidecar, making them highly stable and suitable for public CI.

## Performance Budget Implementation Summary
- `check_v2_performance_budgets.py` runs `ScoringV2Service().score_day` and `SemanticV2Service().build_v2_block` in a loop of 50 iterations, measuring p95 execution latency.
- It asserts p95 latency is under a strict 50ms threshold (local execution on Basil fixtures is ~3.09ms for scoring and ~0.37ms for semantic building).
- It emits an explicit `mode: fixture` as required by doc-15.

## Rollout Gate Checker Summary
- `check_solarsage_v2_rollout_gates.py` validates the markdown checklist in `docs/rollout/solarsage_v2_rollout_gates.md`.
- It matches checklist items (`- [x] gate_name: true`) and exits with code 0 only if all required rollout checklist items are present and set to true (ready).

## Verification Outputs

### Target Golden & Performance Tests
```text
cd apps/api && source .venv/bin/activate && python -m pytest \
  tests/test_golden_basil_2026_07_08.py \
  tests/test_golden_v2_convergence.py \
  tests/test_basil_2026_07_08_v2_golden.py \
  tests/test_v2_performance_budgets.py -q

.....                                                                    [100%]
5 passed in 1.62s
```

### Deterministic Audit Golden Gate
```text
make audit-golden

python3 scripts/check_audit_golden.py
...                                                                      [100%]
3 passed in 0.77s
=== Running Audit Golden Snapshots Gate ===
Audit golden snapshots gate: PASSED
```

### Performance Budgets Gate
```text
python3 scripts/check_v2_performance_budgets.py

=== Running V2 Performance Budgets Check ===
mode: fixture
Scoring V2 p95: 3.09 ms
Semantic V2 p95: 0.37 ms
Performance budget check: PASSED
```

### Rollout Gates Validation
```text
python3 scripts/check_solarsage_v2_rollout_gates.py

=== Running SolarSage V2 Rollout Gates Validation ===
Gate ready: W0_to_W6_accept_docs_exist
Gate ready: dual_run_evidence_exists
Gate ready: no_unexplained_status_flips
Gate ready: status_flips_have_activation_evidence
Gate ready: frontend_compatibility_tests_exist
Gate ready: rollback_procedure_documented
Gate ready: performance_budget_check_passes

Rollout gates validation: PASSED
```

### Logging Guardrails
```text
python3 scripts/check_logging_guardrails.py

=== Running Logging and Observability Guardrails ===
drift gate: OK
backend logger gate: OK
frontend console gate: OK

All guardrails PASSED.
```

### Whitespace and Git Checks
```text
git diff 2f9173fbe9a9e20e97891e9789db6de57a2afaef..HEAD --check
(No output, completely clean)

git show --check HEAD
(Exited with 0, completely clean)
```

## Push / Deploy Status
Push: NOT_ATTEMPTED

## Commit SHA
Commit: see callback/current HEAD
