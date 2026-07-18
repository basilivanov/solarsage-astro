# Phase A manifest — dead code reachability audit (TZ 181)

Read-only audit. Nothing deleted or edited. Reachability proven with `rg` over active surfaces: `.github/workflows/`, `infra/`, `scripts/`, `AGENTS.md`, `docs/DEPLOYMENT.md`, `docs/PRODUCTION_RUNBOOK.md` (historical `docs/work/**` excluded from runtime reachability).

## 1. KEEP — canonical, no content edits

### Workflows
- `.github/workflows/deploy-production.yml` — manual gate (build/push → approval → SSH).
- `.github/workflows/source-readiness.yml` — private source gate before deploy.

### Infra (production + active templates)
- `infra/production/docker-compose.app.yml`, `infra/production/docker-compose.yml`, `infra/production/solarsage-github-deploy`, `infra/production/solarsage-deploy.sudoers`, `infra/production/tmpfiles.d/solarsage.conf`
- `infra/systemd/solarsage-db.service`, `infra/systemd/solarsage-backup.service`, `infra/systemd/solarsage-backup.timer` — canonical DB + daily automated backup units.
- `infra/nginx/00-solarsage-default-reject.conf`, `infra/nginx/astro.vasiliy-ivanov.ru.conf`, `infra/nginx/astro-acme-bootstrap.conf`, `infra/certbot/deploy-hooks/20-solarsage-reload-nginx`, `infra/fail2ban/jail.d/solarsage-sshd.local`, `infra/ssh/github.com.known_hosts` — active Nginx/Certbot/Fail2ban/SSH templates (installed/checked by host-prepare + cert-prepare).

### Scripts (canonical entrypoints)
- `scripts/deploy/prod-orchestrator.sh` — sole app deploy entrypoint.
- `scripts/deploy/prod-host-prepare.sh` — host preparation (EDIT required, see §3).
- `scripts/deploy/prod-os-bootstrap.sh` — OS bootstrap.
- `scripts/deploy/prod-cert-prepare.sh` — TLS/Nginx preparation (uses prod-path-transaction).
- `scripts/deploy/prod-github-access.sh` — GitHub transport setup.
- `scripts/deploy/prod-infra-fingerprint.sh` — infra fingerprint (EDIT required, see §3).
- `scripts/deploy/check_prod_guard.sh` — prod guard; used by `scripts/guardrails.sh:280` (correct path) and `package.json` (stale path, see §3).
- `scripts/deploy/lib/prod-path-transaction.sh` — sourced by prod-host-prepare.sh:53 and prod-cert-prepare.sh:55.

### Focused tests retained (all green today)
- `scripts/deploy/tests/test-prod-orchestrator.sh` — orchestrator contract (28 cases).
- `scripts/deploy/tests/test-prod-github-wrapper.sh` — forced-command wrapper (56+10).
- `scripts/deploy/tests/test-prod-github-access.sh` — GitHub access matrix; no parked refs.
- `scripts/deploy/tests/test-prod-path-transaction.sh` — kept lib contract.
- `scripts/deploy/tests/test-prod-host-offsite-routing.sh` — host-prepare structural (EDIT follows host-prepare changes).
- `scripts/deploy/tests/test-prod-namespace-layout.sh` — namespace guard (EDIT follows README reduction).
- `scripts/deploy/tests/test-prod-backup-units.sh` — unit timeout regression; covers 2 kept + 2 parked units (EDIT to canonical backup units only; uncertain→KEEP per TZ rule).

## 2. DELETE — parked, closed reference clusters (all refs enumerated)

| File(s) | LOC | Last active references (all in delete/edit set or historical) |
|---|---:|---|
| `scripts/deploy/legacy/` (8 files) | 595 | README, test-prod-legacy-root-discovery (delete), legacy internal, docs parked-mentions |
| `scripts/deploy/prod-release-authority.py` | 809 | README, test-prod-release-authority (delete), test-prod-namespace-layout (edit), docs parked-mentions |
| `scripts/deploy/prod-release-promote.sh` | 112 | README, lib/prod-release-promotion (delete), test-prod-release-promotion (delete), docs parked-mentions |
| `scripts/deploy/prod-release-run.sh` | 137 | README, test-prod-release-pinning (delete) |
| `scripts/deploy/lib/prod-release.sh` | 115 | release lib/tests (delete), README |
| `scripts/deploy/lib/prod-release-build.sh` | 743 | release tests (delete), README, run-deploy-matrix (delete) |
| `scripts/deploy/lib/prod-release-manifest.py` | 498 | release lib/tests (delete), README |
| `scripts/deploy/lib/prod-release-promotion.sh` | 841 | release tests (delete), README, docs parked-mentions |
| `scripts/deploy/prod-env-prepare.sh` | 78 | prod-deploy (delete), host-prepare inventory (edit), fingerprint (edit), env tests (delete), README |
| `scripts/deploy/prod-env-run.sh` | 106 | backup-maintenance.service (delete), prod-deploy (delete), lib/prod-profile-context (delete), lib/prod-release-build (delete), env tests (delete), host-prepare inventory (edit), fingerprint (edit), README |
| `scripts/deploy/lib/prod-env-tool.py` | 2240 | env/backup/restore tests+scripts (delete), host-prepare inventory (edit), fingerprint (edit), README |
| `scripts/deploy/lib/prod-profile-context.sh` | 71 | backup/offsite/restore scripts (delete), host-prepare inventory (edit), fingerprint (edit), README |
| `scripts/deploy/prod-backup.sh` | 590 | backup tests (delete), host-prepare inventory (edit), fingerprint (edit), docs parked-mentions, README |
| `scripts/deploy/prod-backup-verify.sh` | 252 | prod-db-restore (delete), host-prepare inventory (edit), fingerprint (edit), backup tests (delete), docs parked-mentions |
| `scripts/deploy/prod-db-restore.sh` | 442 | host-prepare inventory (edit), fingerprint (edit), restore/profile tests (delete), docs parked-mentions |
| `scripts/deploy/prod-deploy.sh` | 588 | host-prepare inventory (edit), test-prod-deploy-source-loader (delete), docs parked-mentions, README |
| `scripts/deploy/prod-offsite-check.sh` | 103 | host-prepare inventory (edit), fingerprint (edit), offsite tests (delete), README |
| `scripts/deploy/prod-offsite-maintenance.sh` | 135 | backup-maintenance.service (delete), host-prepare inventory (edit), fingerprint (edit), offsite tests (delete), README |
| `scripts/deploy/prod-maintenance-run.sh` | 327 | lib/prod-release-promotion (delete), maintenance tests (delete), README |
| `scripts/deploy/lib/prod-maintenance-state.sh` | 613 | release lib (delete), maintenance tests (delete), README |
| `scripts/deploy/lib/prod-offsite-runtime.sh` | 192 | offsite scripts (delete), host-prepare PROD_TX_PATHS (edit), fingerprint (edit), offsite tests (delete), README |
| `scripts/deploy/tests/run-deploy-matrix.sh` | 211 | README, test-prod-namespace-layout (edit) |
| 24 parked test files (backup×3, db-restore-safety, deploy-source-loader, env×6, legacy-root-discovery, maintenance-foundation, offsite×2, profile-consumer-cutover, release×5, source-readiness-workflow) | 14,264 | self-cluster + run-deploy-matrix (delete) + README (edit) |
| `scripts/deploy/tests/lib/prod_workflow_validator.py`, `swap_workflow_steps.py` | 787 | test-prod-source-readiness-workflow.sh (delete) only |
| `infra/systemd/solarsage-api.service`, `solarsage-sidecar.service`, `solarsage-frontend.service` | 184 | host-prepare install/verify lists (edit), fingerprint (edit), parked tests (delete), docs/AGENTS (edit) |
| `infra/systemd/solarsage-backup-maintenance.service`, `solarsage-backup-maintenance.timer` | 94 | host-prepare lists (edit), fingerprint (edit), test-prod-backup-units (edit), docs parked-mentions |
| `infra/systemd/solarsage.service`, `solarsage-frontend-preview-3001.service` | 43 | host-prepare LEGACY_UNITS disable-by-name only (kept without templates) |
| `scripts/deploy/**/__pycache__/` (3 dirs, 5 `.pyc`) | — | generated caches |

**DELETE LOC subtotal: 25,075** (legacy 595 + R14 release 3,255 + profile/env 2,495 + backup/offsite/maintenance 2,654 + prod-deploy 588 + matrix+parked tests 15,167 + infra templates 321).

## 3. EDIT — active files with parked references

- `scripts/deploy/prod-host-prepare.sh` — remove parked entries from: `UNITS_TO_COMPARE` (api/sidecar/frontend + backup-maintenance), `INVENTORY_FILES`, `SHELL_SCRIPTS`, systemd-analyze `UNITS` (app units), `PROD_TX_PATHS` (sidecar/api/frontend units, backup-maintenance unit+timer, offsite_runtime), `SYSTEMD_SRC_FILES` (app units + backup-maintenance). RETAIN disable-by-name without templates: `DISABLED_UNITS` (app units), `LEGACY_UNITS` (`solarsage.service`, `solarsage-frontend-preview-3001.service`).
- `scripts/deploy/prod-infra-fingerprint.sh` — `FILES` list: drop api/sidecar/frontend units, backup-maintenance service/timer, prod-backup.sh, prod-backup-verify.sh, prod-db-restore.sh, prod-offsite-*, prod-env-*, lib/prod-env-tool.py, lib/prod-profile-context.sh, lib/prod-offsite-runtime.sh. Open question for reviewer: whether to add canonical new files (`docker-compose.app.yml`, `tmpfiles.d/solarsage.conf`, `prod-orchestrator.sh`) to the fingerprint list.
- `scripts/deploy/README.md` — rewrite inventory/compatibility to the reduced set.
- `package.json:30` — stale `bash scripts/check_prod_guard.sh` (broken since namespace move; old path absent) → `scripts/deploy/check_prod_guard.sh`.
- `AGENTS.md` — Systemd section lists app units as current runtime; update to Compose-canonical (cutover note retained).
- `docs/DEPLOYMENT.md`, `docs/PRODUCTION_RUNBOOK.md` — remove/reword dead-path references in active text (Appendix mentions of deleted paths).

## 4. Focused tests retained after cleanup

`test-prod-orchestrator.sh`, `test-prod-github-wrapper.sh`, `test-prod-github-access.sh`, `test-prod-path-transaction.sh`, `test-prod-host-offsite-routing.sh`, `test-prod-namespace-layout.sh`, `test-prod-backup-units.sh` (reduced). No matrix, no exhaustive suites.

## 5. Line counts

| Area | Before | Delete | After |
|---|---:|---:|---:|
| `scripts/deploy/` (files, excl. `__pycache__`) | 34,764 | 24,754 | 10,010 |
| `infra/` | 1,124 | 321 | 803 |
| **Total** | **35,888** | **25,075** | **10,813** |

## 6. Uncertain files (KEEP and report, never guess-delete)

- `test-prod-backup-units.sh` — kept as reduced edit (canonical backup units only) per "uncertain means KEEP"; reviewer may alternatively accept full deletion with the old backup slice.
- `test-prod-source-readiness-workflow.sh` + `tests/lib/*` — classified DELETE per explicit TZ candidate and "not a release gate" clause, with the noted trade-off: `source-readiness.yml` (kept workflow) loses its structural validator. Flagged for reviewer confirmation.
- `infra/nginx/astro-acme-bootstrap.conf` — kept (active cert bootstrap path), no uncertainty.

Stopped for reviewer approval. No deletion or edit performed in Phase A. No production actions.
