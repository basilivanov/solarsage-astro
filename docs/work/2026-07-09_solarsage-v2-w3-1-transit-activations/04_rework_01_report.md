# Rework 01 Report — Wave W3.1 Transit Activations

## Summary

Fixed all P0 blockers and P1/P2 issues from `02_arch_review.md` without expanding beyond transit-family activation extraction.

## Changed Files

| File | Change |
|------|--------|
| `apps/solarsage/solarsage/services/activation_builder.py` | Fixed: deterministic ordering (ordered tuple), applying/separating (orb comparison), evidence display (human-readable names) |
| `apps/solarsage/tests/test_activation_layer_endpoint.py` | Renamed `BASIL_REQUEST` → `MOSCOW_FIXTURE_REQUEST`, added real `BASIL_AUDIT_REQUEST`, added Moon-Pluto test with separating/applying assertions |
| `apps/solarsage/tests/test_activation_transits.py` | Renamed fixtures, added determinism test, Basil Moon-Pluto regression test, strengthened lot assertions, removed tautologies |
| `scripts/audit_sidecar_activation.py` | Self-reexec into sidecar venv when invoked by system `python3` |
| `artifacts/audit/2026-07-08/17_sidecar_activation_layer.json` | Regenerated with fixes |

## Fixes

### P0: Audit script not runnable from repo root
- Script now detects when `swisseph` is unavailable and re-execs into `apps/solarsage/venv/bin/python` with correct `PYTHONPATH`.
- Command `python3 scripts/audit_sidecar_activation.py ...` works from repo root.

### P0: Non-deterministic default technique ordering
- Replaced `W3_1_SUPPORTED = {...}` set with `W3_1_SUPPORTED_ORDER = (...) ` ordered tuple.
- `ALL_TECHNIQUES = list(W3_1_SUPPORTED_ORDER)` — iteration order is hashseed-independent.
- Added `test_default_activation_order_deterministic` test.
- Hashseed verification: 3 runs with `PYTHONHASHSEED=random` produce identical sha256sums.

### P0: Phase/applying used raw angular distance instead of orb
- Now computes `current_orb = abs(adist - aspect_angle)` and `probe_orb = abs(probe_adist - aspect_angle)`.
- Compares probe_orb vs current_orb to determine applying/separating.
- Basil Moon-Pluto (2026-07-08 12:00 Europe/Moscow): `phase=separating`, `applying=false`.

### P1: Evidence used uppercase planet names
- Added `_DISPLAY_NAMES` map and `_display_name()` helper.
- Evidence now reads `"Transit Moon opposition natal Pluto, orb 1.0454°"` (not `"natal PLUTO"`).
- `target_key` remains uppercase (`"PLUTO"`), `by_planet["PLUTO"]` unchanged.

### P1: Tests used wrong fixture data
- Renamed `BASIL_REQUEST` → `MOSCOW_FIXTURE_REQUEST`.
- Added `BASIL_AUDIT_REQUEST` with real Basil birth data (1980-10-30 19:50 Monchegorsk).
- Added `test_basil_moon_opposition_pluto` proving:
  - evidence: `Transit Moon opposition natal Pluto`
  - orb within `0.05°` of `1.0454`
  - `phase = "separating"`, `applying = false`
- Replaced tautology `assert len(total_lot_refs) >= 0` with real assertions on `by_lot`.

### P2: Agent report had unfilled commit placeholder
- Filled in report with actual commit SHA.

## Basil Moon-Pluto Evidence

For Basil profile (1980-10-30 19:50, 67.9394/32.8144, Europe/Moscow, target 2026-07-08 12:00):
- Activation ID: `t2n__MOON__OPPOSITION__PLUTO`
- Evidence: `Transit Moon opposition natal Pluto, orb 1.0454°`
- Orb: `1.0454` (within 0.05° of expected)
- Phase: `separating`
- Applying: `false`
- Strength: `0.7514`

## Verification Results

| Gate | Result |
|------|--------|
| `pytest tests/ -q` (sidecar full suite) | 41 passed, 1 warning |
| `pytest test_activation_layer_transits test_activation_layer_contract test_today_meta_versions -q` (API) | 15 passed |
| `python3 scripts/audit_sidecar_activation.py` from repo root | Works ✓ |
| `PYTHONHASHSEED=random` + `sha256sum` × 3 | All identical ✓ |
| `git diff --exit-code -- artifacts/audit/2026-07-08/17_sidecar_activation_layer.json` | clean after regenerate |
| `rg 'Transit Moon opposition natal Pluto'` in artifact | Found ✓ |
| `rg 'natal PLUTO'` in artifact | No matches ✓ |
| `rg 'sidecar_activation_layer=None' today_service.py` | Still None ✓ |
| `git diff --check` (whitespace) | clean (exit 0) |

## Commit

`e72037c`

## Push Status

`NOT_ATTEMPTED`
