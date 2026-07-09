# W7 Rework 03 Report

## Goal
Make the W7 gate scripts interpreter-portable so that running them directly via `python3` from repo root uses the correct API virtual environment.

## Changed Files
- `scripts/check_audit_golden.py` (added bootstrap re-exec block to dynamically load the venv python interpreter if it exists)
- `scripts/check_v2_performance_budgets.py` (added bootstrap re-exec block to dynamically load the venv python interpreter if it exists)
- `scripts/check_solarsage_v2_rollout_gates.py` (added bootstrap re-exec block to dynamically load the venv python interpreter if it exists)

## Interpreter Portability Implementation
Added a lightweight bootstrap re-exec block at the top of each script before any API module imports.
- It detects the presence of the `apps/api/.venv/bin/python` interpreter.
- If the virtual environment python interpreter exists and the current interpreter (`sys.executable`) is not that path, the script re-executes itself through it.
- Uses a recursion guard environment variable (`SOLARSAGE_*_RE_EXEC`) to prevent infinite re-exec loops.
- Preserves all CLI arguments using `sys.argv`.
- If the virtual environment does not exist (e.g. in GitHub CI after dependencies are installed in the global environment), it continues running on the current `sys.executable`.

## Verification Outputs

### Performance Budgets Gate
```text
python3 scripts/check_v2_performance_budgets.py

=== Running V2 Performance Budgets Check ===
mode: fixture
Scoring V2 p95: 0.14 ms
Semantic V2 p95: 0.04 ms
{"ts": "2026-07-09T10:34:08.265719+00:00Z", "level": "info", "event": "system.performance_budgets_passed", "msg": "Performance budget check passed", "service": "performance-tool", "slice": "W7", "module": "M-V2-PERFORMANCE-BUDGETS-CHECK", "block": "PERFORMANCE_RUN"}
Performance budget check: PASSED
```

### Rollout Gates Validation
```text
python3 scripts/check_solarsage_v2_rollout_gates.py

=== Running SolarSage V2 Rollout Gates Validation ===
Doc checked: docs/work/2026-07-08_solarsage-v2-w0-audit-baseline/29_arch_acceptance.md (exists)
Doc checked: docs/work/2026-07-09_solarsage-v2-w1-contracts-canon/05_arch_acceptance.md (exists)
Doc checked: docs/work/2026-07-09_solarsage-v2-w2-activation-layer/11_arch_acceptance.md (exists)
Doc checked: docs/work/2026-07-09_solarsage-v2-w3-1-transit-activations/08_arch_acceptance.md (exists)
Doc checked: docs/work/2026-07-09_solarsage-v2-w3-2-profections/05_arch_acceptance.md (exists)
Doc checked: docs/work/2026-07-09_solarsage-v2-w3-3-firdar/14_arch_acceptance.md (exists)
Doc checked: docs/work/2026-07-09_solarsage-v2-w3-4-returns/08_arch_acceptance.md (exists)
Doc checked: docs/work/2026-07-09_solarsage-v2-w3-5-progressions/08_arch_acceptance.md (exists)
Doc checked: docs/work/2026-07-09_solarsage-v2-w3-6-eclipse-window/05_arch_acceptance.md (exists)
Doc checked: docs/work/2026-07-09_solarsage-v2-w4-scoring-v2/17_arch_acceptance.md (exists)
Doc checked: docs/work/2026-07-09_solarsage-v2-w5-api-cache-dual-run/23_rework_07_review.md (exists)
Doc checked: docs/work/2026-07-09_solarsage-v2-w6-semantic-frontend-v2/08_arch_accept.md (exists)
Fixture checked: basil_2026_07_08_v1.json (size: 1.38 KB, privacy OK)
Fixture checked: basil_2026_07_08_v2.json (size: 53.99 KB, privacy OK)
Fixture checked: mercury_convergence_case_v2.json (size: 3.12 KB, privacy OK)
Fixture checked: antidominance_case_v2.json (size: 1.88 KB, privacy OK)
Total golden fixtures size: 60.36 KB
Status flip record verified: supportive -> steady (explained)
Frontend test checked: __tests__/contracts/today.test.ts (exists)
Frontend test checked: __tests__/lib/adapt-payload.test.ts (exists)
Rollback procedure documentation checked: OK
Performance budget script checked: OK (passed)
{"ts": "2026-07-09T10:34:08.725940+00:00Z", "level": "info", "event": "system.rollout_gates_passed", "msg": "Rollout gates validation passed", "service": "rollout-tool", "slice": "W7", "module": "M-V2-ROLLOUT-GATES-VALIDATOR", "block": "VALIDATION_RUN"}

Rollout gates validation: PASSED
```

### Deterministic Audit Golden Gate
```text
python3 scripts/check_audit_golden.py

=== Running Audit Golden Snapshots Gate ===
{"ts": "2026-07-09T10:30:35.331399+00:00Z", "level": "info", "event": "system.audit_golden_passed", "msg": "Audit golden snapshots gate passed", "service": "audit-tool", "slice": "W7", "module": "M-AUDIT-GOLDEN-GATE", "block": "AUDIT_RUN"}
Audit golden snapshots gate: PASSED
```

### Pytest Suite
```text
cd apps/api && source .venv/bin/activate && python -m pytest tests/test_golden_basil_2026_07_08.py tests/test_golden_v2_convergence.py tests/test_v2_performance_budgets.py -q

....                                                                     [100%]
4 passed in 0.38s
```

### Privacy scans
```text
rg -n '/opt/solarsage-astro|833478509|basil_ivanov|1980-10-30|Мончегорск|67\.9394|32\.8144|43\.59699|39\.72477' apps/api/tests/fixtures/golden apps/api/tests/test_golden_basil_2026_07_08.py scripts/check_audit_golden.py scripts/check_v2_performance_budgets.py scripts/check_solarsage_v2_rollout_gates.py
(No output, completely clean)

rg -n 'birth_local_date|progressed_utc_iso|raw_natal_context|raw_activations|source_longitude|target_longitude' apps/api/tests/fixtures/golden
(No output, completely clean)
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
Commit: bee7319
