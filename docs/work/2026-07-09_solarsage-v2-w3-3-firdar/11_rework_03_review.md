# Architect Review — W3.3 Rework 03

Status: REWORK REQUIRED
Branch: main
Reviewed commits:
- cf3c2df W3.3 Rework 03: close test/contract gaps
- e544459 docs(w3.3): finalize rework 03 report with sha cf3c2df

## Verification Performed

```text
cd apps/solarsage && venv/bin/python -m pytest tests/test_firdar.py -q
40 passed, 1 warning
```

Manual malformed-canon check:

```text
minor_divisions=0 via calculate_firdar(canon=bad) -> ZeroDivisionError: float division by zero
day_sequence sum mismatch via calculate_firdar(canon=bad) -> NO ValueError, returned SUN 0.0..10.0
```

The new tests pass because they call `_validate_firdar_canon()` directly. They do not prove that the public calculation path validates caller-supplied `canon`.

## Findings

### P1 — `calculate_firdar(canon=...)` bypasses canon validation

`_load_firdar_canon()` now validates file-loaded canon, but `calculate_firdar()` accepts a pre-loaded `canon` parameter and uses it directly.

That contradicts the module contract and Rework 03 goal. A malformed caller-supplied canon still causes:

- `minor_divisions = 0` -> `ZeroDivisionError`;
- selected sequence sum mismatch -> silent fallback/result instead of `ValueError`.

Fix: validate the canon inside `calculate_firdar()` before using `cycle_years`, `minor_divisions`, or sequence data. It is acceptable if file-loaded canon is validated twice; correctness is more important than avoiding a tiny validation pass.

### P1 — `calculate_firdar` contract still mentions strength keys

`apps/solarsage/solarsage/services/firdar.py` still contains:

```text
error_behavior: KeyError on missing canon keys or strength keys
```

Firdar calculation does not own activation-rule strength lookup. Remove `strength keys` from this function contract.

### P2 — Function-contract placement is still awkward

`FirdarContext.__init__` contract is inside the argument list before `self`. Move it to a normal location:

- immediately above `def __init__`, or
- inside the method body immediately after the signature.

Keep `returns: None`.

### P3 — Minor cleanup

`_validate_firdar_canon()` imports `math` but does not use it. The test helper imports `_load_firdar_canon` but does not use it. Remove both.

## Decision

Do a narrow Rework 04. Normal Firdar results and accepted audit artifact must not change.
