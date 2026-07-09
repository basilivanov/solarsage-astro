# Architect Review: Wave W2 Activation Layer

Status: REWORK REQUIRED

Reviewed commits:

- implementation: `aff70066da944e4e8fa0af2295ece23e748f7d92`
- report: `5dabad40351afbef59e6feabaddf2b3d4aa96072`

## Summary

W2 moved in the right direction:

- API `ActivationLayerService` exists and builds transit-to-natal plus transit planet-in-house activations;
- sidecar `/v1/activation-layer` contract endpoint exists;
- audit artifact `16_activation_layer.json` exists and contains Basil 2026-07-08 transit activations;
- `TODAY_CONTENT_VERSION` was bumped to 8;
- runtime `TodayMeta.activation_layer_version` is set for full fresh payloads.

W2 cannot be accepted yet because several explicit W2 requirements are not met or not truthfully reported.

## Blocking Findings

### P0. Whitespace gate is red

Required W2 verification included:

```bash
git diff 2f9173fbe9a9e20e97891e9789db6de57a2afaef..HEAD --check
git show --check HEAD
```

Architect rerun:

```text
apps/solarsage/solarsage/api/activation_layer.py:65: trailing whitespace.
apps/solarsage/solarsage/services/activation_builder.py:25: trailing whitespace.
```

The agent report says this gate is clean, which is false for current HEAD.

Required fix:

- Remove trailing whitespace.
- Rerun and report both whitespace checks exactly.

### P0. TodayService builds the activation layer but still passes `None` to semantic contexts

W2 TZ required:

> Pass `activation_layer` to `SemanticService.build_why_contexts(...)` only as structured future evidence; it must not change text in W2.

Current `apps/api/app/services/today_service.py` still does:

```python
activation_layer=None,
```

This breaks the docs/15 target pipeline contract: the layer exists but is not actually threaded through the semantic context boundary.

Required fix:

- Pass the actual `activation_layer` object to `build_why_contexts`.
- Add a regression test that monkeypatches or spies `SemanticService.build_why_contexts` and proves it receives an `ActivationLayer` with `activation_layer_version == "al-1.0"`.
- The test must also prove scoring remains v1 and receives only `day_signals`, not the activation layer.

### P1. Required TodayService metadata tests are missing

W2 TZ required tests proving:

- full fresh payload meta has `activation_layer_version == "al-1.0"`;
- scoring input/result remains based on `day_signals`;
- locked preview does not claim an activation layer.

Current changes only update the old content-version assertion in `test_day_endpoints.py`. There is no test that exercises full fresh payload `activation_layer_version`, no test for preview `activation_layer_version is None`, and no explicit scoring-input guard around the new activation layer wiring.

Required fix:

- Add/extend TodayService endpoint/service tests for all three bullets.
- Keep `TODAY_CONTENT_VERSION == 8`.

### P1. W2 report contains an invalid implementation SHA

Report says:

```text
aff700623b549331360c757cc8f4ab270c0424c0
```

That object does not exist. Current implementation commit is:

```text
aff70066da944e4e8fa0af2295ece23e748f7d92
```

Required fix:

- Update the report with the real implementation commit, or the new rework commit if the report is amended after fixes.

### P2. Sidecar endpoint module has dead placeholder classes

`apps/solarsage/solarsage/api/activation_layer.py` defines placeholder classes:

```python
class ActivationLayerRequest:
class BirthInfo:
class TargetInfo:
```

then later redefines `ActivationLayerRequest` as a Pydantic model after importing `BaseModel`.

This is harmless at runtime but unnecessary and confusing in a contract module.

Required fix:

- Remove dead placeholder classes.
- Move Pydantic imports to the normal import section.

### P2. Activation builders should guard on explicit `Transit_` source

The report says transit aspect and house activations map signals "where planet starts with `Transit_`", but `ActivationLayerService` currently relies on `filter_day_scored_signals()` and does not explicitly guard before calling `_build_transit_aspect` / `_build_transit_in_house`.

Current `AstroSignal.type` makes this mostly safe today, but W2's service contract should be robust when future day-event signals are added.

Required fix:

- In `ActivationLayerService`, only build W2 transit activations when `(signal.planet or "").startswith("Transit_")`.
- Add a small negative test for a non-transit aspect or house signal passed to `build()`.

## Evidence To Preserve

Keep these positive parts:

- `artifacts/audit/2026-07-08/16_activation_layer.json` contains:
  - `Transit Moon opposition natal Pluto`;
  - `transit_to_natal`;
  - `transit_planet_in_house`;
  - no fake unsupported techniques.
- Sidecar endpoint remains contract-only and is not a hard TodayService runtime dependency.
- Runtime `/day` remains scoring v1 and does not claim `ss-scoring-2.0`.
- New audit artifact should remain deterministic after rework.

## Required Rework

See `03_rework_01_TZ.md`.
