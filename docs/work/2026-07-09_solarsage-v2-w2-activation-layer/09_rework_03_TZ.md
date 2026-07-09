# Rework 03 TZ: Make W2 Behavioral Test Deterministic And Strict

Owner: coder in `tmux astro:0.0`
Architect/review: current Codex thread
Branch: main
Push/deploy: do not push/deploy before architect review

## Goal

Finish W2 by tightening the Rework 02 behavioral tests so they prove the actual TodayService contract without depending on live sidecar/natal cache state.

Do not change production behavior unless the stricter tests expose a real bug.

## Required Fixes

### 1. Remove accidental sidecar/natal-context dependency

In `apps/api/tests/test_today_meta_versions.py`, update `test_today_service_fresh_payload_activation_layer_wiring` so it does not call live SolarSage natal calculation and does not rely on existing natal cache.

Required:

- Patch `app.services.today_service.NatalContextService.get_or_build_natal_context` to return a deterministic valid `NatalContextData`, or pre-seed `NatalChartCache` and explicitly prove the sidecar natal client is not called.
- Preferred: patch `NatalContextService.get_or_build_natal_context`.
- Remove unused `mock_natal_data`.
- Keep `get_solarsage_client().get_transits` mocked for the transit call.

The test must be hermetic: it should pass even if `solarsage-sidecar.service` is down.

### 2. Control normalized day signals explicitly

Patch `app.services.today_service.NormalizationService.normalize_day(...)` to return deterministic `AstroSignal` fixtures.

Use at least these signals:

```python
transit_aspect = AstroSignal(
    type="aspect",
    planet="Transit_Moon",
    target_planet="Pluto",
    aspect_type="opposition",
    orb=1.0,
    strength=0.9,
)
transit_house = AstroSignal(
    type="planet_in_house",
    planet="Transit_Mars",
    house=12,
    strength=1.0,
)
static_background = AstroSignal(
    type="planet_in_house",
    planet="Sun",
    house=5,
    strength=1.0,
)
```

Patch `TodayService._get_yesterday_signals` to return `None` or `[]`, so the day-delta step cannot rewrite the deterministic fixture list.

### 3. Strengthen scoring assertions

In the fresh/full test, assert exactly:

```python
assert mock_scoring.score_day.call_count == 1
call_args, call_kwargs = mock_scoring.score_day.call_args
assert len(call_args) == 1
assert call_kwargs == {}
assert call_args[0] == [transit_aspect, transit_house]
```

The static/non-transit `Sun` background signal must not be passed into scoring.

Also assert that no `ActivationLayer` object appears in scoring positional args:

```python
from app.schemas.activation import ActivationLayer
assert all(not isinstance(arg, ActivationLayer) for arg in call_args)
```

### 4. Preserve activation-layer semantic assertions

Keep the positive W2 semantic checks:

- `SemanticService.build_why_contexts(...)` is called;
- its `activation_layer` kwarg is an `ActivationLayer`;
- `activation_layer.activation_layer_version == "al-1.0"`;
- activations include `transit_to_natal`;
- activations include `transit_planet_in_house`;
- returned payload meta has `activation_layer_version == "al-1.0"`;
- returned payload meta has `scoring_version == 1`.

### 5. Preserve locked-preview guard

Keep or strengthen:

- locked preview access state is locked;
- `payload.meta.activation_layer_version is None`;
- `payload.meta.scoring_version == 1`.

### 6. Clean reports and generated churn

Write:

```text
docs/work/2026-07-09_solarsage-v2-w2-activation-layer/10_rework_03_report.md
```

Include:

- changed files;
- how the test avoids live sidecar/natal cache;
- exact scoring call assertions;
- exact verification results;
- commit SHA;
- push status `NOT_ATTEMPTED`.

Do not commit generated `next-env.d.ts` churn.

Unrelated untracked files already present may remain untracked:

- `.grace/`
- `grace.db`
- `skills/`
- `docs/superpowers/plans/2026-07-05-fix-day-route-auth-build.md`

## Required Verification

Run and report exact results:

```bash
cd apps/api && source .venv/bin/activate && python -m pytest tests/test_today_meta_versions.py tests/test_activation_layer_contract.py tests/test_day_endpoints.py -q
```

```bash
cd apps/api && source .venv/bin/activate && python -m pytest tests/test_activation_layer_contract.py tests/test_activation_contracts.py tests/test_today_meta_versions.py tests/test_day_endpoints.py tests/test_astronomy_oracle.py -q
```

```bash
cd apps/api && source .venv/bin/activate && python -m pytest tests/ -q
```

```bash
cd apps/solarsage && venv/bin/python -m pytest tests/test_activation_layer_endpoint.py tests/test_activation_schema.py -q
cd apps/solarsage && venv/bin/python -m pytest tests/ -q
```

```bash
pnpm contracts:generate
git diff --exit-code -- packages/contracts/openapi.json packages/contracts/_generated.ts
npx vitest run
```

```bash
make audit-day USER_ID=eb3876be-e1b4-43d6-b887-1f8554e33150 DATE=2026-07-08
git diff --exit-code -- artifacts/audit/2026-07-08
```

```bash
rg -n 'inspect\.getsource' apps/api/tests/test_today_meta_versions.py
echo "Expected: no matches"
rg -n 'ss-scoring-2.0' apps/api/app/services/today_service.py artifacts/audit/2026-07-08/11_final_today_payload.json || true
rg -n 'activation_layer=None' apps/api/app/services/today_service.py
rg -n 'transit_planet_in_house|transit_to_natal|Transit Moon opposition natal Pluto|activation-layer.v1|al-1.0' artifacts/audit/2026-07-08/16_activation_layer.json
git diff 2f9173fbe9a9e20e97891e9789db6de57a2afaef..HEAD --check
git show --check HEAD
git status --short --branch
```

For the `rg -n 'inspect\.getsource'` command, no matches is the expected success condition; use `|| true` only if needed so the script continues, but report that there were no matches.

## Callback

After committing and writing the report, call:

```bash
curl -X POST http://127.0.0.1:18765/trigger \
  -H "Authorization: Bearer 324b0306c32ffc5f6a64e16076c8c9ac0ee12fbba925cfd3" \
  -H "Content-Type: application/json" \
  -d '{"prompt":"Wave W2 Rework 03 ready for architect review. Report: docs/work/2026-07-09_solarsage-v2-w2-activation-layer/10_rework_03_report.md. Review: docs/work/2026-07-09_solarsage-v2-w2-activation-layer/08_rework_02_review.md. Rework TZ: docs/work/2026-07-09_solarsage-v2-w2-activation-layer/09_rework_03_TZ.md. Branch: main. Commit: <commit_sha>. Push: NOT_ATTEMPTED"}'
```
