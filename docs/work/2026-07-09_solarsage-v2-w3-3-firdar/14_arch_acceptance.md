# Architect Acceptance — W3.3 Firdar Activations

Status: ACCEPTED
Branch: main
Push/deploy: not attempted

## Accepted Commits

- f94204a docs(w3.3): request firdar activations
- 15f9b1c W3.3: firdar activations (firdar_major + firdar_minor)
- e20e4d6 docs(w3.3): finalize report with sha 15f9b1c
- 70c24a4 docs(w3.3): request rework 01 for firdar
- 568cbdf W3.3 Rework 01: fix boundaries, contracts, and test coverage
- 30b11c6 docs(w3.3): finalize rework 01 report with sha 568cbdf
- de7fb43 docs(w3.3): request rework 02 for firdar
- 11574e6 W3.3 Rework 02: fixture/GRACE/test-discipline fixes
- fbf965d docs(w3.3): finalize rework 02 report with sha 11574e6
- 44d1c0e docs(w3.3): request rework 03 for firdar
- cf3c2df W3.3 Rework 03: close test/contract gaps
- e544459 docs(w3.3): finalize rework 03 report with sha cf3c2df
- c41c8af docs(w3.3): request rework 04 for firdar
- f27d394 W3.3 Rework 04: validate caller-supplied canon, cleanup contracts
- 1a36adf docs(w3.3): finalize rework 04 report with sha f27d394

## Scope Accepted

W3.3 adds Firdar activation-layer support only:

- `firdar_major`
- `firdar_minor`

It does not wire the sidecar activation layer into `TodayService`, does not add scoring v2, and does not add future techniques.

## Verification Evidence

```text
cd apps/solarsage && venv/bin/python -m pytest tests/test_firdar.py tests/test_activation_layer_endpoint.py tests/test_activation_transits.py tests/test_activation_schema.py tests/test_profections.py -q
72 passed, 1 warning
```

```text
cd apps/api && source .venv/bin/activate && python -m pytest tests/test_activation_layer_firdar.py tests/test_activation_layer_profections.py tests/test_activation_layer_transits.py tests/test_activation_layer_contract.py tests/test_today_meta_versions.py -q
23 passed
```

```text
cd apps/solarsage && venv/bin/python -m pytest tests/ -q
93 passed, 1 warning
```

```text
cd apps/api && source .venv/bin/activate && python -m pytest tests/ -q
690 passed, 5 skipped, 1 warning
```

Malformed caller-supplied canon now fails through `calculate_firdar(canon=bad)`:

```text
minor0 ValueError minor_divisions must be > 0, got 0
day_sum ValueError day_sequence years sum 10.0 != cycle_years 75
night_sum ValueError night_sequence years sum 9.0 != cycle_years 75
node_len ValueError node_minor_sequence length 3 != minor_divisions 7
```

Audit regeneration:

```text
python3 scripts/audit_sidecar_activation.py ... --out artifacts/audit/2026-07-08/19_sidecar_activation_layer_w3_3_firdar.json
Activations: 117
Warnings: []
git diff --exit-code -- artifacts/audit/2026-07-08/19_sidecar_activation_layer_w3_3_firdar.json
no diff
```

Hashseed determinism:

```text
a1b94bbb9838b78e96fd12e14c9bb91f14ad71d1505c1c9f2f3953369fded296
a1b94bbb9838b78e96fd12e14c9bb91f14ad71d1505c1c9f2f3953369fded296
a1b94bbb9838b78e96fd12e14c9bb91f14ad71d1505c1c9f2f3953369fded296
```

Artifact assertions:

```text
_audit_meta.wave == W3.3
len(activations) == 117
firdar_major__PERIOD_LORD__SUN strength == 0.65
firdar_minor__SUBPERIOD_LORD__SATURN strength == 0.40
major.debug.age_years == 45.68767123
```

TodayService remains unwired:

```text
apps/api/app/services/today_service.py:245 sidecar_activation_layer=None
```

Static checks:

```text
rg 'strength keys|unknown sign|import math|load_count <=' apps/solarsage/solarsage/services/firdar.py apps/solarsage/tests/test_firdar.py
no matches

git diff 2f9173fbe9a9e20e97891e9789db6de57a2afaef..HEAD --check
clean

git show --check HEAD
clean
```

## Notes

The local worktree still has pre-existing untracked files outside W3.3:

```text
.grace/
docs/superpowers/plans/2026-07-05-fix-day-route-auth-build.md
grace.db
skills/
```

They were not part of this acceptance.
