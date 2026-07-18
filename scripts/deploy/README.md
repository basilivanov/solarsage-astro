# ############################################################################
# AI_HEADER: MODULE_DEPLOY_README — Canonical deployment namespace inventory
# ROLE: Single source of truth for deployment file locations after the 181 cleanup.
# DEPENDENCIES: none
# GRACE_ANCHORS: [DEPLOY_NAMESPACE, COMPATIBILITY_MAP]
# ############################################################################

# START_MODULE_CONTRACT: M-DEPLOY-README
# purpose: Inventory and compatibility map for the scripts/deploy/ namespace.
# owns:
#   - scripts/deploy/README.md
# inputs: none
# outputs: Documentation of canonical paths and retained test harnesses.
# dependencies: none
# side_effects: none
# emitted_logs: none
# invariants:
#   - Every canonical deployment file is listed exactly once.
#   - The canonical production path is the minimal Compose path
#     (docs/work/2026-07-15_production-server-bootstrap/172_ARCH_MINIMAL_PRODUCTION_PATH_DECISION.md).
# failure_policy: none (documentation only)
# END_MODULE_CONTRACT: M-DEPLOY-README

# START_MODULE_MAP: M-DEPLOY-README
# public_entrypoints:
#   - README (this file)
# semantic_blocks:
#   - DEPLOY_NAMESPACE: layout and canonical inventory
#   - COMPATIBILITY_MAP: origin map and new files
# END_MODULE_MAP: M-DEPLOY-README

## Canonical production path

The canonical production path is the minimal Compose path: immutable per-SHA
OCI images + `infra/production/docker-compose.app.yml` + the sole orchestrator
`scripts/deploy/prod-orchestrator.sh` (installed as
`/usr/local/libexec/solarsage/prod-orchestrator`). The parked R14
promotion/GC runtime, the profile/env engine, the old backup/offsite
entrypoints, the legacy operator tools, the exhaustive matrix and the stale
workflow validator were removed in the 181 cleanup
(`docs/work/2026-07-15_production-server-bootstrap/181A_MANIFEST_DEAD_CODE_AUDIT.md`).

## Layout

```text
scripts/deploy/
  README.md                         # this inventory and compatibility map
  check_prod_guard.sh               # production environment safety guard
  prod-*.sh                         # canonical production entrypoints
  lib/
    prod-*                          # shared deployment libraries
  tests/
    test-prod-*                     # focused deployment harnesses
```

## Canonical inventory

Every canonical file under `scripts/deploy/` (excluding this README and generated caches) is listed exactly once below.

### Guard

  - `scripts/deploy/check_prod_guard.sh`

### Shared libraries

  - `scripts/deploy/lib/prod-path-transaction.sh`

### Production entrypoints

  - `scripts/deploy/prod-cert-prepare.sh`
  - `scripts/deploy/prod-github-access.sh`
  - `scripts/deploy/prod-host-prepare.sh`
  - `scripts/deploy/prod-infra-fingerprint.sh`
  - `scripts/deploy/prod-orchestrator.sh`
  - `scripts/deploy/prod-os-bootstrap.sh`

### Focused test harnesses

  - `scripts/deploy/tests/test-prod-backup-units.sh`
  - `scripts/deploy/tests/test-prod-github-access.sh`
  - `scripts/deploy/tests/test-prod-github-wrapper.sh`
  - `scripts/deploy/tests/test-prod-host-offsite-routing.sh`
  - `scripts/deploy/tests/test-prod-namespace-layout.sh`
  - `scripts/deploy/tests/test-prod-orchestrator.sh`
  - `scripts/deploy/tests/test-prod-path-transaction.sh`

## Compatibility map

Origin of the retained files and the files introduced after the namespace refactor. Coverage is mechanically validated by `tests/test-prod-namespace-layout.sh`.

### Category mappings (mechanically validated)

| Old path pattern | New canonical location | Coverage |
|------------------|------------------------|----------|
| `scripts/prod-<name>.sh` | `scripts/deploy/prod-<name>.sh` | every retained production shell entrypoint (`scripts/deploy/prod-*.sh`) |
| `scripts/lib/prod-<name>` | `scripts/deploy/lib/prod-<name>` | every retained shared library (`scripts/deploy/lib/prod-*`) |
| `scripts/tests/test-prod-<name>.sh` | `scripts/deploy/tests/test-prod-<name>.sh` | every retained focused test harness (`scripts/deploy/tests/test-prod-*.sh`) |

### Explicit old-path rows

| Old path | New canonical path | Status |
|----------|-------------------|--------|
| `scripts/check_prod_guard.sh` | `scripts/deploy/check_prod_guard.sh` | moved |

### New files after the namespace refactor (no old path)

These files were created after the namespace refactor; they intentionally have no old-path row.

  - `scripts/deploy/prod-orchestrator.sh` — sole minimal app deploy entrypoint (TZ 173)
  - `scripts/deploy/tests/test-prod-orchestrator.sh` — focused orchestrator contract harness
  - `scripts/deploy/tests/test-prod-namespace-layout.sh` — namespace/layout contract

## Boundary rules

1. The installed privileged entrypoint path is `/usr/local/libexec/solarsage/prod-orchestrator` (root:root `0755`); this namespace does not install it — host preparation does.
2. All production behavior, canonical ports, Telegram HMAC-only auth, manual-only launch gates, and `AGENTS.md` constraints are preserved.
3. No production action, service restart, config installation, database operation, Git mutation, commit, or push is performed by this namespace.
4. The removed parked slice (R14 promotion/GC, profile/env engine, old backup/offsite entrypoints, legacy operator tools, exhaustive matrix, stale workflow validator) is documented in `181A_MANIFEST_DEAD_CODE_AUDIT.md`; do not recreate it.
