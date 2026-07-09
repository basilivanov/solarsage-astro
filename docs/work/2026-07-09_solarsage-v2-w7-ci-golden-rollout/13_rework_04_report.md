# W7 Rework 04 Report — Fix Venv Symlink Detection

## Goal

Fix venv detection in the W7 gate bootstrap: do not compare resolved binary targets, detect actual venv context via `sys.prefix` so that `python3 scripts/check_v2_performance_budgets.py` and `python3 scripts/check_solarsage_v2_rollout_gates.py` pass from repo root even when `apps/api/.venv/bin/python` is a symlink to the system interpreter.

## Changed Files

- `scripts/check_v2_performance_budgets.py` (replaced venv bootstrap re-exec block)
- `scripts/check_solarsage_v2_rollout_gates.py` (replaced venv bootstrap re-exec block)
- `scripts/check_audit_golden.py` (replaced venv bootstrap re-exec block)

## Implementation Decision for Venv Detection

The old code compared resolved binary targets:

```python
real_sys = Path(sys.executable).resolve()
real_venv = venv_python.resolve()
if real_sys != real_venv:
    # re-exec
```

On this server `apps/api/.venv/bin/python` is a symlink to `/usr/bin/python3.12`, so both resolved to the same value, the re-exec was skipped, and the scripts imported with the wrong site-packages.

The new code uses `sys.prefix` to detect actual venv membership:

```python
api_venv = repo_root / "apps" / "api" / ".venv"
venv_python = api_venv / "bin" / "python"
current_prefix = Path(sys.prefix).resolve()
in_api_venv = current_prefix == api_venv.resolve()
if venv_python.exists() and not in_api_venv and not os.environ.get(RE_EXEC_GUARD):
    env = os.environ.copy()
    env[RE_EXEC_GUARD] = "1"
    os.execve(str(venv_python), [str(venv_python)] + sys.argv, env)
```

When running system `python3`, `sys.prefix` resolves to `/usr` (or similar system prefix), which does not match `apps/api/.venv`. When running inside the API venv, `sys.prefix` resolves to the venv root, so the re-exec is correctly skipped.

A recursion guard env var (`SOLARSAGE_*_RE_EXEC`) per script prevents infinite loops. If the venv path does not exist (CI without venv), the script continues with the current interpreter.

## Verification

### Why the old check was invalid

```bash
python3 - <<'PY'
import sys
from pathlib import Path
print(Path(sys.executable).resolve())
print(Path('apps/api/.venv/bin/python').resolve())
print(Path(sys.executable).resolve() == Path('apps/api/.venv/bin/python').resolve())
PY
```

Output:
```
/usr/bin/python3.12
/usr/bin/python3.12
True
```

Both resolve to the same binary target, confirming the old check incorrectly skipped re-exec.

### Performance Budgets Gate

```bash
python3 scripts/check_v2_performance_budgets.py
```

Output:
```
=== Running V2 Performance Budgets Check ===
mode: fixture
Scoring V2 p95: 0.18 ms
Semantic V2 p95: 0.03 ms
{"ts": "2026-07-09T11:11:19.314821+00:00Z", "level": "info", "event": "system.performance_budgets_passed", "msg": "Performance budget check passed", "service": "performance-tool", "slice": "W7", "module": "M-V2-PERFORMANCE-BUDGETS-CHECK", "block": "PERFORMANCE_RUN"}
Performance budget check: PASSED
```

### Rollout Gates Validation

```bash
python3 scripts/check_solarsage_v2_rollout_gates.py
```

Output:
```
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
{"ts": "2026-07-09T11:11:24.074328+00:00Z", "level": "info", "event": "system.rollout_gates_passed", "msg": "Rollout gates validation passed", "service": "rollout-tool", "slice": "W7", "module": "M-V2-ROLLOUT-GATES-VALIDATOR", "block": "VALIDATION_RUN"}

Rollout gates validation: PASSED
```

### Audit Golden Gate

```bash
python3 scripts/check_audit_golden.py
```

Output:
```
=== Running Audit Golden Snapshots Gate ===
{"ts": "2026-07-09T11:11:32.731012+00:00Z", "level": "info", "event": "system.audit_golden_passed", "msg": "Audit golden snapshots gate passed", "service": "audit-tool", "slice": "W7", "module": "M-AUDIT-GOLDEN-GATE", "block": "AUDIT_RUN"}
Audit golden snapshots gate: PASSED
```

### Pytest Suite

```bash
cd apps/api && source .venv/bin/activate && python -m pytest tests/test_golden_basil_2026_07_08.py tests/test_golden_v2_convergence.py tests/test_v2_performance_budgets.py -q
```

Output:
```
....                                                                     [100%]
4 passed in 0.39s
```

### Privacy Scans

```bash
rg -n '/opt/solarsage-astro|833478509|basil_ivanov|1980-10-30|Мончегорск|67\.9394|32\.8144|43\.59699|39\.72477' apps/api/tests/fixtures/golden apps/api/tests/test_golden_basil_2026_07_08.py scripts/check_audit_golden.py scripts/check_v2_performance_budgets.py scripts/check_solarsage_v2_rollout_gates.py
```
(No output — completely clean)

```bash
rg -n 'birth_local_date|progressed_utc_iso|raw_natal_context|raw_activations|source_longitude|target_longitude' apps/api/tests/fixtures/golden
```
(No output — completely clean)

### Logging Guardrails

```bash
python3 scripts/check_logging_guardrails.py
```

Output:
```
=== Running Logging and Observability Guardrails ===
drift gate: OK
backend logger gate: OK
frontend console gate: OK

All guardrails PASSED.
```

### Whitespace and Git Checks

```bash
git diff 2f9173fbe9a9e20e97891e9789db6de57a2afaef..HEAD --check
```
(No output, completely clean)

```bash
git show --check HEAD
```
(No output, completely clean)

## Commit SHA

Commit: `ab5ffe2`

## Push / Deploy Status

Push: NOT_ATTEMPTED
Deploy: NOT_ATTEMPTED

## Sudo Usage

No `sudo` was used during Rework 04.
