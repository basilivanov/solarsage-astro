# Architect Acceptance: Wave W2 Activation Layer

Status: ACCEPTED

Accepted commits:

- `aff70066da944e4e8fa0af2295ece23e748f7d92` — W2 implementation
- `d9c58f1` — Rework 01
- `3921fef` — Rework 02
- `679647dc71a60953f8ba871ee788056d5f28f197` — Rework 03

## Acceptance Summary

W2 is accepted.

The activation-layer infrastructure now exists and is wired into the fresh full `/day` pipeline without enabling scoring v2:

- API `ActivationLayerService` builds deterministic W2 minimal activations from day-scored transit signals;
- W2 activations include `transit_to_natal` and `transit_planet_in_house`;
- non-transit/static natal background signals are explicitly excluded;
- `TodayService` builds the layer after `day_signals = filter_day_scored_signals(signals)`;
- `ScoringService.score_day(...)` still receives day signals only;
- `SemanticService.build_why_contexts(...)` receives the real `ActivationLayer`;
- full fresh payload meta sets `activation_layer_version == "al-1.0"`;
- locked preview payload keeps `activation_layer_version is None`;
- runtime scoring remains v1 and does not claim `ss-scoring-2.0`;
- sidecar `/v1/activation-layer` exists as contract-only endpoint and is not a hard TodayService dependency yet;
- audit artifact `artifacts/audit/2026-07-08/16_activation_layer.json` is deterministic and contains Basil activation evidence.

## Architect Verification

Fresh commands run by architect after Rework 03:

```bash
cd apps/api && source .venv/bin/activate && python -m pytest tests/test_today_meta_versions.py tests/test_activation_layer_contract.py tests/test_day_endpoints.py -q
```

Result: `19 passed, 1 warning`.

```bash
cd apps/api && source .venv/bin/activate && python -m pytest tests/ -q
```

Result: `678 passed, 5 skipped, 1 warning`.

```bash
cd apps/solarsage && venv/bin/python -m pytest tests/ -q
```

Result: `28 passed, 1 warning`.

```bash
npx vitest run
```

Result: `85 passed test files, 902 passed tests`.

```bash
pnpm contracts:generate
git diff --exit-code -- packages/contracts/openapi.json packages/contracts/_generated.ts
```

Result: generated contracts are clean.

```bash
make audit-day USER_ID=eb3876be-e1b4-43d6-b887-1f8554e33150 DATE=2026-07-08
git diff --exit-code -- artifacts/audit/2026-07-08
```

Result: audit oracle passes and artifacts are deterministic.

```bash
rg -n 'inspect\.getsource' apps/api/tests/test_today_meta_versions.py || true
rg -n 'ss-scoring-2.0' apps/api/app/services/today_service.py artifacts/audit/2026-07-08/11_final_today_payload.json || true
rg -n 'activation_layer=None' apps/api/app/services/today_service.py || true
rg -n 'transit_planet_in_house|transit_to_natal|Transit Moon opposition natal Pluto|activation-layer.v1|al-1.0' artifacts/audit/2026-07-08/16_activation_layer.json
```

Result:

- no `inspect.getsource` remains in W2 TodayService tests;
- no `ss-scoring-2.0` in runtime TodayService or frozen final payload;
- the only `activation_layer=None` match is `sidecar_activation_layer=None`, the allowed W2 contract-only sidecar path;
- activation artifact contains `activation-layer.v1`, `al-1.0`, `transit_to_natal`, `transit_planet_in_house`, and `Transit Moon opposition natal Pluto`.

```bash
git diff 2f9173fbe9a9e20e97891e9789db6de57a2afaef..HEAD --check
git show --check HEAD
git status --short --branch
```

Result: whitespace checks are clean; only pre-existing unrelated untracked local files remain.

## Notes

`10_rework_03_report.md` contains stale Vitest text from the agent run and leaves the commit placeholder unfilled. Architect verification supersedes those report fields: fresh `npx vitest run` passed with `902` tests, and the accepted Rework 03 commit is `679647dc71a60953f8ba871ee788056d5f28f197`.

## Next

Proceed to W3.1: implement sidecar-owned transit activation extraction so `/v1/activation-layer` can return real transit activations instead of the W2 contract-only empty layer.
