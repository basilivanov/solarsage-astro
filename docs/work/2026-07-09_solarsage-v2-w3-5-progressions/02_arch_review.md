# Architect Review — W3.5 Progressions

Status: REWORK REQUIRED

Reviewed range: `eadd92b..6d8dfe8`
Implementation commit: `887228c`
Report commit: `6d8dfe8`

## Findings

### P0 — Secondary progression strength uses the wrong base

Evidence:
- `apps/solarsage/solarsage/services/progressions.py:535-536` computes every aspect strength with hardcoded `0.7`.
- `apps/solarsage/solarsage/services/activation_builder.py:1453-1502` loads `progressed_moon_aspect` base into debug, but uses `asp["strength"]` from the hardcoded helper.
- Artifact proof: `secondary_progression__MOON__SEMI_SEXTILE__NATAL_LOT_EROS` has `strength=0.6297`, `debug.base_strength=0.65`, `debug.orb_factor=0.8996`; expected strength is `round(0.65 * 0.8996, 4) == 0.5847`.

Impact:
- W3.5 scoring is mathematically inconsistent with its own debug data and the canon.
- Tests only prove that `_get_progression_strength()` can raise with a manually modified dict; they do not prove production strength uses that value.

Required fix:
- Compute strength from the exact canon base used by the activation kind:
  - `solar_arc_aspect`
  - `progressed_moon_aspect`
  - `progressed_sun_sign_transition`
  - `progressed_sun_house_transition`
- Add tests asserting `activation.strength == round(debug.base_strength * debug.orb_factor, 4)` for every W3.5 activation kind present in test output.

### P1 — Secondary progression orb is not read from its own canon key

Evidence:
- `apps/solarsage/solarsage/services/progressions.py:127-135` has `_get_progression_orb()` reading only `techniques.solar_arc.orb`.
- `calculate_secondary_progression_context()` also calls that same helper, so `techniques.secondary_progression.orb` can be missing or changed without affecting runtime.
- The TZ required both canon keys and loud failure when keys are missing/non-numeric.

Impact:
- The contract says solar arc and secondary progression have independent technique configuration, but runtime silently couples them.

Required fix:
- Replace the generic helper with strict per-technique lookup, for example `_get_progression_orb("solar_arc")` and `_get_progression_orb("secondary_progression")`.
- Fail loudly on missing/non-numeric values.
- Add tests for missing `solar_arc.orb` and missing `secondary_progression.orb`.

### P1 — Solar arc aspect debug misses required `source_longitude`

Evidence:
- TZ requires every aspect activation debug to include `source_longitude`, then solar arc debug additionally includes `solar_arc_source_longitude`.
- `apps/solarsage/solarsage/services/activation_builder.py:1409-1428` includes `solar_arc_source_longitude`, but not `source_longitude`.

Impact:
- API consumers cannot uniformly inspect aspect activation geometry across transit, solar arc, and secondary progression.

Required fix:
- Add `source_longitude` to every solar arc aspect activation debug.
- Add a test that checks the full aspect-debug field set for both solar arc and progressed Moon aspects.

### P1 — Sun transition contract is not fully tested and debug keys are partial

Evidence:
- TZ requires deterministic test coverage for progressed Sun transition code even if Basil has no transition.
- `apps/solarsage/tests/test_secondary_progressions.py` has no sign/house transition fixture.
- `apps/solarsage/solarsage/services/activation_builder.py:1537-1552` sign-transition debug omits `current_house` and `target_house`.
- `apps/solarsage/solarsage/services/activation_builder.py:1574-1588` house-transition debug omits `current_sign`, `previous_sign`, and `next_sign`.

Impact:
- The transition path can regress while all current W3.5 tests remain green.
- Consumers cannot rely on a stable transition debug shape.

Required fix:
- Emit all transition debug keys from the TZ, using `None` where not applicable.
- Add deterministic tests for sign transition and house transition.
- Include a wrap-around case for the Aries/Pisces boundary or make the code demonstrably correct there.

### P2 — Solar arc stable IDs use display-case source names

Evidence:
- TZ stable ID format uses `<SOURCE_PLANET>` and all existing activation IDs use uppercase canonical keys.
- `apps/solarsage/solarsage/services/activation_builder.py:1372-1389` uses `source_clean = asp["source_key"].capitalize()`.
- Artifact IDs are like `solar_arc__Mars__TRINE__NATAL_VENUS`, not `solar_arc__MARS__TRINE__NATAL_VENUS`.

Impact:
- IDs are less consistent with the rest of the activation layer and harder to join/group by canonical source key.

Required fix:
- Use uppercase canonical source keys in solar arc IDs.
- Keep evidence display names human-readable.
- Regenerate the W3.5 artifact after this change.

### P2 — Aspect map is duplicated instead of shared

Evidence:
- TZ says to use the existing canonical aspect map from `activation_builder.py`.
- `apps/solarsage/solarsage/services/progressions.py:58-68` duplicates `ASPECT_ANGLES` and `_classify_polarity()`.

Impact:
- Future canon/aspect changes can diverge between transit and progression paths.

Required fix:
- Reuse the existing activation-builder map/classification or extract a small shared helper without changing external contracts.
- Add a regression that progression aspect names/angles match the builder canonical map.

## Verification required after rework

Run and report:
- Sidecar targeted W3.1-W3.5 tests.
- Full sidecar pytest.
- API targeted activation-layer tests.
- Full API pytest.
- W3.5 audit artifact regeneration.
- Three random-hashseed audit regenerations with identical SHA.
- Explicit artifact assertion that each W3.5 activation has strength equal to `round(debug.base_strength * debug.orb_factor, 4)` when `debug.orb_factor` exists.
- `rg -n 'sidecar_activation_layer=None' apps/api/app/services/today_service.py`.
- `git diff 2f9173fbe9a9e20e97891e9789db6de57a2afaef..HEAD --check`.
- `git show --check HEAD`.
