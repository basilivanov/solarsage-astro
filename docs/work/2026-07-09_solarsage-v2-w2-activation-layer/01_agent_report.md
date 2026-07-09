# Wave W2 Report: Activation Layer Infrastructure

## Changed Files

**New files:**
- `apps/api/app/services/activation_layer_service.py` — API `ActivationLayerService` with transit aspect and planet-in-house builders
- `apps/api/tests/test_activation_layer_contract.py` — 4 tests
- `apps/api/tests/fixtures/activation_layer_minimal.json` — Minimal fixture
- `apps/solarsage/solarsage/api/activation_layer.py` — Sidecar `POST /v1/activation-layer` endpoint
- `apps/solarsage/solarsage/services/activation_builder.py` — W2 contract-only builder (empty layer with warning)
- `apps/solarsage/tests/test_activation_layer_endpoint.py` — 2 tests
- `artifacts/audit/2026-07-08/16_activation_layer.json` — New audit artifact
- `artifacts/audit/2026-07-08/debug/activation_layer.json` — Debug copy

**Modified files:**
- `apps/api/app/services/today_service.py` — Wired `ActivationLayerService` after `day_signals`, added `activation_layer_version` to `TodayMeta`, bumped `TODAY_CONTENT_VERSION` to 8
- `apps/api/app/services/canon_service.py` — Added `transit_planet_in_house` to known technique keys
- `apps/api/tests/test_day_endpoints.py` — Updated content version assertion to 8
- `apps/solarsage/solarsage/app.py` — Registered activation layer router
- `grace/canon/activation_rules.v1.yml` — Added `transit_planet_in_house` to transit family
- `scripts/audit_today.py` — Builds activation layer and writes `16_activation_layer.json`

## API ActivationLayerService Design

- Builds activation layer from `day_signals` only (static natal background excluded via `filter_day_scored_signals`).
- Two activation sources:
  - **Transit aspect to natal planet** (`transit_to_natal`): maps `AstroSignal(type="aspect")` where planet starts with `Transit_`. Sets `target_frame="natal"`, `source_frame="transit"`, polarity from aspect type, evidence string like `Transit Moon opposition natal Pluto, orb 1.0454°`.
  - **Transit planet in natal house** (`transit_planet_in_house`): maps `AstroSignal(type="planet_in_house")` where planet starts with `Transit_`. Sets `target_type="house"`, evidence string like `Transit Sun in natal house 1, strength 1.00`.
- IDs are deterministic: e.g., `t2n__MOON__PLUTO`, `tih__SUN__1`.
- Index maps: `by_planet` by uppercase target planet, `by_house` by string house number.
- Accepts optional `sidecar_activation_layer` (validates with API schema and returns it).

## TodayService Wiring

- `ActivationLayerService().build(...)` called after `filter_day_scored_signals(signals)` and before `ScoringService().score_day(day_signals)`.
- `activation_layer_version=activation_layer.activation_layer_version` added to fresh/payload `TodayMeta`.
- `TODAY_CONTENT_VERSION` bumped from 7 to 8 (payload meta shape changed).
- Scoring remains v1 — activation layer is NOT passed into scoring.
- `scoring_version` remains `1`, no `ss-scoring-2.0` in runtime paths.

## Sidecar Endpoint

- `POST /v1/activation-layer` added with request/response schemas.
- W2: returns an empty activation layer with warning `contract_only_no_techniques_built_yet`.
- Not yet a hard runtime dependency in `TodayService` (can be wired in W3+).

## Audit Artifact

`16_activation_layer.json` now produced by `make audit-day`. Contains full Basil 2026-07-08 activation evidence including `Transit Moon opposition natal Pluto` and transit planet-in-house activations. No fake/unsupported techniques present.

## Verification Results

| Command | Result |
|---|---|
| `cd apps/api && python -m pytest tests/ -q` | **674 passed, 5 skipped** |
| `cd apps/solarsage && python -m pytest tests/ -q` | **28 passed** |
| `pnpm contracts:generate` + `git diff --exit-code contracts` | **Clean** |
| `make audit-day` + `git diff --exit-code` | **Deterministic** |
| `rg ss-scoring-2.0` in runtime paths | **No matches** |
| `rg 'Transit Moon opposition natal Pluto'` in `16_activation_layer.json` | **Found** |
| `git diff 2f9173f..HEAD --check` | **Clean** |
| `git show --check HEAD` | **Clean** |
| `git status --short --branch` | Only known unrelated untracked files |

## Commit SHA
- **Commit**: `aff700623b549331360c757cc8f4ab270c0424c0`

## Push/Deploy Status
- **Push**: NOT_ATTEMPTED
