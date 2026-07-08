# Architect Review: Wave W1 Contracts / Canon / Versioning

Status: REWORK REQUIRED

Reviewed commit: `dc7a87fd617f2d7b0ab482427b2d71d58d419353`
Implementation commit: `f3678cdfb5dcadfa995c9231bb8dc1042ecfbad9`

## Summary

The W1 implementation added useful initial schemas, canon files, tests, and versioning fields. The full API suite reportedly passes, and the new local schema tests are a good start.

W1 cannot be accepted because several explicit W1 requirements are not met:

- canon loader is not wired into production startup/import path;
- generated OpenAPI/TS contracts do not include the new top-level contracts;
- `ActivationLayer` does not validate index references;
- runtime `TodayMeta` does not include `canon_versions` despite keeping numeric v1 versions;
- whitespace check is currently red.

## Blocking Findings

### P0. Canon loader is not wired into production startup/import path

The W1 TZ required:

> `activation_rules.v1.yml` and `scoring_v2.v1.yml` must be loaded and validated by production API startup/import path.

The agent report says the opposite:

> Canon loader is created but not yet wired into production startup.

Current evidence:

```bash
rg -n "canon_service|validate_canon|load_canon_bundle|CANON_VERSIONS" apps/api/app apps/api/tests scripts packages
```

Only tests and the new service reference it. `apps/api/app/main.py` and `ScoringService` do not validate the full canon bundle.

Also `load_canon_bundle()` currently logs and continues on missing/invalid files. That is the opposite of "fail loudly" for dev/test startup.

Required fix:

- Wire strict validation into API startup/import path, preferably in `apps/api/app/main.py`.
- The startup/import path must call a strict function, e.g. `validate_canon_bundle()`, not the best-effort `load_canon_bundle()`.
- Missing/invalid `activation_rules.v1.yml` or `scoring_v2.v1.yml` must make API boot fail in dev/test.
- Add a test proving `apps/api/app/main.py` boot/startup invokes strict canon validation. Use monkeypatch/import strategy; do not mutate committed canon.

### P0. OpenAPI/TS contracts were not regenerated and do not expose W1 contracts

The W1 TZ required generated TS/OpenAPI components for:

- `ActivationLayer`
- canonical activation evidence schema from `apps/api/app/schemas/activation.py`
- `ScoringV2Result`
- `SphereScoreV2`
- `SphereContribution`

But implementation commit did not modify:

```text
packages/contracts/openapi.json
packages/contracts/_generated.ts
scripts/contracts/export_openapi.py
```

Current evidence:

```bash
rg -n "ActivationLayer|ScoringV2Result" packages/contracts/openapi.json packages/contracts/_generated.ts
```

No matches.

`scripts/contracts/export_openapi.py` still has the old `_TOP_LEVEL_NAMES` and does not include `ActivationLayer` or `ScoringV2Result`.

Required fix:

- Add new top-level schemas to the OpenAPI export registry.
- Run `pnpm contracts:generate`.
- Commit `packages/contracts/openapi.json` and `packages/contracts/_generated.ts`.
- Add a regression test or contract check proving the generated files contain `ActivationLayer` and `ScoringV2Result`.

Important collision note:

`apps/api/app/schemas/today.py` already contains a legacy `ActivationEvidence` used by `TodayPayload.activation_evidence`, while W1 adds canonical `app.schemas.activation.ActivationEvidence`.

The rework must resolve this cleanly. Acceptable options:

- If Pydantic/OpenAPI emits unambiguous component names for both schemas, add tests proving `ActivationLayer.activations[]` points to the canonical activation evidence schema with fields like `techniqueFamily`, `targetType`, `strength`, and not the legacy `theme/convergenceLevel` schema.
- If schema names collide or generated TS becomes confusing, rename the legacy Today schema to a clear internal name such as `ConvergenceEvidence` while preserving the wire field `activationEvidence`.

Do not leave generated contracts ambiguous.

### P0. `ActivationLayer` does not validate index references

The W1 TZ required:

> every id referenced by index maps exists in `activations`.

Current `ActivationLayer` only has typed maps:

```python
by_planet: dict[str, list[str]]
by_house: dict[str, list[str]]
by_lot: dict[str, list[str]]
by_angle: dict[str, list[str]]
```

There is no `model_validator` checking that referenced ids exist in `activations`.

Required fix:

- Add a model validator to API `ActivationLayer`.
- Add the same or equivalent validator to sidecar `ActivationLayer`.
- Add tests where `by_planet={"MOON": ["missing-id"]}` fails.

### P1. Runtime TodayMeta does not include `canon_versions`

The W1 TZ said:

> If keeping numeric v1 versions in runtime payload, add `canon_versions` and keep `activation_layer_version=None`.

Current `TodayService` still builds:

```python
calculation_version=1
scoring_version=1
...
cached=False
```

and does not set `canon_versions`.

Required fix:

- Import `get_canon_versions()` or equivalent.
- Add `canon_versions=get_canon_versions()` to full and preview `TodayMeta`.
- Keep `activation_layer_version=None` until W2.
- Do not set runtime scoring version to `ss-scoring-2.0`.

### P1. `git diff --check` is red

Current command:

```bash
git diff 2f9173fbe9e20e97891e9789db6de57a2afaef..HEAD --check
```

Observed:

```text
apps/api/app/services/canon_service.py:64: trailing whitespace.
```

Required fix:

- Remove trailing whitespace.
- Re-run both `git diff 2f9173f...HEAD --check` and `git show --check HEAD`.

### P2. W1 report omitted required verification

The W1 TZ required:

```bash
pnpm contracts:generate
git diff --exit-code -- packages/contracts/openapi.json packages/contracts/_generated.ts
npx vitest run
```

The report does not include those results. If broad `npx vitest run` fails for unrelated existing reasons, report the failure honestly and run a narrower contract-affected frontend test set.

## Passing Evidence To Preserve

The following are useful and should remain green:

- API W1 unit tests: `18 passed`.
- sidecar activation tests: `4 passed`.
- full API suite reportedly: `667 passed, 5 skipped`.
- no runtime `TodayService` path should claim `ss-scoring-2.0` before W4.

## Required Rework

See `03_rework_01_TZ.md`.

