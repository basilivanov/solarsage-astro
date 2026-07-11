# solarsage-contracts

`solarsage-contracts` is a local-only Python distribution for shared SolarSage wire contracts. It is not published to PyPI.

This package owns calculation-evidence semantics for activation-layer payloads: fields, literal values, defaults, constraints, version constants, and index-reference validation.

Casing belongs to boundary wrappers:

- sidecar wrappers keep snake_case wire output;
- API wrappers keep public camelCase wire output.

Local editable install commands:

```bash
apps/api/.venv/bin/python -m pip install -e ./packages/py-contracts
apps/solarsage/venv/bin/python -m pip install -e ./packages/py-contracts
```

The package distribution version (`0.1.0`) is not a wire version. Wire versions remain `activation-layer.v1`, `al-1.1`, and `ss-calc-1.2.0`.
