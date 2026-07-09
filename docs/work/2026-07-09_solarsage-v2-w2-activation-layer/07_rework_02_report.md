# Rework 02 Report — Wave W2 Activation Layer

## Summary

Replaced `inspect.getsource` test in `test_today_meta_versions.py` with two behavioral mock-based integration tests that exercise the real `TodayService.get_today_payload()` path:

1. **`test_today_service_fresh_payload_activation_layer_wiring`** — Proves that for a full (non-locked) payload:
   - `build_why_contexts` receives an `ActivationLayer` with version `al-1.0`
   - The layer contains `transit_to_natal` and `transit_planet_in_house` activations
   - Returned payload meta has `activation_layer_version == "al-1.0"`
   - `scoring_version` remains `1` (no V2 scoring)
   - `ScoringService.score_day` is called with only `day_signals` (no `activation_layer` kwarg)

2. **`test_today_service_locked_preview_no_activation_layer`** — Proves that a locked preview payload:
   - Has `access.state == "locked"`
   - Has `meta.activation_layer_version is None`
   - Has `meta.scoring_version == 1`

## Changes

| File | Change |
|------|--------|
| `apps/api/tests/test_today_meta_versions.py` | Replaced `inspect.getsource` assertion test with 2 behavioral mock tests |

## Verification

- `pytest apps/api/tests/test_today_meta_versions.py -q` — **6 passed**
- `pytest apps/api/tests/ -q` — **679 passed, 4 skipped** (no regressions)
- The `inspect.getsource` test was removed; coverage now comes from runtime mock-based assertions instead of source introspection.

## Remaining

None. Rework 02 is complete.
