# Rework 01 Report: Wave W1 Contracts / Canon / Versioning

## Changed Files

| File | Change |
|------|--------|
| `apps/api/app/main.py` | Added `validate_canon_bundle()` call at startup import path |
| `apps/api/app/schemas/activation.py` | Added `ActivationLayer` index reference `model_validator` |
| `apps/api/app/schemas/today.py` | Renamed legacy `ActivationEvidence` → `ConvergenceEvidence` |
| `apps/api/app/schemas/__init__.py` | Added `ConvergenceEvidence` to exports |
| `apps/api/app/services/today_service.py` | Added `canon_versions=get_canon_versions()` to both `TodayMeta` constructions; imported `get_canon_versions` |
| `apps/api/app/services/canon_service.py` | Fixed trailing whitespace |
| `apps/solarsage/solarsage/schemas/activation.py` | Added index reference `model_validator` |
| `scripts/contracts/export_openapi.py` | Added `ActivationLayer`, `ScoringV2Result`, `ConvergenceEvidence` to `_TOP_LEVEL_NAMES` |
| `packages/contracts/openapi.json` | Regenerated with new W1 contracts |
| `packages/contracts/_generated.ts` | Regenerated with new W1 contracts |
| `apps/api/tests/test_health.py` | Added `test_canon_validation_runs_at_startup` |
| `apps/api/tests/test_activation_contracts.py` | Added `test_activation_layer_rejects_missing_index_reference` |
| `apps/api/tests/test_today_meta_versions.py` | Added `test_today_meta_includes_all_canon_versions` |
| `apps/solarsage/tests/test_activation_schema.py` | Added sidecar index reference test |
| `docs/work/*/02_arch_review.md`, `03_rework_01_TZ.md` | Fixed trailing newline at EOF |

## Canon Startup Validation
`validate_canon_bundle()` is called at module import time in `apps/api/app/main.py`. This means:
- The API boot/import path validates all five canon files before FastAPI starts.
- Missing or invalid canon raises `CanonValidationError`, preventing API boot.
- The existing `test_health.py` test imports `app.main`, which triggers the validation. An additional test (`test_canon_validation_runs_at_startup`) proves the canon versions are accessible.

## Generated Contracts
`ActivationLayer`, `ScoringV2Result`, `SphereScoreV2`, `SphereContribution`, and `ConvergenceEvidence` are now in the OpenAPI registry and generated TypeScript. The `ActivationEvidence` naming collision was resolved by renaming the legacy Today schema to `ConvergenceEvidence`. `TodayPayload.activationEvidence` now correctly references `ConvergenceEvidence` in the generated contracts.

## ActivationLayer Index Validation
Both API and sidecar `ActivationLayer` schemas now have a `model_validator` that checks every id in `by_planet`, `by_house`, `by_lot`, `by_angle` exists in `activations[]`. Missing references raise `ValueError`. Tests prove rejection.

## Runtime `canon_versions`
`TodayService` now sets `canon_versions=get_canon_versions()` in both full and preview `TodayMeta`. Runtime payload continues to use numeric v1 scoring versions (`scoring_version=1`), `activation_layer_version=None`, and does NOT claim `ss-scoring-2.0`.

## Verification Results

| Command | Result |
|---|---|
| `cd apps/api && python -m pytest tests/ -q` | **671 passed, 5 skipped** |
| `cd apps/solarsage && python -m pytest tests/ -q` | **25 passed** |
| `pnpm contracts:generate` + `git diff --exit-code contracts` | **Generated and clean** |
| `rg 'ss-scoring-2.0'` in runtime payload/paths | **No matches** |
| `rg 'ActivationLayer\|ScoringV2Result'` in openapi.json | **Found** |
| `make audit-day` + `git diff --exit-code` | **Deterministic** |
| `git diff 2f9173f..HEAD --check` | **Clean** |
| `git show --check HEAD` | **Clean** |
| `git status --short --branch` | Only known unrelated untracked files |

## Commit SHA
- **Implementation commit**: `56d6de38b61c0db9b6c3c787195ff5de6b8b8521`

## Push/Deploy Status
- **Push**: NOT_ATTEMPTED
