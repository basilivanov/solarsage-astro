# W3.6 Architect Acceptance — Eclipse Window

Status: ACCEPTED
Branch: `main`
Accepted implementation commit: `2346d1c`
Report finalization commit: `feb6d17`
Review docs: `02_arch_review.md`, `03_rework_01_TZ.md`

## Scope Accepted

W3.6 `eclipse_window` activation support is accepted for the sidecar activation layer.

Accepted behavior:
- sidecar computes solar/lunar eclipse candidates via Swiss Ephemeris;
- candidates are filtered by configured `days_before` / `days_after`;
- runtime activation build uses only the nearest candidate after filtering;
- natal planets, natal angles, and lots are activated only on conjunction within `orb_to_natal`;
- if the nearest candidate has no natal/angle/lot hits, no farther eclipse is activated;
- `TodayService` remains unwired with `sidecar_activation_layer=None`;
- no scoring v2, convergence, semantic/frontend, push, or deploy was included.

## Independent Verification

Fresh architect-run verification after `feb6d17`:

```text
cd apps/solarsage && venv/bin/python -m pytest \
  tests/test_eclipse_window.py \
  tests/test_solar_arc.py \
  tests/test_secondary_progressions.py \
  tests/test_activation_layer_endpoint.py \
  tests/test_firdar.py \
  tests/test_profections.py \
  tests/test_activation_transits.py \
  tests/test_activation_schema.py -q
```

Result:

```text
114 passed, 1 warning
```

```text
cd apps/solarsage && venv/bin/python -m pytest tests/ -q
```

Result:

```text
159 passed, 1 warning
```

```text
cd apps/api && source .venv/bin/activate && python -m pytest \
  tests/test_activation_layer_eclipse.py \
  tests/test_activation_layer_progressions.py \
  tests/test_activation_layer_returns.py \
  tests/test_activation_layer_firdar.py \
  tests/test_activation_layer_profections.py \
  tests/test_activation_layer_transits.py \
  tests/test_activation_layer_contract.py \
  tests/test_today_meta_versions.py -q
```

Result:

```text
38 passed
```

```text
cd apps/api && source .venv/bin/activate && python -m pytest tests/ -q
```

Result:

```text
705 passed, 5 skipped, 1 warning
```

## Regression Evidence

Manual regression for Basil `2026-03-03`:

```text
candidates:
lunar total 2026_03_03 0.1067
solar annular 2026_02_17 -13.8667
act_count 0
nearest-no-hit eclipse regression passed
```

This proves the original false positive is fixed: the farther solar eclipse is not activated when the nearest lunar eclipse has no natal/angle/lot hits.

## Artifact Evidence

Regenerated:

```text
artifacts/audit/2026-08-12/22_sidecar_activation_layer_w3_6_eclipse.json
```

Result:

```text
Activations: 151
eclipse_window activations: 1
```

Accepted eclipse activation:

```text
eclipse_window__SOLAR__TOTAL__2026_08_12__CONJUNCTION__NATAL_ANGLE_IC
kind=solar
date=2026_08_12
orb=2.0641
strength=0.1671
```

`git diff --exit-code -- artifacts/audit/2026-08-12/22_sidecar_activation_layer_w3_6_eclipse.json` was clean after regeneration.

Hashseed determinism:

```text
430277990c6b069423c9830738b6d8c0b3cadf6900ca1cab69163bf74e6943b3
430277990c6b069423c9830738b6d8c0b3cadf6900ca1cab69163bf74e6943b3
430277990c6b069423c9830738b6d8c0b3cadf6900ca1cab69163bf74e6943b3
```

Artifact assertions verified:
- `_audit_meta.wave == "W3.6"`;
- at least one `eclipse_window` activation exists;
- family/frame/aspect/phase/polarity are canonical;
- all required eclipse debug fields are present;
- strength equals `base_strength * orb_factor * window_factor`, rounded to 4 decimals;
- date and orb constraints hold.

## Wiring And Cleanliness

TodayService sidecar wiring remains off:

```text
apps/api/app/services/today_service.py:245:
sidecar_activation_layer=None
```

Whitespace/check gates:

```text
git diff 2f9173fbe9a9e20e97891e9789db6de57a2afaef..HEAD --check
git show --check HEAD
```

Both completed cleanly.

Current tracked worktree is clean. Existing untracked local files are unrelated and were not touched:

```text
.grace/
docs/superpowers/plans/2026-07-05-fix-day-route-auth-build.md
grace.db
skills/
```

## Notes

The sort helper still comments its final tie-break as solar-before-lunar. Because `eclipse_jd` precedes that final tie-break and simultaneous solar/lunar eclipse candidates are not a physically expected case, this does not affect accepted behavior. If this area is touched again, prefer making the comment/key wording match the original TZ exactly: `(abs_delta, eclipse_jd, eclipse_kind)`.

## Decision

W3.6 is accepted. Next wave can start from W4 Scoring V2 in `docs/15_SolarSage_v2_activation_audit_TZ.md`.
