# Rework 02 Report — Wave W3.1 Transit Activations

## Summary

Closed remaining W3.1 Rework 01 test contract and traceability gaps.

## Changed Files

| File | Change |
|------|--------|
| `apps/solarsage/tests/test_activation_transits.py` | Strengthened Basil lot test to assert all 7 lots; replaced no-op uppercase evidence block with real assertion |

## Fixes

### Strengthened Basil lot regression test

Replaced:
```python
common = lot_keys & expected_lots
assert len(common) >= 1
```
With:
```python
missing = expected_lots - lot_keys
assert not missing, f"Missing expected Basil audit lots: {sorted(missing)}"
```

The test now fails if any one of the seven audit lot keys (`FORTUNE`, `SPIRIT`, `EROS`, `MARRIAGE`, `NECESSITY`, `VICTORY`, `NEMESIS`) disappears from `by_lot`.

### Removed no-op uppercase evidence block

Replaced the `pass`-only loop with a real assertion that checks for uppercase planet names in evidence text:
```python
planet_words = {"SUN", "MOON", "MERCURY", "VENUS", "MARS", "JUPITER", "SATURN", "URANUS", "NEPTUNE", "PLUTO"}
found_upper = [w for w in ev_text.split() if w in planet_words]
assert not found_upper
```

This fails when evidence contains uppercase planet display text like `natal PLUTO`.

## Verification Results

| Gate | Result |
|------|--------|
| `pytest test_activation_transits test_activation_layer_endpoint test_activation_schema -q` (sidecar) | 20 passed, 1 warning |
| `python3 scripts/audit_sidecar_activation.py` from repo root | Works ✓ |
| `git diff --exit-code -- artifacts/audit/.../17_sidecar_activation_layer.json` | clean ✓ |
| `PYTHONHASHSEED=random` × 3 | All identical ✓ |
| `rg 'Transit Moon opposition natal Pluto'` in artifact | Found ✓ |
| `rg 'natal PLUTO'` in artifact | No matches ✓ |
| `rg 'annual_profection|firdar_major|solar_return'` in artifact | No matches ✓ |
| `sidecar_activation_layer=None` in today_service.py | Still None ✓ |
| `git diff --check` (whitespace) | clean ✓ |

## Commit

`e5c4ff8`

## Push Status

`NOT_ATTEMPTED`
