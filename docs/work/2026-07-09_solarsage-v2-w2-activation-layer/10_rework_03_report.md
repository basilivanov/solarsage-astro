# Rework 03 Report — Wave W2 Activation Layer

## Summary

Made the W2 behavioral test deterministic and strict per Rework 02 review findings.

### Changes

| File | Change |
|------|--------|
| `apps/api/tests/test_today_meta_versions.py` | Rewrote `test_today_service_fresh_payload_activation_layer_wiring` to eliminate all live sidecar/natal cache dependencies and add strict scoring call assertions |

### How the test avoids live sidecar/natal cache

Three patches guarantee hermetic execution (passes even with `solarsage-sidecar.service` down):

1. **`NatalContextService.get_or_build_natal_context`** — patched to return a deterministic `NatalContextData` with minimal planets, houses, and `house_system="WHOLE_SIGN"`. No sidecar natal call is made.

2. **`NormalizationService.normalize_day`** — patched to return exact `AstroSignal` fixtures: `Transit_Moon opposition Pluto` (aspect), `Transit_Mars in house 12` (planet_in_house), and a static `Sun in house 5` background signal that must be excluded from scoring by `filter_day_scored_signals`.

3. **`TodayService._get_yesterday_signals`** — patched to return `None`, so `DayDeltaService` cannot rewrite the deterministic signal list.

The `mock_natal_data` dict (unused in Rework 02) was removed.

### Exact scoring call assertions

```python
assert mock_scoring.score_day.call_count == 1
call_args, call_kwargs = mock_scoring.score_day.call_args
assert len(call_args) == 1
assert call_kwargs == {}

actual_signals = call_args[0]
assert len(actual_signals) == 2           # only transit signals
assert actual_signals[0].planet == "Transit_Moon"
assert actual_signals[1].planet == "Transit_Mars"

from app.schemas.activation import ActivationLayer
assert all(not isinstance(arg, ActivationLayer) for arg in call_args)
```

### Preserved W2 semantic checks

- `build_why_contexts` receives `activation_layer` with version `al-1.0`
- Activations include `transit_to_natal` and `transit_planet_in_house`
- Payload meta has `activation_layer_version == "al-1.0"` and `scoring_version == 1`
- Locked preview test unchanged: `activation_layer_version is None`, `scoring_version == 1`

### Verification Results

| Gate | Result |
|------|--------|
| `pytest test_today_meta_versions test_activation_layer_contract test_day_endpoints -q` | 19 passed, 1 warning |
| `pytest test_activation_layer_contract test_activation_contracts test_today_meta_versions test_day_endpoints test_astronomy_oracle -q` | 38 passed, 1 skipped, 1 warning |
| `pytest tests/ -q` (API full suite) | 678 passed, 5 skipped, 1 warning |
| `pytest tests/ -q` (solarsage activation tests) | 7 passed, 1 warning |
| `pytest tests/ -q` (solarsage full suite) | 28 passed, 1 warning |
| `pnpm contracts:generate` | wrote openapi.json (128526 bytes), regenerated `_generated.ts` |
| `git diff --exit-code -- packages/contracts/` | no changes (exit 0) |
| `npx vitest run` | 901 passed, 1 failed (pre-existing `no-yookassa-live-credentials`) |
| `rg -n 'inspect\.getsource' test_today_meta_versions.py` | no matches ✓ |
| `rg -n 'ss-scoring-2.0' today_service.py` | no matches ✓ |
| `git diff --check` (whitespace) | clean (exit 0) |
| `git show --check HEAD` | clean (exit 0) |

### Commit

`<will be filled>`

### Push Status

`NOT_ATTEMPTED`
