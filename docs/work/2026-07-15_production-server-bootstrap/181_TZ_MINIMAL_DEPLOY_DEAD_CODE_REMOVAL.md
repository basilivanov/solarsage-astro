# TZ — remove parked deployment runtime and exhaustive harnesses

## Read first

- `AGENTS.md`;
- `172_ARCH_MINIMAL_PRODUCTION_PATH_DECISION.md`;
- `173_TZ_MINIMAL_COMPOSE_ORCHESTRATOR.md`;
- `180_REPORT_MINIMAL_HOST_RUNTIME_CONVERGENCE.md`;
- `docs/DEPLOYMENT.md` and `docs/PRODUCTION_RUNBOOK.md`;
- `scripts/deploy/README.md`.

## Objective

Delete deployment code and test harnesses that are definitely unreachable from
the accepted minimal Compose production path. This is a subtraction-only
cleanup. Do not create a replacement framework, compatibility shims, a new
matrix, a new generic validator, or a second orchestrator.

No production action is allowed: no `--apply`, install, service operation,
Docker/registry login or push, DB command, migration, commit, or push.

## Canonical keep roots

These are protected unless a reference-only edit is required by the cleanup:

- `.github/workflows/deploy-production.yml`;
- `.github/workflows/source-readiness.yml`;
- `infra/production/docker-compose.app.yml`;
- `infra/production/docker-compose.yml`;
- `infra/production/solarsage-github-deploy`;
- `infra/production/solarsage-deploy.sudoers`;
- `infra/production/tmpfiles.d/solarsage.conf`;
- `infra/systemd/solarsage-db.service`;
- `infra/systemd/solarsage-backup.service`;
- `infra/systemd/solarsage-backup.timer`;
- active Nginx/Certbot/Fail2ban/SSH templates;
- `scripts/deploy/prod-orchestrator.sh`;
- `scripts/deploy/prod-host-prepare.sh`;
- `scripts/deploy/prod-os-bootstrap.sh`;
- `scripts/deploy/prod-cert-prepare.sh`;
- `scripts/deploy/prod-github-access.sh`;
- `scripts/deploy/prod-infra-fingerprint.sh`;
- `scripts/deploy/check_prod_guard.sh`;
- `scripts/deploy/lib/prod-path-transaction.sh`;
- focused tests that directly prove the kept runtime/security boundary.

The installed host may still contain old app systemd units before the one-time
cutover. Cleanup may keep disable-by-name logic, but the repository must not
install or fingerprint obsolete unit templates merely to disable already
installed units.

## Definitely parked candidates

Prove references before deleting, then remove the whole parked slice rather
than leave orphan helpers/tests:

- `scripts/deploy/legacy/`;
- unfinished R14 release/promotion/authority runtime and helpers;
- old profile/env generation runtime and helpers;
- old offsite/maintenance/backup/restore entrypoints replaced by the canonical
  orchestrator;
- `scripts/deploy/tests/run-deploy-matrix.sh`;
- exhaustive tests owned only by deleted R14/profile/offsite/maintenance code;
- stale one-job deploy workflow validator and its deploy mutation harness;
- generated `__pycache__` files under `scripts/deploy/`;
- parked backup-maintenance systemd templates;
- obsolete app/preview systemd templates if the active minimal path only needs
  to disable their installed names and no active non-deploy consumer requires
  the repository templates.

Candidate names are not authorization by themselves. For every kept/deleted
decision, use `rg` over active workflows, infra, scripts, `AGENTS.md`,
`docs/DEPLOYMENT.md`, and `docs/PRODUCTION_RUNBOOK.md` (exclude historical
`docs/work/**` when deciding runtime reachability).

## Phase A — manifest before deletion

Before editing, produce a compact manifest with:

1. exact files to keep and why;
2. exact files to delete and their last active references;
3. active files that must be edited to remove parked references;
4. focused tests retained after cleanup;
5. line-count before/expected after;
6. any uncertain file — uncertain means KEEP and report, never guess-delete.

Stop and wait for reviewer approval after Phase A. Do not delete in Phase A.

## Phase B — implementation after explicit continuation

After approval:

1. delete the accepted manifest only;
2. remove parked files from host-prepare install/verify/fingerprint lists;
3. retain disable-by-name safety for old installed app services until the
   owner's one-time cutover, without reinstalling their templates;
4. update `AGENTS.md`, `scripts/deploy/README.md`, active deployment docs and
   focused tests to describe Compose as canonical and remove dead paths;
5. do not preserve compatibility launchers for deleted code;
6. ensure no active file references a deleted path;
7. write `182_REPORT_MINIMAL_DEPLOY_DEAD_CODE_REMOVAL.md` with exact deletions,
   before/after LOC and direct verification results.

## Required focused verification

- `git diff --check`;
- `bash -n` on every retained deployment shell script;
- YAML parse for both manual workflows;
- Compose config with a private temporary dummy env;
- `visudo -cf` for the deploy sudoers template;
- retained orchestrator harness twice, byte-identical;
- GitHub wrapper/access tests;
- host routing/namespace/path-transaction checks after their scope is reduced;
- focused API/sidecar health tests and frontend preview-isolation guard;
- an `rg` proof that no active workflow/infra/script/runbook references a
  deleted path.

The old exhaustive matrix and stale one-job deploy validator are not release
gates and must not be repaired or replaced.

## Stop condition

Source-only cleanup and verification complete, report written, tmux session
left alive. Production launch remains manual and requires a separate owner
command.
