# TZ R14 — deployment namespace refactor correction

Read review 165 and the original namespace TZ 164 in full. Correct only the refactor findings; do not broaden scope or alter production behavior.

## Required corrections

### Legacy tools

1. Fix repository-root discovery in `scripts/deploy/legacy/backup.sh`, `deploy.sh` and `db-create.sh` so invocation from any cwd resolves the repository root at the new depth before reading `.env` or compose files.
2. Update the GRACE/module `owns:` path in every moved legacy file to its canonical `scripts/deploy/legacy/...` path. Do not leave stale old implementation paths in active source comments.
3. Add a focused static/layout assertion for these three root calculations so a future move cannot silently regress them. Do not execute Docker, PostgreSQL, Redis or a real deployment.

### Honest namespace contract

Strengthen `scripts/deploy/tests/test-prod-namespace-layout.sh`:

- scan `scripts/deploy/legacy/` too; exclude only the contract test itself, README, and generated `__pycache__` files;
- scan active docs (`docs/*.md` and explicitly `docs/PRODUCTION_RUNBOOK.md`, `docs/DEPLOYMENT.md`, `docs/monitoring-setup.md`) in addition to workflows, infra and scripts; historical `docs/work/**` may remain historical and must be documented as excluded;
- keep the old-path and double-prefix checks binary-safe and fail closed;
- validate the README inventory, not merely its existence. Use a deterministic full-relative-path list: every canonical file under `scripts/deploy/` (excluding README and generated caches) must appear exactly once in the inventory, including `tests/test-prod-namespace-layout.sh`; every listed path must exist; and the legacy/compatibility section must match the actual old-to-new map;
- add a mutation proof in the harness: remove one inventory row or inject a stale legacy/docs path in a temporary copy and require the contract test to fail.

Use fixed patterns/allowlists so the contract does not match its own explanatory strings. Do not solve self-matches by excluding an entire deployment subtree.

### Deterministic verification transcript

Keep the 23-suite green matrix and run it twice. Make the acceptance transcript honest and deterministic without changing production logic or weakening test assertions:

- capture each suite’s exit code and complete output;
- compare a documented canonical transcript produced by a narrow normalization function that only replaces known volatile fields (`gen-[0-9a-f]{32}`, PIDs on the exact expected `Hangup` diagnostic lines, and the outer run label); do not strip arbitrary lines or failures;
- separately report whether raw transcripts were identical and list any normalized fields;
- require the canonical transcripts and per-suite exit statuses to be byte-identical across runs;
- keep the five release/authority suites and syntax/isolated-Python checks as direct, unnormalized checks too.

If it is possible to make the existing test output deterministic without changing a production contract, prefer that; otherwise the explicit canonicalization plus raw-diff report is required. Do not call raw output byte-identical when it is not.

## Verification

Run independently and twice where applicable:

```bash
bash -n scripts/deploy/**/*.sh scripts/deploy/*.sh
python3.12 -I -S -m py_compile scripts/deploy/prod-release-authority.py scripts/deploy/lib/prod-release-manifest.py
bash scripts/deploy/tests/test-prod-namespace-layout.sh
bash scripts/deploy/tests/test-prod-release-authority.sh
bash scripts/deploy/tests/test-prod-release-build.sh
bash scripts/deploy/tests/test-prod-release-pinning.sh
bash scripts/deploy/tests/test-prod-release-promotion.sh
bash scripts/deploy/tests/test-prod-release-pointer-contract.sh
```

Then run the relevant moved smoke matrix twice with the deterministic transcript contract. Keep `/etc/solarsage/env` and root-only blockers explicitly outside the green claim.

No real `/opt` runtime, `/run`, service, nginx, database, Git registry, sudoers install, commit, push, reset or checkout action is authorized. Stop for independent review when complete.
