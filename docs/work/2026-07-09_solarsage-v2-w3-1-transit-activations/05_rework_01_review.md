# Architect Review: Wave W3.1 Rework 01

Status: REWORK REQUIRED

Reviewed commit:

- `b345a5b` — W3.1 Rework 01: stabilize transit activations

## Summary

The runtime blockers from the first review are resolved:

- root `python3 scripts/audit_sidecar_activation.py ...` works;
- audit artifact is deterministic across `PYTHONHASHSEED=random`;
- Basil `t2n__MOON__OPPOSITION__PLUTO` is now `phase="separating"` and `applying=false`;
- evidence uses `Transit Moon opposition natal Pluto`, while canonical keys remain uppercase;
- TodayService is still not wired to `sidecar_activation_layer`.

Fresh architect verification:

```text
sidecar targeted: 20 passed, 1 warning
sidecar full:     41 passed, 1 warning
API targeted:     27 passed, 1 skipped
API full:         682 passed, 5 skipped, 1 warning
hashseed audit:   deterministic_ok
artifact diff:    clean
```

W3.1 still cannot be accepted because two rework requirements are incomplete.

## Blocking Findings

### P1. Lot regression test still does not prove all seven audit lots

`03_rework_01_TZ.md` required replacing the tautology with real assertions that the Basil audit fixture exposes all seven lots:

```text
FORTUNE, SPIRIT, EROS, MARRIAGE, NECESSITY, VICTORY, NEMESIS
```

Current test in `apps/solarsage/tests/test_activation_transits.py` only proves at least one expected lot exists:

```python
common = lot_keys & expected_lots
assert len(common) >= 1
```

That still allows six missing lots to pass. The artifact currently has all seven lots, so this is a test-contract gap, not a runtime defect.

Required fix:

- Change the Basil `by_lot` test to assert exact/superset coverage of all seven expected lots.
- Keep the existing ref-validity assertion.
- The test must fail if any one of the seven audit lot keys disappears.

### P2. Rework report contains the wrong commit SHA

Actual reviewed `HEAD`:

```text
b345a5b
```

`04_rework_01_report.md` says:

```text
e72037c
```

The previous review explicitly required the report to contain the actual rework commit SHA. This is a traceability issue.

Required fix:

- Write a Rework 02 report with the actual Rework 02 commit SHA after committing.
- Do not leave stale or placeholder SHAs.

### P2. Remove no-op uppercase evidence check

`apps/solarsage/tests/test_activation_transits.py` contains an uppercase-name loop that never fails:

```python
if word not in ("ASC", "MC", "DSC", "IC"):
    pass
```

This test block creates false confidence.

Required fix:

- Remove the no-op block or replace it with a real assertion.
- Keep the exact Basil Moon-Pluto evidence assertion.

## Evidence To Preserve

Do not regress:

- `python3 scripts/audit_sidecar_activation.py ...` root command;
- deterministic `PYTHONHASHSEED=random` audit output;
- `Transit Moon opposition natal Pluto, orb 1.0454°`;
- `phase="separating"` and `applying=false`;
- all seven `by_lot` keys in artifact;
- no unsupported W3+ techniques;
- `sidecar_activation_layer=None` in TodayService.

## Required Rework

See `06_rework_02_TZ.md`.
