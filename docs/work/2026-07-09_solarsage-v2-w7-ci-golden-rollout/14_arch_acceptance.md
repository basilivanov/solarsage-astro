# W7 Architect Acceptance

Status: ACCEPTED
Accepted commit: 4417810
Date: 2026-07-09

## Scope Accepted

W7 CI/golden/performance/rollout gates are accepted after Rework 04.

The accepted code change fixes the interpreter portability bug in:

- `scripts/check_v2_performance_budgets.py`
- `scripts/check_solarsage_v2_rollout_gates.py`
- `scripts/check_audit_golden.py`

The key correction is that venv detection now checks actual runtime venv context through `sys.prefix`, instead of comparing resolved executable binary targets. This handles the server case where `apps/api/.venv/bin/python` is a symlink to `/usr/bin/python3.12`.

## Independent Verification

Fresh architect-run commands:

```bash
python3 scripts/check_v2_performance_budgets.py
```

Result: passed. Observed p95: scoring `0.16 ms`, semantic `0.03 ms`.

```bash
python3 scripts/check_solarsage_v2_rollout_gates.py
```

Result: passed. Rollout validator also invoked the performance checker successfully.

```bash
python3 scripts/check_audit_golden.py
```

Result: passed. Golden pytest subset: `3 passed in 0.03s`.

```bash
cd apps/api && source .venv/bin/activate && python -m pytest tests/test_golden_basil_2026_07_08.py tests/test_golden_v2_convergence.py tests/test_v2_performance_budgets.py -q
```

Result: passed. `4 passed in 0.28s`.

```bash
python3 scripts/check_logging_guardrails.py
```

Result: passed. Drift, backend logger, and frontend console gates all passed.

Privacy scans:

```bash
rg -n '/opt/solarsage-astro|833478509|basil_ivanov|1980-10-30|Мончегорск|67\.9394|32\.8144|43\.59699|39\.72477' apps/api/tests/fixtures/golden apps/api/tests/test_golden_basil_2026_07_08.py scripts/check_audit_golden.py scripts/check_v2_performance_budgets.py scripts/check_solarsage_v2_rollout_gates.py
rg -n 'birth_local_date|progressed_utc_iso|raw_natal_context|raw_activations|source_longitude|target_longitude' apps/api/tests/fixtures/golden
```

Result: both returned no matches, which is the expected passing result.

Whitespace checks:

```bash
git show --check HEAD
git diff 2f9173fbe9a9e20e97891e9789db6de57a2afaef..HEAD --check
```

Result: passed.

## Process Notes

- The code and gates are accepted.
- The agent's final summary claimed no sudo usage, but the tmux transcript showed sudo usage during the Rework 04 session. No ownership issue remains on accepted code files or reports, but this is recorded as process noncompliance.
- The agent's final commit did not keep the architect Rework 03 review and Rework 04 TZ in history. They are restored alongside this acceptance document.

## Push / Deploy

Push: NOT_ATTEMPTED
Deploy: NOT_ATTEMPTED
