# TZ: SolarSage guardrails unification

## Goal

Make SolarSage guardrails the source of truth for target-repo mechanical checks.

GRACE orchestrator must be able to call stable target-repo commands without knowing internal lint commands. SolarSage owns the actual scripts because the scripts validate SolarSage code and conventions.

## Scope

Repository: `basilivanov/solarsage-astro`.

Files expected to change:

- `scripts/grace_lint.py`
- `scripts/test_grace_lint.py`
- `scripts/grace_front_lint.py` new
- `scripts/grace/check-markers.sh`
- `scripts/grace/check-negative.sh`
- `scripts/guardrails.sh`
- optionally docs under `docs/work/`

Do not change product runtime code unless a test fixture absolutely requires it.

## Current problems

1. Backend GRACE lint exists only for Python contract markers.
2. Backend GRACE lint does not enforce file/function size limits.
3. Frontend GRACE marker gate is bash-only and weaker than backend `grace_lint.py`.
4. `check_horary_quality.sh` is domain-specific but currently runs inside universal frontend guardrails.
5. Guardrails expose project-area commands, but not a clean `fast / normal / strict` interface.

## Required architecture

Target repo exposes stable commands:

```bash
bash scripts/guardrails.sh fast
bash scripts/guardrails.sh normal
bash scripts/guardrails.sh strict
```

Legacy area commands may remain:

```bash
bash scripts/guardrails.sh frontend
bash scripts/guardrails.sh backend
bash scripts/guardrails.sh full
bash scripts/guardrails.sh domain
```

GRACE orchestrator will call these stable target-repo commands. It must not import or duplicate SolarSage lint internals.

## Backend GRACE lint

Update `scripts/grace_lint.py`.

Existing rule codes must remain stable:

- `GRC000`: Python syntax error.
- `GRC001`: missing `AI_HEADER`.
- `GRC002`: module contract pairing mismatch.
- `GRC003`: module map pairing mismatch.
- `GRC004`: block pairing mismatch.
- `GRC010`: public function missing function contract.
- `GRC011`: function contract missing required fields.
- `GRC020`: missing module contract block.
- `GRC021`: missing module map block.
- `GRC999`: file read error.

Add new rules:

### `GRC030`: file too long

A checked file must be at most 1000 physical lines.

Failure message should include actual line count and max limit.

### `GRC031`: function too large

Every Python `def` / `async def` must be at most 4000 dependency-free lexical tokens.

Use stdlib-only implementation. A simple regex token counter is acceptable for MVP. No external tokenizer dependency.

Failure message should include function name, actual token count, and max limit.

## Backend GRACE lint self-tests

Update `scripts/test_grace_lint.py`.

Add tests for:

- file with 1001 lines fails with `GRC030`;
- file with 1000 lines does not fail with `GRC030`;
- oversized function fails with `GRC031`;
- normal function does not fail with `GRC031`;
- existing tests for `GRC001/GRC002/GRC003/GRC004/GRC010/GRC011/GRC020/GRC021` keep passing.

## Frontend GRACE lint

Create `scripts/grace_front_lint.py`.

It must be Python stdlib-only.

Default input source:

```text
grace/frontend.paths
```

It should expand the globs from repo root and check `.ts`, `.tsx`, `.js`, `.jsx` files.

Frontend rule codes should match backend where semantically equivalent:

- `GRC001`: missing `AI_HEADER`.
- `GRC002`: `START_MODULE_CONTRACT` / `END_MODULE_CONTRACT` mismatch.
- `GRC003`: `START_MODULE_MAP` / `END_MODULE_MAP` mismatch.
- `GRC004`: `START_BLOCK` / `END_BLOCK` mismatch by block name.
- `GRC030`: file has more than 1000 physical lines.
- `GRC031`: frontend function/component-like block has more than 4000 lexical tokens.
- `GRC999`: file read error.

For `GRC031`, MVP should detect at least:

- `function Name(...) { ... }`
- `export function Name(...) { ... }`
- `export default function Name(...) { ... }`
- `const Name = (...) => { ... }`
- `export const Name = (...) => { ... }`

A brace-depth scanner is enough for MVP. Do not add TypeScript parser dependencies.

## Compatibility wrapper

Keep `scripts/grace/check-markers.sh` for backward compatibility, but turn it into a wrapper:

```bash
#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
python3 "$ROOT/scripts/grace_front_lint.py"
```

Existing callers must continue to work.

## Negative tests

Update `scripts/grace/check-negative.sh`.

It must verify that frontend gates really fail for broken cases:

- remove `AI_HEADER` -> frontend lint fails with `GRC001` or non-zero exit;
- remove `END_BLOCK` -> frontend lint fails with `GRC004` or non-zero exit;
- create checked frontend file over 1000 lines -> frontend lint fails with `GRC030`;
- create checked frontend function/component over 4000 tokens -> frontend lint fails with `GRC031`;
- keep existing ESLint negative cases if they still reflect real frontend policy.

The script must operate in a temp copy and never dirty the real worktree.

## Guardrails interface

Update `scripts/guardrails.sh`.

### Universal commands

`frontend` should run only universal frontend checks:

```bash
pnpm exec eslint .
pnpm exec tsc --noEmit
python3 scripts/grace_front_lint.py
bash scripts/grace/check-negative.sh
```

`backend` should keep:

```bash
python -m unittest scripts/test_grace_lint.py -v
ruff check .
mypy app
alembic sqlite round-trip
pytest -q
```

`backend-grace` should run:

```bash
python -m unittest scripts/test_grace_lint.py -v
python scripts/grace_lint.py apps/api/app
```

`domain` should run domain-specific guards, initially:

```bash
bash scripts/check_horary_quality.sh
```

`full` should run:

```text
docs + secrets + orchestrator + contracts + backend + frontend + domain + prod
```

`strict` should run:

```text
full + backend-grace + logging guardrails
```

### New profiles

Add:

```bash
bash scripts/guardrails.sh fast
bash scripts/guardrails.sh normal
bash scripts/guardrails.sh strict
```

Expected mapping for SolarSage:

- `fast`: cheap mechanical checks only. Must include frontend/backend GRACE lint when relevant or safe to run globally.
- `normal`: `frontend` and/or `backend` level checks suitable for normal acceptance.
- `strict`: full merge gate.

For MVP, acceptable mapping:

```text
fast   -> frontend GRACE lint + backend GRACE lint self-tests/app lint where dependencies are available
normal -> frontend + backend
strict -> existing strict
```

If dependency availability makes backend expensive locally, document the fallback clearly in the script output.

## Acceptance criteria

These commands must pass:

```bash
python3 scripts/test_grace_lint.py
python3 scripts/grace_front_lint.py
bash scripts/grace/check-negative.sh
bash scripts/guardrails.sh frontend
bash scripts/guardrails.sh backend
bash scripts/guardrails.sh full
bash scripts/guardrails.sh strict
```

After implementation:

- backend `GRC030/GRC031` are enforced;
- frontend `GRC001/GRC002/GRC003/GRC004/GRC030/GRC031` are enforced;
- `check_horary_quality.sh` no longer runs as part of universal `frontend` alone;
- `check-markers.sh` remains available as a wrapper;
- guardrails expose `fast`, `normal`, `strict`;
- no product runtime code is changed unless justified in the report;
- final report includes commands run and pass/fail output snippets.

## Non-goals

- Do not add GitHub Actions.
- Do not add external parser/tokenizer dependencies.
- Do not move scripts into GRACE orchestrator runtime.
- Do not require architect/coder agents to know individual bash commands.
