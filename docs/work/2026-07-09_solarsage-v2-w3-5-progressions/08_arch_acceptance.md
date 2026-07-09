# Architect Acceptance — W3.5 Progressions

Status: ACCEPTED

Accepted through commit: `1333236 docs(w3.5): clean review whitespace`

## Accepted commits

- `c5fe1ca docs(w3.5): request progression activations`
- `887228c W3.5: solar arc + secondary progression activations`
- `6d8dfe8 docs(w3.5): finalize report with sha 887228c`
- `23c4511 docs(w3.5): request rework 01 for progressions`
- `e899a8a W3.5 Rework 01: progression contract closure`
- `8433753 docs(w3.5): finalize rework 01 report with sha e899a8a`
- `7da3fba docs(w3.5): request rework 02 for progressions`
- `44c7f7a W3.5 Rework 02: transition contract and artifact cleanup`
- `6c51c12 docs(w3.5): finalize rework 02 report with sha 44c7f7a`
- `1333236 docs(w3.5): clean review whitespace`

## Acceptance evidence

Fresh architect-run verification:

```text
cd apps/solarsage && venv/bin/python -m pytest tests/test_solar_arc.py tests/test_secondary_progressions.py tests/test_activation_layer_endpoint.py tests/test_firdar.py tests/test_profections.py tests/test_activation_transits.py tests/test_activation_schema.py -q
101 passed, 1 warning
```

```text
cd apps/solarsage && venv/bin/python -m pytest tests/ -q
146 passed, 1 warning
```

```text
cd apps/api && source .venv/bin/activate && python -m pytest tests/test_activation_layer_progressions.py tests/test_activation_layer_returns.py tests/test_activation_layer_firdar.py tests/test_activation_layer_profections.py tests/test_activation_layer_transits.py tests/test_activation_layer_contract.py tests/test_today_meta_versions.py -q
34 passed
```

```text
cd apps/api && source .venv/bin/activate && python -m pytest tests/ -q
701 passed, 5 skipped, 1 warning
```

Audit artifact regeneration:

```text
python3 scripts/audit_sidecar_activation.py --user-id eb3876be-e1b4-43d6-b887-1f8554e33150 --date 2026-07-08 --techniques transit_to_natal,transit_to_angle,transit_planet_in_house,transit_to_lot,annual_profection,monthly_profection,firdar_major,firdar_minor,solar_return,lunar_return,solar_arc,secondary_progression --out artifacts/audit/2026-07-08/21_sidecar_activation_layer_w3_5_progressions.json
Activations: 147
Warnings: ['return_location_fallback:birth_location:current_location_missing']
git diff --exit-code -- artifacts/audit/2026-07-08/21_sidecar_activation_layer_w3_5_progressions.json
exit 0
```

Hashseed determinism:

```text
02344897d6a5178e0fe8717db172f9beade8eccb38a80cb88fadb85a4a459610  /tmp/sidecar_activation_w3_5_rework_02_1.json
02344897d6a5178e0fe8717db172f9beade8eccb38a80cb88fadb85a4a459610  /tmp/sidecar_activation_w3_5_rework_02_2.json
02344897d6a5178e0fe8717db172f9beade8eccb38a80cb88fadb85a4a459610  /tmp/sidecar_activation_w3_5_rework_02_3.json
cmp 1=2 exit 0
cmp 1=3 exit 0
```

Artifact assertions:

```text
artifact ok 14
by_technique Counter({'transit_to_natal': 50, 'transit_to_lot': 35, 'transit_to_angle': 16, 'solar_arc': 11, 'transit_planet_in_house': 10, 'solar_return': 9, 'lunar_return': 7, 'secondary_progression': 3, 'annual_profection': 2, 'monthly_profection': 2, 'firdar_major': 1, 'firdar_minor': 1})
```

TodayService remains unwired:

```text
apps/api/app/services/today_service.py:245:            sidecar_activation_layer=None,  # Can be wired in W3+ when sidecar endpoint is ready
```

Final checks:

```text
git diff 2f9173fbe9a9e20e97891e9789db6de57a2afaef..HEAD --check
exit 0

git show --check HEAD
exit 0

git status --short --branch
## main...origin/main [ahead 100]
?? .grace/
?? docs/superpowers/plans/2026-07-05-fix-day-route-auth-build.md
?? grace.db
?? skills/
```

Only the listed untracked files remain, and they predate this acceptance.

## Accepted scope

W3.5 adds deterministic sidecar activation-layer support for:
- `solar_arc`
- `secondary_progression`

W3.5 does not wire `TodayService`, scoring v2, semantic/LLM/frontend, or deploy/push.
