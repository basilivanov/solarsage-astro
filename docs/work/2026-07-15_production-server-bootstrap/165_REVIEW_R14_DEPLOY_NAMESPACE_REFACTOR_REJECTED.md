# Review R14 — deployment namespace refactor rejected for correction

## Verdict

**REJECTED for acceptance pending a narrow correction.** The bulk move into `scripts/deploy/` is present and most moved suites are green, but the refactor currently has a real legacy-path regression, an incomplete layout contract, and no honest byte-identical transcript proof.

## Independent evidence

The following checks were run outside the coder session:

- `bash scripts/deploy/tests/test-prod-namespace-layout.sh` reports green.
- All moved shell scripts pass `bash -n`; moved Python files pass isolated `py_compile`.
- The release/authority focused suites remain green after the move.
- A temporary-tree mutation proof demonstrates that the current namespace test returns `0` when:
  - `README.md` contains arbitrary non-empty text but no inventory;
  - a stale old deployment path is placed under `scripts/deploy/legacy/`; and
  - a stale old deployment path is placed in an active documentation file.
- The raw two-run transcript differs in random `gen-*` identifiers, process IDs in expected signal diagnostics and outer run labels. Both runs are green, but raw output is not byte-identical.

## Blocking findings

### 1. Legacy relative-root regression

After moving the old operator tools to `scripts/deploy/legacy/`, these files still contain:

```bash
cd "$(dirname "$0")/.."
```

For the new location this resolves to `/opt/solarsage-astro/scripts/deploy`, not the repository root. `backup.sh`, `deploy.sh` and `db-create.sh` therefore read `.env`, compose files and other relative paths from the wrong directory.

The moved files also retain stale GRACE `owns:` paths such as `scripts/backup.sh`; the canonical source location must be reflected in the module contract.

### 2. Namespace contract false-green

The new layout test:

- excludes the complete `legacy/` subtree from stale-reference scanning;
- does not scan active `docs/` files;
- checks only that README is non-empty, not that it inventories the actual files; and
- does not list the new `test-prod-namespace-layout.sh` in the README inventory.

The temporary mutation proof above passes despite all three violations.

### 3. Determinism claim is not yet proven

The coder’s first and second 23-suite runs both returned `23/23`, but raw `diff` showed random generation IDs and PIDs. The final report must not call this byte-identical until either the harness transcript is made deterministic or a narrowly specified canonical transcript is compared and reported as such (with the raw volatile fields explicitly accounted for, not silently discarded).

## Non-blocking conditions retained

The backup/offsite/restore suites that fail before their verifier because `/etc/solarsage/env` is absent, and the root-only env suites, remain separately documented pre-existing/environment-gated blockers. They must not be changed as part of this path-only correction.

## Required next slice

Implement `166_TZ_R14_DEPLOY_NAMESPACE_REFACTOR_CORRECTION.md`, then stop for another independent review. Do not start promotion/rollback/GC integration and do not perform production actions.
