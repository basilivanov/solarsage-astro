# Agent Report — Wave W3.1 Transit Activations

## Summary

Implemented sidecar-owned real transit activation extraction for all four W3.1 techniques: `transit_to_natal`, `transit_to_angle`, `transit_to_lot`, `transit_planet_in_house`. The sidecar `/v1/activation-layer` endpoint now produces deterministic ephemeris-based activations instead of the W2 contract-only empty layer. `TodayService` is NOT wired to the sidecar layer yet (`sidecar_activation_layer=None` remains).

## Changed Files

| File | Change |
|------|--------|
| `apps/solarsage/solarsage/services/activation_builder.py` | Full rewrite: real transit activation builder with ephemeris, canonical aspects, lots, angles, stable IDs |
| `apps/solarsage/solarsage/api/activation_layer.py` | Pass `techniques` to builder |
| `apps/solarsage/tests/test_activation_layer_endpoint.py` | Updated to expect real activations; added technique and unsupported-technique tests |
| `apps/solarsage/tests/test_activation_transits.py` | **New** — 7 sidecar transit activation tests |
| `apps/api/tests/test_activation_layer_transits.py` | **New** — 4 API boundary acceptance tests for sidecar dict |
| `scripts/audit_sidecar_activation.py` | **New** — deterministic audit artifact generator |
| `artifacts/audit/2026-07-08/17_sidecar_activation_layer.json` | **New** — Basil audit artifact (111 activations) |

## Sidecar Activation Builder Design

### Natal + Transit Context
- Calculate birth JD and natal planet positions via Swiss Ephemeris
- Calculate target JD and transit planet positions
- Calculate natal houses and angles (ASC, MC, DSC=ASC+180°, IC=MC+180°)
- Determine day/night chart from natal Sun house position

### Aspect Extraction
- Canonical aspect map loaded from `grace/canon/aspect_rules.v1.yml`:
  - `ASPECT_ANGLES` maps lowercase names (conjunction..opposition) to degrees
  - `orb_profile_default` provides per-planet max orbs (fallback 5.0)
  - `aspect_weights` provides per-aspect weight
- For each transit-target pair:
  1. Compute angular distance normalized to 0..180°
  2. Find closest canonical aspect within max orb
  3. Compute orb = |distance - aspect_angle|
  4. Compute strength = aspect_weight × max(0, 1 - orb/max_orb), clamped 0..1
  5. Polarity: supportive (trine/sextile), tense (square/opposition/semi), mixed (conjunction), neutral
  6. Phase/applying: compare current orb vs orb at target_jd + 0.1 days

### Lot Calculations (7 Hermetic lots)
- Day/night reversed formulas based on `www.twowander.com/blog/what-are-hermetic-lots-arabic-parts`:
  - FORTUNE: day=ASC+Moon-Sun, night=ASC+Sun-Moon
  - SPIRIT: day=ASC+Sun-Moon, night=ASC+Moon-Sun
  - EROS: day=ASC+Venus-Spirit, night=ASC+Spirit-Venus
  - NECESSITY: day=ASC+Fortune-Mercury, night=ASC+Mercury-Fortune
  - VICTORY: day=ASC+Jupiter-Spirit, night=ASC+Spirit-Jupiter
  - NEMESIS: day=ASC+Fortune-Saturn, night=ASC+Saturn-Fortune
  - MARRIAGE: non-reversing ASC+DSC-Venus
- Lot debug includes `formula` and `house`

### Stable IDs
- `t2n__MOON__OPPOSITION__PLUTO` (transit_to_natal)
- `t2a__SATURN__TRINE__MC` (transit_to_angle)
- `t2l__VENUS__TRINE__FORTUNE` (transit_to_lot)
- `tih__MARS__12` (transit_planet_in_house)

### Basil Evidence
For Basil profile (1980-10-30 19:50 Monchegorsk, 2026-07-08 12:00):
- `Transit Moon opposition natal PLUTO, orb 1.0454°` ✓ (angular distance 178.95°, orb 1.045°)

### Techniques Handling
- Empty `techniques` defaults to all four supported transit techniques
- Unsupported W3+ techniques produce `unsupported_technique_deferred:<name>` warnings
- All evidence strings include frames (transit, natal, angle, lot)

## TodayService NOT Wired
```python
# apps/api/app/services/today_service.py:245
sidecar_activation_layer=None,  # Can be wired in W3+ when sidecar endpoint is ready
```

## Verification Results

| Gate | Result |
|------|--------|
| `pytest test_activation_transits test_activation_layer_endpoint test_activation_schema -q` (sidecar) | 17 passed, 1 warning |
| `pytest tests/ -q` (sidecar full suite) | 38 passed, 1 warning |
| `pytest test_activation_layer_transits test_activation_layer_contract test_today_meta_versions -q` (API) | 15 passed |
| `pytest tests/ -q` (API full suite) | 682 passed, 5 skipped, 1 warning |
| `scripts/audit_sidecar_activation.py` — artifact written | 111 activations, all 4 indices populated |
| `git diff --exit-code -- artifacts/audit/2026-07-08/17_sidecar_activation_layer.json` | clean (exit 0) |
| `rg 'Transit Moon opposition natal Pluto'` in artifact | found ✓ |
| `rg 'annual_profection|firdar_major|solar_return'` in artifact | no matches ✓ |
| `git diff --check` (whitespace) | clean (exit 0) |
| `git show --check HEAD` | clean (exit 0) |

## Commit

`<will be filled>`

## Push Status

`NOT_ATTEMPTED`
