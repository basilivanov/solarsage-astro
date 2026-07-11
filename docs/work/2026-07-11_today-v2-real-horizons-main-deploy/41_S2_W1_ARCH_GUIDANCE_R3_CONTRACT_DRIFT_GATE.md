# S2.W1 Architect Guidance R3 — contract drift gate before an intentional commit

Дата: 2026-07-12
Applies to: `39_S2_W1_ARCH_REVIEW_R1.md`, section 7.4.
Status: immediate clarification; no commit/push/staging.

## Problem

Current `scripts/contracts/check.sh` ends with:

```bash
git diff --exit-code -- \
  packages/contracts/openapi.json \
  packages/contracts/_generated.ts \
  packages/contracts/_generated.zod.ts
```

S2.W1 intentionally changes the committed default from `al-1.0` to `al-1.1`.
Therefore before the accepted commit these generated files must differ from
HEAD. At the same time this wave requires an empty index.

It is mathematically impossible for current `pnpm contracts:check` to return 0
in that state. Staging generated files only to hide the worktree diff is
forbidden and is not a valid proof.

## Correct pre-commit proof

Do not change `check.sh` in S2.W1. Stage A owns that workflow improvement.

Before S2.W1 callback run:

```bash
pnpm contracts:generate
sha256sum \
  packages/contracts/openapi.json \
  packages/contracts/_generated.ts \
  packages/contracts/_generated.zod.ts \
  > /tmp/s2w1-contracts-first.sha256

pnpm contracts:generate
sha256sum \
  packages/contracts/openapi.json \
  packages/contracts/_generated.ts \
  packages/contracts/_generated.zod.ts \
  > /tmp/s2w1-contracts-second.sha256

diff -u \
  /tmp/s2w1-contracts-first.sha256 \
  /tmp/s2w1-contracts-second.sha256

git diff --check -- \
  packages/contracts/openapi.json \
  packages/contracts/_generated.ts \
  packages/contracts/_generated.zod.ts

git diff -- \
  packages/contracts/openapi.json \
  packages/contracts/_generated.ts \
  packages/contracts/_generated.zod.ts

rm -f \
  /tmp/s2w1-contracts-first.sha256 \
  /tmp/s2w1-contracts-second.sha256
```

Acceptance before commit:

- both hash manifests identical;
- exact generated diff contains only expected `al-1.0 -> al-1.1` defaults;
- no timing fields are added/removed/redeclared;
- index empty;
- `pnpm contracts:check` exit 1 is reported as `EXPECTED_PRECOMMIT_DRIFT`, not
  represented as PASS.

## Post-commit proof

After architect accepts S2.W1 and separately authorizes the scoped commit:

```bash
pnpm contracts:check
```

must return 0 from a clean worktree. If it does not, commit/push acceptance is
revoked until fixed.

## Callback replacement

Replace only the pre-commit `contract_tests` line with:

```text
contract_generation_idempotent: PASS <three hashes>
generated_diff: EXPECTED al-1.0 -> al-1.1 only
contracts_check_precommit: EXPECTED_PRECOMMIT_DRIFT
index: EMPTY
```

Existing Vitest runtime contract tests and TypeScript typecheck remain mandatory.
