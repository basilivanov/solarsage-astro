# Rework 02 TZ: Replace Source Inspection With Behavioral W2 Guards

Owner: coder in `tmux astro:0.0`
Architect/review: current Codex thread
Branch: main
Push/deploy: do not push/deploy before architect review

## Goal

Finish W2 acceptance by replacing weak source-code assertions with behavioral tests that exercise the actual `TodayService.get_today_payload()` fresh/full and locked-preview paths.

Do not expand into W3 or scoring v2.

## Required Fixes

### 1. Remove source inspection test

In `apps/api/tests/test_today_meta_versions.py`, remove the `inspect.getsource(...)` assertion.

Do not use string/source-code checks for W2 wiring. The test must fail if the runtime call stops passing a real activation layer.

### 2. Add behavioral fresh full payload regression

Add a test that calls `TodayService.get_today_payload(...)` on the fresh/full path with controlled dependencies.

The test must prove all of these facts from actual runtime calls:

- `SemanticService.build_why_contexts(...)` is called;
- its `activation_layer` kwarg is an `ActivationLayer`;
- `activation_layer.activation_layer_version == "al-1.0"`;
- the layer contains at least one W2 minimal activation from transit signals;
- at least one activation has `technique == "transit_to_natal"` or `technique == "transit_planet_in_house"`;
- the returned `TodayPayload.meta.activation_layer_version == "al-1.0"`;
- the returned `TodayPayload.meta.scoring_version == 1`.

Implementation guidance:

- Use `monkeypatch`/`unittest.mock` around:
  - `NatalContextService.get_or_build_natal_context`;
  - `get_solarsage_client`;
  - `NormalizationService.normalize_day`;
  - `DayDeltaService` or `_get_yesterday_signals` if needed to keep the signal list deterministic;
  - `ScoringService.score_day`;
  - `SemanticService.build_semantic_layer`;
  - `SemanticService.build_why_contexts`;
  - `LLMService` generation methods;
  - `TodayImportantService` only if the payload builder reaches it.
- Prefer an existing test pattern from `apps/api/tests/test_day_no_birthday_fallback.py` or `apps/api/tests/test_wave3_day_pipeline_reuse.py`.
- Use real `AstroSignal` objects for the day signals, including at least:
  - `AstroSignal(type="aspect", planet="Transit_Moon", target_planet="Pluto", aspect_type="opposition", orb=1.0, strength=0.9)`;
  - `AstroSignal(type="planet_in_house", planet="Transit_Mars", house=12, strength=1.0)`.
- Do not assert by reading `today_service.py` source.

### 3. Add scoring input guard

In the same behavioral test or a focused companion test, prove:

- `ScoringService.score_day(...)` is called exactly once;
- it receives exactly the day-scored transit signal list;
- it receives no `activation_layer` positional or keyword argument.

The point is to lock W2 behavior: activation layer is observable evidence, not scoring input yet.

### 4. Add locked preview guard

Add or extend a test that calls `TodayService.get_today_payload(...)` with `ContentAccessState(state="locked", ...)`.

Assert:

- returned payload access state is locked;
- `payload.meta.activation_layer_version is None`;
- `payload.meta.scoring_version == 1`;
- the preview path does not fake an activation layer.

### 5. Keep generated files clean

Do not include generated `next-env.d.ts` churn.

Before commit, ensure:

```bash
git status --short --branch
```

does not show `M next-env.d.ts`.

Unrelated untracked files already present in this workspace may remain untracked:

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
git diff 2f9173fbe9a9e20e97891e9789db6de57a2afaef..HEAD --check
git show --check HEAD
git status --short --branch
```

If the first command set is clean, run the broader W2 gates too unless a test failure requires another rework:

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
rg -n 'ss-scoring-2.0' apps/api/app/services/today_service.py artifacts/audit/2026-07-08/11_final_today_payload.json || true
rg -n 'activation_layer=None' apps/api/app/services/today_service.py
rg -n 'transit_planet_in_house|transit_to_natal|Transit Moon opposition natal Pluto|activation-layer.v1|al-1.0' artifacts/audit/2026-07-08/16_activation_layer.json
```

## Report

Write:

```text
docs/work/2026-07-09_solarsage-v2-w2-activation-layer/07_rework_02_report.md
```

Include:

- changed files;
- which source-inspection test was removed;
- how the new behavioral tests prove the fresh/full and locked-preview contracts;
- exact verification results;
- commit SHA;
- push status `NOT_ATTEMPTED`.

## Callback

After committing and writing the report, call:

```bash
curl -X POST http://127.0.0.1:18765/trigger \
  -H "Authorization: Bearer 324b0306c32ffc5f6a64e16076c8c9ac0ee12fbba925cfd3" \
  -H "Content-Type: application/json" \
  -d '{"prompt":"Wave W2 Rework 02 ready for architect review. Report: docs/work/2026-07-09_solarsage-v2-w2-activation-layer/07_rework_02_report.md. Review: docs/work/2026-07-09_solarsage-v2-w2-activation-layer/05_rework_01_review.md. Rework TZ: docs/work/2026-07-09_solarsage-v2-w2-activation-layer/06_rework_02_TZ.md. Branch: main. Commit: <commit_sha>. Push: NOT_ATTEMPTED"}'
```
