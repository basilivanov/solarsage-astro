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

Contract workflow commands from the repository root:

```bash
pnpm contracts:sync
pnpm contracts:check
pnpm contracts:compat
```

- `pnpm contracts:sync` is the intentional update command: focused Python guards, deterministic generation, compatibility classification, contract Vitest, TypeScript typecheck, and generated diff summary.
- `pnpm contracts:check` is the deterministic CI/drift guard: focused Python guards, generation, fixture normalization, and generated artifact diff.
- `pnpm contracts:compat` runs only the OpenAPI compatibility checker.
- `CONTRACT_BASE_REF` can override the compatibility base ref; otherwise the checker uses `git merge-base HEAD origin/main`.

CI does not enable automatic breaking-contract override. Any breaking change requires reviewed follow-up outside the default CI path.
