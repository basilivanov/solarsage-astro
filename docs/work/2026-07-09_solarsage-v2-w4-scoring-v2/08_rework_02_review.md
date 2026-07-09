# W4 Rework 02 Architect Review — Rework Required

Status: REWORK REQUIRED
Branch: `main`
Reviewed commits: `d374cc4` implementation, `3c27b80` report finalization
Reviewed report: `docs/work/2026-07-09_solarsage-v2-w4-scoring-v2/07_rework_02_report.md`

## Fresh Verification Performed

Targeted V2 tests:

```bash
cd apps/api && source .venv/bin/activate && python -m pytest \
  tests/test_scoring_v2_contracts.py \
  tests/test_scoring_v2_convergence.py \
  tests/test_scoring_v2_antidominance.py \
  tests/test_scoring_v2_thresholds.py \
  tests/test_scoring_v2_family_dedup.py \
  tests/test_scoring_v2_breakdown_contract.py \
  tests/test_basil_2026_07_08_v2_golden.py -q
```

Observed:

```text
22 passed in 0.47s
```

Activation/meta tests:

```bash
cd apps/api && source .venv/bin/activate && python -m pytest \
  tests/test_activation_layer_contract.py \
  tests/test_activation_layer_transits.py \
  tests/test_activation_layer_profections.py \
  tests/test_activation_layer_firdar.py \
  tests/test_activation_layer_returns.py \
  tests/test_activation_layer_progressions.py \
  tests/test_activation_layer_eclipse.py \
  tests/test_today_meta_versions.py -q
```

Observed:

```text
38 passed in 0.57s
```

Strict canon missing-key checks:

```text
strict canon missing-key checks passed
```

Artifact equality after running with the API venv interpreter:

```text
result_diff_rc=0
diff_diff_rc=0
```

## Finding

### P1 — documented W4 audit command fails from a clean repo-root shell

File: `scripts/audit_scoring_v2.py`
Docs: `docs/work/2026-07-09_solarsage-v2-w4-scoring-v2/00_TZ.md:491`
Docs: `docs/work/2026-07-09_solarsage-v2-w4-scoring-v2/06_rework_02_TZ.md:116`

The W4 TZ and follow-up rework TZ both document this command:

```bash
python3 scripts/audit_scoring_v2.py \
  --signals artifacts/audit/2026-07-08/04_day_scored_signals_after_filter.csv \
  --activation-layer artifacts/audit/2026-07-08/21_sidecar_activation_layer_w3_5_progressions.json \
  --out-result artifacts/audit/2026-07-08/22_scoring_v2_result.json \
  --out-diff artifacts/audit/2026-07-08/23_scoring_v2_diff.json
```

Fresh execution from repo root fails:

```text
Traceback (most recent call last):
  File "/opt/solarsage-astro/scripts/audit_scoring_v2.py", line 146, in <module>
    main()
  File "/opt/solarsage-astro/scripts/audit_scoring_v2.py", line 79, in main
    from app.schemas.normalization import AstroSignal
ModuleNotFoundError: No module named 'app'
```

Environment proof:

```text
/usr/bin/python3
pydantic 1.10.14
ModuleNotFoundError No module named 'pydantic.alias_generators'
```

The same script works when explicitly run under the API venv:

```bash
apps/api/.venv/bin/python scripts/audit_scoring_v2.py ...
```

Observed:

```text
Wrote V2 result to /tmp/22_scoring_v2_result_check.json
Wrote V1/V2 diff to /tmp/23_scoring_v2_diff_check.json
  V1 status: supportive
  V2 status: steady
  Spheres: 9
```

This is not a scoring algorithm defect, but it is still a W4 acceptance blocker because the audit command published in the work docs is not runnable as written. The script should either satisfy the documented command or the documented command should be changed everywhere before acceptance. Since W4 already published `python3 scripts/audit_scoring_v2.py`, prefer making that command work.

## Accepted Parts

These Rework 02 changes look aligned pending the remaining audit CLI fix:

- both W4 artifacts are committed and match fresh venv-generated output;
- tracked working tree is clean after callback;
- strict canon missing-key behavior is covered by tests and manual check;
- `_ACTIVE_ACTIVATIONS` dead state is removed;
- fallback pattern search has no unwanted W4 runtime matches;
- runtime `/day` remains V1.

## Required Next Step

Implement `docs/work/2026-07-09_solarsage-v2-w4-scoring-v2/09_rework_03_TZ.md`.
