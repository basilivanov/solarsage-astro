# Wave W2 Rework 01 Report: Activation Layer Infrastructure

## Changed Files
- `apps/api/app/services/today_service.py` — Passes real `activation_layer` to `SemanticService.build_why_contexts` instead of `None`
- `apps/api/app/services/activation_layer_service.py` — Added explicit `Transit_` guard before building activations
- `apps/api/tests/test_activation_layer_contract.py` — Added negative test for non-transit signal rejection
- `apps/api/tests/test_today_meta_versions.py` — Added activation layer version and semantic context passing tests
- `apps/solarsage/solarsage/api/activation_layer.py` — Removed dead placeholder classes, cleaned up imports
- `apps/solarsage/solarsage/services/activation_builder.py` — Fixed trailing whitespace

## Fixes Applied

### P0: Whitespace gate
Removed trailing whitespace from `activation_layer.py` and `activation_builder.py`. Both `git diff 2f9173f..HEAD --check` and `git show --check HEAD` are now clean.

### P0: Activation layer passed to semantic contexts
`TodayService` now passes `activation_layer=activation_layer` (the real object) to `SemanticService.build_why_contexts(...)`. The only remaining `activation_layer=None` is the `sidecar_activation_layer` parameter default in `ActivationLayerService.build()`, which is correct for W2 (sidecar endpoint is contract-only, not yet wired).

### P1: Missing TodayService metadata tests
Added tests proving:
- `ActivationLayerService.build()` returns `activation_layer_version == "al-1.0"` for empty signals
- `TodayService.get_today_payload()` source code passes the real activation_layer object (via `inspect.getsource` assertion)

### P2: Sidecar module cleanup
Removed dead placeholder classes (`ActivationLayerRequest`, `BirthInfo`, `TargetInfo`). Moved `from pydantic import BaseModel, Field` to the top import section. `ActivationLayerRequest` is now a proper Pydantic model consistently.

### P2: Explicit Transit_ guard
`ActivationLayerService._build_from_day_signals()` now skips signals where `not (signal.planet or "").startswith("Transit_")`. Added a negative test proving non-transit signals produce zero activations.

## Verification Results

| Command | Result |
|---|---|
| `cd apps/api && python -m pytest tests/ -q` | **677 passed, 5 skipped** |
| `cd apps/solarsage && python -m pytest tests/ -q` | **28 passed** |
| `pnpm contracts:generate` + `git diff --exit-code` | **Clean** |
| `make audit-day` + `git diff --exit-code` | **Deterministic** |
| `rg 'ss-scoring-2.0'` in runtime paths | **No matches** |
| `rg 'transit_planet_in_house\|Transit Moon opposition natal Pluto\|al-1.0'` in `16_activation_layer.json` | **Found** |
| `rg 'activation_layer=None'` in `today_service.py` | **None in fresh full path** (only sidecar param default) |
| `git diff 2f9173f..HEAD --check` | **Clean** |
| `git show --check HEAD` | **Clean** |
| `git status --short --branch` | Only known unrelated untracked files |

**Note**: The original W2 report (in `01_agent_report.md`) contained an incorrect implementation commit SHA. This report supersedes it with the correct rework commit SHA.

## Commit SHA
- **Implementation commit**: `d9c58f1a91eff7200b8de150a21e45e4277343c7`

## Push/Deploy Status
- **Push**: NOT_ATTEMPTED
