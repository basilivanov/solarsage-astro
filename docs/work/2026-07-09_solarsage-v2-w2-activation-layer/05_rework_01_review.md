# Architect Review: Wave W2 Rework 01

Status: REWORK REQUIRED

Reviewed commits:

- rework implementation: `d9c58f1`
- rework report: `00db386`

## Summary

Rework 01 fixed the main runtime wiring issue:

- `TodayService.get_today_payload()` now passes `activation_layer=activation_layer` into `SemanticService.build_why_contexts(...)`;
- sidecar placeholder classes were removed;
- the explicit `Transit_` guard exists in `ActivationLayerService`;
- whitespace gates are currently clean;
- targeted API tests pass locally: `10 passed`.

W2 is still not acceptable because the required TodayService regression tests are not behavioral. They mostly validate the schema/service in isolation and one test inspects source code text. That is too weak for the W2 boundary we are trying to protect.

## Blocking Finding

### P1. TodayService semantic/scoring regression is asserted by source inspection, not runtime behavior

File: `apps/api/tests/test_today_meta_versions.py`

Current test:

```python
source = inspect.getsource(TodayService.get_today_payload)
assert "activation_layer=activation_layer" in source
```

This does not prove the service passes a real `ActivationLayer` object at runtime. It would pass even if:

- the layer is empty when transit day signals exist;
- scoring receives the wrong input;
- `build_why_contexts` is not called in the exercised path;
- a future refactor keeps the string but breaks the call contract.

The Rework 01 TZ explicitly required:

- `SemanticService.build_why_contexts(...)` receives an `ActivationLayer`;
- that object has `activation_layer_version == "al-1.0"`;
- it contains at least one W2 minimal activation when day signals include transits;
- `ScoringService.score_day(...)` is still called with `day_signals` only and no activation-layer argument;
- fresh full payload meta has `activation_layer_version == "al-1.0"`;
- locked preview payload keeps `activation_layer_version is None`;
- runtime `scoring_version` remains `1`.

Current tests do not prove that full runtime chain.

## Evidence Checked

```bash
git diff 2f9173fbe9a9e20e97891e9789db6de57a2afaef..HEAD --check
git show --check HEAD
```

Result: clean.

```bash
cd apps/api && source .venv/bin/activate && python -m pytest tests/test_today_meta_versions.py tests/test_activation_layer_contract.py -q
```

Result: `10 passed in 0.04s`.

The pass result does not close the finding because one of the key tests is only a source-code string assertion.

## Required Rework

See `06_rework_02_TZ.md`.
