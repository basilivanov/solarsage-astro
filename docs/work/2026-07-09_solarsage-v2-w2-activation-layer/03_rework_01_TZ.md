# Rework 01 TZ: Finish W2 Activation Layer Wiring And Gates

Owner: coder in `tmux astro:0.0`
Architect/review: current Codex thread
Branch: main
Push/deploy: do not push/deploy before architect review

## Goal

Fix the blockers in `02_arch_review.md` without expanding into W3 or V2 scoring.

Keep W2 as:

- API builds minimal activation layer from `day_signals`;
- sidecar endpoint is contract-only;
- scoring remains v1;
- no frontend visual changes.

## Required Fixes

### 1. Fix whitespace gates

Remove trailing whitespace in:

- `apps/solarsage/solarsage/api/activation_layer.py`
- `apps/solarsage/solarsage/services/activation_builder.py`

Rerun:

```bash
git diff 2f9173fbe9a9e20e97891e9789db6de57a2afaef..HEAD --check
git show --check HEAD
```

### 2. Pass activation layer into semantic contexts

In `apps/api/app/services/today_service.py`, replace:

```python
activation_layer=None
```

with the actual `activation_layer` object built earlier in the fresh full path.

Do not change LLM prompts, text generation, or scoring behavior in W2.

Add a regression test proving:

- `SemanticService.build_why_contexts(...)` receives an `ActivationLayer`;
- the object has `activation_layer_version == "al-1.0"`;
- the layer contains at least one W2 minimal activation when day signals include transits.

### 3. Add missing TodayService metadata/scoring tests

Add or extend tests proving:

- fresh full `TodayPayload.meta.activation_layer_version == "al-1.0"`;
- locked preview payload keeps `activation_layer_version is None`;
- `ScoringService.score_day(...)` is still called with `day_signals` only and no activation-layer argument;
- runtime `scoring_version` remains `1`.

Keep `TODAY_CONTENT_VERSION == 8`.

### 4. Clean sidecar contract module

In `apps/solarsage/solarsage/api/activation_layer.py`:

- remove dead placeholder classes;
- move `from pydantic import BaseModel, Field` to the top import section;
- keep endpoint response shape unchanged.

### 5. Explicit Transit guard in ActivationLayerService

In `ActivationLayerService`, build W2 transit activations only when:

```python
(signal.planet or "").startswith("Transit_")
```

Add a negative test with non-transit aspect/house signals passed to `build()` and assert they do not produce activations.

### 6. Fix report accuracy

Update:

```text
docs/work/2026-07-09_solarsage-v2-w2-activation-layer/01_agent_report.md
```

or write a new rework report:

```text
docs/work/2026-07-09_solarsage-v2-w2-activation-layer/04_rework_01_report.md
```

Preferred: write the new rework report and leave the original as historical.

The new report must include:

- new commit SHA;
- exact verification results;
- mention that the previous report had an invalid SHA and is superseded;
- push status `NOT_ATTEMPTED`.

## Required Verification

Run and report exact results:

```bash
cd apps/api && source .venv/bin/activate && python -m pytest tests/test_activation_layer_contract.py tests/test_activation_contracts.py tests/test_today_meta_versions.py tests/test_day_endpoints.py tests/test_astronomy_oracle.py -q
```

```bash
cd apps/api && source .venv/bin/activate && python -m pytest tests/ -q
```

```bash
cd apps/solarsage && venv/bin/python -m pytest tests/test_activation_layer_endpoint.py tests/test_activation_schema.py -q
```

```bash
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
rg -n 'ss-scoring-2.0' apps/api/app/services/today_service.py artifacts/audit/2026-07-08/11_final_today_payload.json || true
rg -n 'transit_planet_in_house|transit_to_natal|Transit Moon opposition natal Pluto|activation-layer.v1|al-1.0' artifacts/audit/2026-07-08/16_activation_layer.json
rg -n 'activation_layer=None' apps/api/app/services/today_service.py
echo "Expected: no matches for activation_layer=None in fresh full semantic context"
git diff 2f9173fbe9a9e20e97891e9789db6de57a2afaef..HEAD --check
git show --check HEAD
git status --short --branch
```

If `rg -n 'activation_layer=None'` finds the locked preview path or unrelated code, explain why it is not the fresh full semantic context. It must not remain in the fresh `build_why_contexts` call.

## Callback

After committing and writing the report, call:

```bash
curl -X POST http://127.0.0.1:18765/trigger \
  -H "Authorization: Bearer 324b0306c32ffc5f6a64e16076c8c9ac0ee12fbba925cfd3" \
  -H "Content-Type: application/json" \
  -d '{"prompt":"Wave W2 Rework 01 ready for architect review. Report: docs/work/2026-07-09_solarsage-v2-w2-activation-layer/04_rework_01_report.md. Review: docs/work/2026-07-09_solarsage-v2-w2-activation-layer/02_arch_review.md. Rework TZ: docs/work/2026-07-09_solarsage-v2-w2-activation-layer/03_rework_01_TZ.md. Branch: main. Commit: <commit_sha>. Push: NOT_ATTEMPTED"}'
```
