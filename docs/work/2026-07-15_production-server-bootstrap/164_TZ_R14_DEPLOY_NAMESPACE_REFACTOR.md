# TZ R14 — consolidate the deployment surface under `scripts/deploy/`

## Context

The production-readiness work has accumulated a large but coherent deployment surface across `scripts/prod-*.sh`, `scripts/prod-*.py`, `scripts/lib/prod-*`, `scripts/tests/test-prod-*`, infrastructure files and runbook references. The current release-authority helper and harness are now security-reviewed, so this is the safe point for a path-only refactor before promotion/rollback/GC integration.

The user explicitly requires that everything related to deployment live in one namespace: `scripts/deploy/`. This task is a repository refactor, not a production rollout.

## Goal

Move the canonical deployment/host-preparation/release/backup/restore/health/operator code and its tests into `scripts/deploy/`, preserving behavior, public contracts, exact test oracles and the manual-only production gate.

Use a simple, discoverable layout:

```text
scripts/deploy/
  README.md                         # inventory and compatibility map
  prod-*.sh                         # canonical production entrypoints
  prod-release-authority.py         # source of the installed root helper
  legacy/                           # old compose/bootstrap/operator tools, if still supported
  lib/
    prod-*
  tests/
    test-prod-*
    lib/
```

Keep names stable inside the new namespace unless a collision makes a rename necessary. The README must classify every moved file and every intentionally unmoved `scripts/*` file.

## Scope inventory

The canonical production surface currently includes:

- `scripts/prod-*.sh` and `scripts/prod-release-authority.py`;
- `scripts/lib/prod-*`;
- `scripts/tests/test-prod-*` and `scripts/tests/lib/prod_*`;
- `scripts/check_prod_guard.sh`;
- deployment/operations helpers currently at `scripts/deploy.sh`, `scripts/bootstrap-vds.sh`, `scripts/backup.sh`, `scripts/db-create.sh`, `scripts/health-check.sh`, `scripts/health-check-with-alert.sh`, `scripts/alert.sh` and `scripts/dashboard.sh`.

Place the last group under `scripts/deploy/legacy/` or `scripts/deploy/ops/` with a documented status if they are still supported. Do not silently delete them. Domain audits, contracts, Grace tooling, preview tooling and Telegram test-data generation are not deployment implementations; leave them outside and record the reason in the README.

## Required compatibility and boundary rules

1. The canonical implementation and test source must be under `scripts/deploy/`. Update all repository references in workflows, infra units, runbooks, release builders, source-readiness checks and other scripts.
2. If an old path is consumed by an external contract that cannot be changed in this slice, leave only a tiny compatibility launcher at that old path which `exec`s the canonical file under `scripts/deploy/`. It must contain no deployment logic and be listed in the README. Prefer updating the contract and removing the old implementation when safe.
3. The installed privileged helper path remains `/usr/local/libexec/solarsage/release-authority`; this task must not install it. The source helper becomes `scripts/deploy/prod-release-authority.py`. Do not make the installed helper import mutable checkout modules at runtime. If code is split internally, keep the installed artifact self-contained or define a future bundling/install step without executing it now.
4. The manifest source becomes `scripts/deploy/lib/prod-release-manifest.py`; all builder, pinning and authority harness references must follow it.
5. Update relative-root discovery correctly for the extra directory depth. No command may accidentally resolve the repository as `scripts/` or a test temporary directory.
6. Preserve the exact canonical production ports, Telegram HMAC-only production auth, manual-only production launch, and all no-production-action constraints from `AGENTS.md`.
7. Preserve GRACE headers/contracts. New `README.md`, launchers and modules need the repository’s required module contract/map comments where applicable.

## Test and anti-regression requirements

Add a focused namespace/layout contract check that fails if a canonical deployment implementation remains outside `scripts/deploy/`, except for explicitly listed compatibility launchers. It must also reject stale references to the old implementation paths and double-prefixed paths.

Update the moved harnesses without weakening them:

- exact substitution counts and execution ledgers remain strict;
- temporary fixtures never touch real `/opt`, `/run`, Git, systemd, nginx or database paths;
- authority, build, pinning, promotion and pointer suites keep their existing case counts and mutation proofs;
- all changed focused suites run twice and produce byte-identical output;
- `bash -n` and isolated Python compilation cover the new paths;
- source-readiness/workflow structural checks and any tests that reference old paths are updated and green.

At minimum run:

```bash
bash -n scripts/deploy/**/*.sh scripts/deploy/*.sh
python3.12 -I -S -m py_compile scripts/deploy/prod-release-authority.py scripts/deploy/lib/prod-release-manifest.py
timeout 240 bash scripts/deploy/tests/test-prod-release-authority.sh
timeout 240 bash scripts/deploy/tests/test-prod-release-build.sh
timeout 240 bash scripts/deploy/tests/test-prod-release-pinning.sh
timeout 240 bash scripts/deploy/tests/test-prod-release-promotion.sh
timeout 240 bash scripts/deploy/tests/test-prod-release-pointer-contract.sh
```

Use the actual moved-file list rather than relying on a shell glob that can be empty. Run each changed focused suite twice, compare outputs byte-for-byte, then run the repository’s source-readiness/guard suites that reference deployment paths.

## Acceptance checklist

- [ ] `scripts/deploy/` contains the complete canonical deployment surface and a truthful inventory README.
- [ ] No production behavior changed; only paths, root calculations, imports/references and compatibility launchers changed.
- [ ] All internal, workflow, infra, systemd and documentation references use the canonical namespace or a documented shim.
- [ ] Installed-helper source boundary remains self-contained and uninstalled.
- [ ] Namespace/layout contract and all existing security/mutation suites are green twice and deterministic.
- [ ] No real production action, service restart, config installation, database operation, Git mutation, commit or push occurred.
- [ ] Stop for independent review before adding promotion/rollback/GC integration.
