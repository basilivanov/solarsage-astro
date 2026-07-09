# W3.4 Rework 03 TZ — Test Contract Closure

Owner: coder in `tmux astro:0.0`
Architect/review: current Codex thread
Branch: `main`
Push/deploy: do not push/deploy

Read first:

- `docs/work/2026-07-09_solarsage-v2-w3-4-returns/06_rework_02_review.md`

## Goal

Close the remaining test-contract gaps for W3.4. Runtime behavior is already good; this rework should be tests/report only unless a test exposes a real code bug.

No W3.5. No TodayService wiring. No scoring v2. No frontend. No push/deploy.

## Required Work

### 1. Add malformed `current_location` endpoint tests

Add focused sidecar endpoint tests, preferably in:

```text
apps/solarsage/tests/test_activation_layer_endpoint.py
```

Cover:

- valid `current_location` with `lat/lon/tz` still returns 200;
- missing `current_location.lat` returns 422;
- missing `current_location.lon` returns 422;
- malformed current location does not become a 500.

Use `/v1/activation-layer` and return techniques so this covers the actual request model path.

### 2. Add no-TodayService-wiring regression test

Add a focused API test proving W3.4 did not wire `TodayService` to sidecar activation layer.

Acceptable approaches:

- monkeypatch/capture `ActivationLayerService.build(...)` and assert `sidecar_activation_layer is None` when `TodayService` builds a day payload;
- or, if constructing `TodayService` is too heavy, add a narrow source-level invariant test with a clear comment that this guards the W3.4 no-wiring boundary.

Prefer behavior-level capture if practical. Keep the test small and deterministic.

### 3. Update report

Update:

```text
docs/work/2026-07-09_solarsage-v2-w3-4-returns/01_agent_report.md
```

Include:

- the two added test names;
- exact verification results;
- commit SHA;
- push status `NOT_ATTEMPTED`.

### 4. Verification

Run at minimum:

```bash
cd apps/solarsage && venv/bin/python -m pytest \
  tests/test_activation_layer_endpoint.py \
  tests/test_solar_return.py \
  tests/test_lunar_return.py -q
```

```bash
cd apps/api && source .venv/bin/activate && python -m pytest \
  tests/test_activation_layer_returns.py \
  tests/test_today_meta_versions.py -q
```

Then rerun the full gates if any production code changed. If only tests/docs changed, full gates are still preferred but not required because architect already ran full gates on Rework 02.

## Callback

After tests, report update, and commit, call:

```bash
curl -X POST http://127.0.0.1:18765/trigger \
  -H "Authorization: Bearer 324b0306c32ffc5f6a64e16076c8c9ac0ee12fbba925cfd3" \
  -H "Content-Type: application/json" \
  -d '{"prompt":"Wave W3.4 Rework 03 ready for architect review. Report: docs/work/2026-07-09_solarsage-v2-w3-4-returns/01_agent_report.md. Review: docs/work/2026-07-09_solarsage-v2-w3-4-returns/06_rework_02_review.md. Rework TZ: docs/work/2026-07-09_solarsage-v2-w3-4-returns/07_rework_03_TZ.md. Branch: main. Commit: <commit_sha>. Push: NOT_ATTEMPTED"}'
```
