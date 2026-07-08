# Wave W1 Report: Contracts / Canon / Versioning Skeleton

## Changed Files

**New files:**
- `apps/api/app/schemas/activation.py` — `ActivationEvidence`, `ActivationLayer`, type aliases
- `apps/api/app/schemas/scoring_v2.py` — `ScoringV2Result`, `SphereScoreV2`, `SphereContribution`
- `apps/api/app/services/canon_service.py` — Canon YAML loader with validation, versioning
- `apps/api/tests/test_activation_contracts.py` — 5 tests
- `apps/api/tests/test_scoring_v2_contracts.py` — 4 tests
- `apps/api/tests/test_canon_service.py` — 5 tests
- `apps/api/tests/test_today_meta_versions.py` — 2 tests
- `apps/solarsage/solarsage/schemas/activation.py` — Sidecar activation schemas
- `apps/solarsage/tests/test_activation_schema.py` — 4 tests
- `grace/canon/scoring_v2.v1.yml` — Scoring V2 canon config
- `grace/canon/activation_rules.v1.yml` — Updated with `technique_families` and `activation_strength`

**Modified files:**
- `apps/api/app/schemas/__init__.py` — Re-export activation and scoring V2 schemas
- `apps/api/app/schemas/today.py` — `TodayMeta` updated: `calculation_version`, `scoring_version` → `int | str`; added `canon_versions`, `audit_trace_id`; `activation_layer_version` → `int | str | None`
- `apps/api/app/services/today_service.py` — Bumped `TODAY_CONTENT_VERSION` from 6 to 7
- `apps/api/tests/test_day_endpoints.py` — Updated version assertion to 7

## What Was Added

### Activation Schemas
`ActivationEvidence` with all required fields, strength bounds `[0.0, 1.0]`, detailed transit/aspect metadata. `ActivationLayer` with `by_planet`, `by_house`, `by_lot`, `by_angle` index maps and `warnings`.

### Scoring V2 Contracts
`SphereContribution`, `SphereScoreV2` with full breakdown (base, activation, convergence, raw, final), and `ScoringV2Result` with nested sphere scores and top activations. Contract-only — not instantiated by `TodayService` or `ScoringService`.

### Canon Loader
`apps/api/app/services/canon_service.py` validates all five canon files at startup:
- `spheres.v1.yml`, `dignities.v1.yml`, `aspect_rules.v1.yml`, `activation_rules.v1.yml`, `scoring_v2.v1.yml`
- Checks `schema_version`, required top-level keys, technique family references
- Fails loudly on missing/invalid files
- `CANON_VERSIONS` dict exposed for metadata

### Versioning
`TodayMeta` supports both current int-based versions and future V2 string versions. `TODAY_CONTENT_VERSION` bumped to 7. Runtime payload still uses v1 values — no `ss-scoring-2.0` in production paths.

## Proof V2 Scoring Behavior Not Enabled

```bash
rg -n 'ss-scoring-2.0' artifacts/audit/2026-07-08/11_final_today_payload.json apps/api/app/services/today_service.py
```
Result: no matches. Production runtime does not claim V2.

## Verification Results

| Command | Result |
|---|---|
| `cd apps/api && python -m pytest tests/ -q` | **667 passed, 5 skipped** |
| `cd apps/solarsage && pytest tests/ -q` | **25 passed** |
| `scripts/test_audit_scoring_oracle.py` | **exit 0** |
| `make audit-day` + `git diff --exit-code` | **Deterministic** |
| `rg 'ss-scoring-2.0'` in production payload/paths | **No matches** |
| `git diff 2f9173f..HEAD --check` | **Clean** |
| `git show --check HEAD` | **Clean** |
| `git status --short --branch` | Only known unrelated untracked files |

## Known Limitations for W2+
- Activation layer is not yet computed or populated in `TodayPayload`.
- Scoring V2 contracts are not yet used by `ScoringService`.
- Canon loader is created but not yet wired into production startup (it can be imported and validated but doesn't block app startup yet).
- `ActivationLayer` is not exposed as an API endpoint.

## Commit SHA
- **Commit**: `f3678cdfb5dcadfa995c9231bb8dc1042ecfbad9`

## Push/Deploy Status
- **Push**: NOT_ATTEMPTED
