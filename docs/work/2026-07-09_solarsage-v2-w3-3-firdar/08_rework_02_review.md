# Architect Review — W3.3 Rework 02

Status: REWORK REQUIRED
Branch: main
Reviewed commits:
- 11574e6 W3.3 Rework 02: fixture/GRACE/test-discipline fixes
- fbf965d docs(w3.3): finalize rework 02 report with sha 11574e6

## Verification Performed

```text
cd apps/solarsage && venv/bin/python -m pytest tests/test_firdar.py tests/test_activation_layer_endpoint.py tests/test_activation_transits.py tests/test_activation_schema.py tests/test_profections.py -q
66 passed, 1 warning
```

```text
cd apps/api && source .venv/bin/activate && python -m pytest tests/test_activation_layer_firdar.py tests/test_activation_layer_profections.py tests/test_activation_layer_transits.py tests/test_activation_layer_contract.py tests/test_today_meta_versions.py -q
23 passed
```

Targeted tests pass, but the rework does not yet satisfy all Rework 02 requirements.

## Findings

### P1 — Single activation-rules load proof is too weak

`apps/solarsage/tests/test_firdar.py::test_activation_rules_loaded_once_firdar` makes two requests and asserts `load_count <= 2`.

That does not prove the required contract: exactly one `_load_activation_rules()` call for one request with `["firdar_major", "firdar_minor"]`.

The test should make one focused request and assert `load_count == 1` immediately after that request. If a second request is kept, assert `load_count == 2` after it.

### P1 — Missing exact KeyError tests for `firdar_major` and `firdar_minor`

Rework 02 required focused tests proving missing `firdar_major` or `firdar_minor` strength keys still raise `KeyError`.

Current `test_strength_strict_lookup` only checks `nonexistent_technique` against the real rules. It does not simulate the two actual required missing-key cases:

- `period_strengths.firdar_major` removed
- `period_strengths.firdar_minor` removed

### P1 — `firdar.py` module contract is still inaccurate

`apps/solarsage/solarsage/services/firdar.py` still says:

```text
unknown sign/strength keys raise clear errors
```

`firdar.py` does not own sign normalization or activation-rule strength lookup. This was explicitly called out in Rework 02.

The failure policy also claims canon sequence sum mismatches raise, but the current implementation does not validate that invariant. Either make that invariant true with explicit validation and tests, or remove the false statement from the contract. Architecturally, explicit canon validation is preferred because silent fallback can hide a malformed period canon.

### P2 — `FirdarContext.__init__` function contract placement is imprecise

The `FirdarContext.__init__` function contract is currently attached at class scope before `def __init__`. Move it directly above or inside the method so the contract clearly belongs to the function. Include a `returns: None` line to match the local contract style.

## Decision

Do a narrow Rework 03. Do not change normal Firdar results, accepted sequences, TodayService wiring, scoring v2, or deployment state.
