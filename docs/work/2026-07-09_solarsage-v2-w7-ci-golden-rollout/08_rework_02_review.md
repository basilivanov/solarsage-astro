# W7 Rework 02 Architect Review

Status: REWORK REQUIRED
Reviewed range: c7f2638..f78ceb2
Date: 2026-07-09

## Findings

### P0 - Required `python3` gates fail outside API venv

Evidence:

```bash
python3 scripts/check_v2_performance_budgets.py
```

Fails with:

```text
ModuleNotFoundError: No module named 'pydantic.alias_generators'
```

```bash
python3 scripts/check_solarsage_v2_rollout_gates.py
```

Fails because it invokes the performance checker through the same incompatible interpreter.

Impact:

- W7 CI/rollout gate is red under the exact command shape required by the TZ.
- The Rework 02 report claims these commands pass, so the reported verification cannot be accepted.
- The gate is not portable for a fresh operator running from repo root with `python3`.

Required fix:

- Make `python3 scripts/check_v2_performance_budgets.py` pass from repo root on this server.
- Preferred implementation: at script startup, detect `apps/api/.venv/bin/python`; if present and current `sys.executable` is not that interpreter, re-exec into it with a recursion guard and preserve CLI args.
- If `.venv` does not exist, continue with the current interpreter so CI still works after dependency installation.
- Make `python3 scripts/check_solarsage_v2_rollout_gates.py` pass from repo root as well. It may rely on the performance script self-reexec or resolve the same interpreter explicitly.
- Keep the change narrow. Do not refactor scoring, fixtures, frontend, or rollout semantics.

## Verified Passes

Privacy scans are clean:

```bash
rg -n '/opt/solarsage-astro|833478509|basil_ivanov|1980-10-30|Мончегорск|67\.9394|32\.8144|43\.59699|39\.72477' apps/api/tests/fixtures/golden apps/api/tests/test_golden_basil_2026_07_08.py scripts/check_audit_golden.py scripts/check_v2_performance_budgets.py scripts/check_solarsage_v2_rollout_gates.py
rg -n 'birth_local_date|progressed_utc_iso|raw_natal_context|raw_activations|source_longitude|target_longitude' apps/api/tests/fixtures/golden
```

Whitespace checks are clean:

```bash
git show --check HEAD
git diff 2f9173fbe9a9e20e97891e9789db6de57a2afaef..HEAD --check
```
