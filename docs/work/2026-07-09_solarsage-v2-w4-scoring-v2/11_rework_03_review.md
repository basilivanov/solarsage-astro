# W4 Rework 03 Architect Review — Rework Required

Status: REWORK REQUIRED
Branch: `main`
Reviewed commits: `97d7e14` implementation, `bd1481f` report finalization
Reviewed report: `docs/work/2026-07-09_solarsage-v2-w4-scoring-v2/10_rework_03_report.md`

## Fresh Verification Performed

Documented clean repo-root command now exits 0:

```bash
python3 scripts/audit_scoring_v2.py \
  --signals artifacts/audit/2026-07-08/04_day_scored_signals_after_filter.csv \
  --activation-layer artifacts/audit/2026-07-08/21_sidecar_activation_layer_w3_5_progressions.json \
  --out-result artifacts/audit/2026-07-08/22_scoring_v2_result.json \
  --out-diff artifacts/audit/2026-07-08/23_scoring_v2_diff.json
```

Observed:

```text
Wrote V2 result to artifacts/audit/2026-07-08/22_scoring_v2_result.json
Wrote V1/V2 diff to artifacts/audit/2026-07-08/23_scoring_v2_diff.json
  V1 status: supportive
  V2 status: steady
  Spheres: 9
```

Tracked working tree stayed clean after that command.

## Finding

### P2 — bootstrap can false-positive on `import app` and skip needed venv re-exec

File: `scripts/audit_scoring_v2.py:42-75`

Rework 03 required detecting whether the current interpreter can import the API runtime correctly. The current implementation checks only:

```python
import app
```

This is insufficient because `apps/api/app/__init__.py` is light and does not prove the runtime dependencies are correct.

Fresh proof:

```bash
PYTHONPATH=/opt/solarsage-astro/apps/api python3 - <<'PY'
try:
    import app
    print("import app ok")
except Exception as e:
    print("import app failed", type(e).__name__, e)
try:
    from app.schemas.normalization import AstroSignal
    print("import AstroSignal ok")
except Exception as e:
    print("import AstroSignal failed", type(e).__name__, e)
PY
```

Observed:

```text
import app ok
import AstroSignal failed ModuleNotFoundError No module named 'pydantic.alias_generators'
```

Then the script fails under exactly that environment because `_ensure_api_runtime()` returns too early:

```bash
PYTHONPATH=/opt/solarsage-astro/apps/api python3 scripts/audit_scoring_v2.py ...
```

Observed:

```text
ModuleNotFoundError: No module named 'pydantic.alias_generators'
```

Expected: the script should recognize that the API runtime is not valid under system Python and re-exec into `apps/api/.venv/bin/python`.

## Accepted Parts

These parts are aligned pending the runtime-detection fix:

- clean repo-root documented command works when `PYTHONPATH` is not pre-set;
- re-exec target is the canonical API venv;
- artifacts remain deterministic and tracked tree stays clean;
- no scoring/TodayService/frontend scope creep.

## Required Next Step

Implement `docs/work/2026-07-09_solarsage-v2-w4-scoring-v2/12_rework_04_TZ.md`.
