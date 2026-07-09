# W3.2 Architect Acceptance — Profection Activations

Status: ACCEPTED
Date: 2026-07-09
Branch: main
Push: NOT_ATTEMPTED

## Accepted Commits

- `1b7674a` — W3.2 initial profection activations
- `fb87f22` — W3.2 initial report traceability
- `305c3ad` — W3.2 Rework 01 monthly drift/debug/audit/sign fallback fixes
- `255e156` — W3.2 Rework 01 report SHA correction

## Review Result

W3.2 is accepted after Rework 01.

Independent review verified:

- annual profection emits house + lord activations for Basil `2026-07-08`;
- monthly profection emits house + lord activations for Basil `2026-07-08`;
- monthly profection no longer drifts across clamped month anniversaries;
- all four Basil profection activations include `house_cusp_longitude`;
- unknown signs now raise `ValueError` instead of falling back to Saturn;
- audit metadata is accurate for the W3.2 command;
- unsupported future W3 techniques are not emitted in the W3.2 artifact;
- `TodayService` remains deliberately unwired from sidecar activation layer for this wave.

## Fresh Verification

Commands run by architect on current worktree:

```bash
cd apps/solarsage && venv/bin/python -m pytest tests/test_profections.py tests/test_activation_layer_endpoint.py tests/test_activation_transits.py tests/test_activation_schema.py -q
```

Result: `31 passed, 1 warning`.

```bash
cd apps/solarsage && venv/bin/python -m pytest tests/ -q
```

Result: `52 passed, 1 warning`.

```bash
cd apps/api && source .venv/bin/activate && python -m pytest tests/test_activation_layer_profections.py tests/test_activation_layer_transits.py tests/test_activation_layer_contract.py tests/test_today_meta_versions.py -q
```

Result: `19 passed`.

```bash
cd apps/api && source .venv/bin/activate && python -m pytest tests/ -q
```

Result: `686 passed, 5 skipped, 1 warning`.

```bash
python3 scripts/audit_sidecar_activation.py \
  --user-id eb3876be-e1b4-43d6-b887-1f8554e33150 \
  --date 2026-07-08 \
  --techniques transit_to_natal,transit_to_angle,transit_planet_in_house,transit_to_lot,annual_profection,monthly_profection \
  --out artifacts/audit/2026-07-08/18_sidecar_activation_layer_w3_2_profections.json
git diff --exit-code -- artifacts/audit/2026-07-08/18_sidecar_activation_layer_w3_2_profections.json
```

Result: artifact regenerated with `115` activations and no diff.

```bash
for i in 1 2 3; do
  PYTHONHASHSEED=random python3 scripts/audit_sidecar_activation.py \
    --user-id eb3876be-e1b4-43d6-b887-1f8554e33150 \
    --date 2026-07-08 \
    --techniques transit_to_natal,transit_to_angle,transit_planet_in_house,transit_to_lot,annual_profection,monthly_profection \
    --out /tmp/sidecar_activation_w3_2_$i.json
  sha256sum /tmp/sidecar_activation_w3_2_$i.json
done
cmp -s /tmp/sidecar_activation_w3_2_1.json /tmp/sidecar_activation_w3_2_2.json
cmp -s /tmp/sidecar_activation_w3_2_1.json /tmp/sidecar_activation_w3_2_3.json
```

Result: all three hashes equal:

```text
a7a4dff2bd74cb39661d7458d7cb3bf52403f70700a8cab8a7445dbbce0a158b
```

Additional checks:

- profection ids/evidence found in `artifacts/audit/2026-07-08/18_sidecar_activation_layer_w3_2_profections.json`;
- no `firdar_major`, `firdar_minor`, `solar_return`, `lunar_return`, `secondary_progression`, `solar_arc`, `eclipse_window` emitted in W3.2 artifact;
- `apps/api/app/services/today_service.py` still contains `sidecar_activation_layer=None`;
- `git diff 2f9173fbe9a9e20e97891e9789db6de57a2afaef..HEAD --check` clean;
- `git show --check HEAD` clean.

## Notes For Next Wave

W3.3 should add `firdar_major` and `firdar_minor` as the next isolated technique family. It must not enable scoring v2 or wire `TodayService` to sidecar activation layer yet.
