# Report 182 — minimal deploy dead code removal (TZ 181, Phase B)

Status: Phase B implemented per accepted `181A_MANIFEST_DEAD_CODE_AUDIT.md` with the reviewer's six decisions. Source-only; no production actions, no commit/push. Stopping for review.

## Exact deletions (accepted manifest)

| Slice | Files | LOC |
|---|---|---:|
| `scripts/deploy/legacy/` operator tools | 8 | 595 |
| R14 release/promotion/authority runtime (`prod-release-authority.py`, `prod-release-promote.sh`, `prod-release-run.sh`, `lib/prod-release.sh`, `lib/prod-release-build.sh`, `lib/prod-release-manifest.py`, `lib/prod-release-promotion.sh`) | 7 | 3,255 |
| Profile/env engine (`prod-env-prepare.sh`, `prod-env-run.sh`, `lib/prod-env-tool.py`, `lib/prod-profile-context.sh`) | 4 | 2,495 |
| Old backup/offsite/maintenance/restore (`prod-backup.sh`, `prod-backup-verify.sh`, `prod-db-restore.sh`, `prod-offsite-check.sh`, `prod-offsite-maintenance.sh`, `prod-maintenance-run.sh`, `lib/prod-maintenance-state.sh`, `lib/prod-offsite-runtime.sh`) | 8 | 2,654 |
| `prod-deploy.sh` | 1 | 588 |
| `tests/run-deploy-matrix.sh` + 23 parked test files + 2 test libs (`prod_workflow_validator.py`, `swap_workflow_steps.py`) | 26 | 15,167 |
| Obsolete systemd templates (`solarsage-api/sidecar/frontend.service`, `solarsage-backup-maintenance.service/.timer`, `solarsage.service`, `solarsage-frontend-preview-3001.service`) | 7 | 321 |
| `scripts/deploy/**/__pycache__/` (3 dirs, 5 `.pyc`) | — | — |
| **Total deleted** | **61 files + 3 cache dirs** | **25,075** |

Decision (1): `test-prod-source-readiness-workflow.sh` and both validator libs deleted; `source-readiness.yml` kept without a replacement harness (not a release gate).

## Edits (parked-reference removal, decisions 2–6)

- `scripts/deploy/prod-host-prepare.sh`: `UNITS_TO_COMPARE` → canonical 3 units; `INVENTORY_FILES`/`SHELL_SCRIPTS` → canonical set (+ `docker-compose.app.yml`, `tmpfiles.d/solarsage.conf`, `prod-orchestrator.sh`); systemd-analyze `UNITS` → db + backup.timer; `PROD_TX_PATHS` → canonical installs only (no app/backup-maintenance/offsite entries); `SYSTEMD_SRC_FILES` → db/backup.service/backup.timer. Retained disable-by-name (no install, no fingerprint, no byte-verify of templates): `DISABLED_UNITS` (api/sidecar/frontend + backup-maintenance.timer), `PARKED_INACTIVE_UNITS` (maintenance timer+service), `COMPOSE_OWNED_UNITS`, `LEGACY_UNITS` (`solarsage.service`, `solarsage-frontend-preview-3001.service`) — decision (4).
- `scripts/deploy/prod-infra-fingerprint.sh`: `FILES` reduced to canonical and ADDED `infra/production/docker-compose.app.yml`, `infra/production/tmpfiles.d/solarsage.conf`, `scripts/deploy/prod-orchestrator.sh` — decision (3). Fingerprint recomputes: `27f06b2c...502b` (value changed by design; applied via next host-prepare).
- `scripts/deploy/tests/test-prod-backup-units.sh`: reduced to the canonical backup pair with sandbox-staged ExecStart verification — decision (2).
- `package.json`: `guardrails:prod` fixed to `scripts/deploy/check_prod_guard.sh` — decision (5). The guard now runs and correctly fails closed on the pre-existing `.env.production` in the dirty worktree root (intended behavior; unrelated to this cleanup).
- `scripts/deploy/README.md`: rewritten to the reduced canonical inventory + compatibility map (decision 6).
- `scripts/deploy/tests/test-prod-namespace-layout.sh`: new-files case now `test-prod-namespace-layout.sh`/`test-prod-orchestrator.sh`; obsolete release-authority/legacy/test-lib branches removed. Suite green with the reduced inventory.
- `AGENTS.md`: ports table and Systemd section describe the Compose-canonical runtime; cutover unit names retained; file-locations table now points to `/etc/solarsage/app.env`, installed orchestrator and installed compose. Post-182 doc microfix: port 18091 documented as the `solarsage-sidecar` container in Compose `solarsage-app` (not systemd), and the Docker section explicitly splits `infra/production/docker-compose.app.yml` (canonical production app), `infra/production/docker-compose.yml` (canonical DB) from root `docker-compose.yml`/`docker-compose.prod.yml` (dev/compatibility only).
- `docs/DEPLOYMENT.md` and `docs/PRODUCTION_RUNBOOK.md`: parked sections rewritten to describe the 181 removal (with manifest link); Appendix A names only operationally relevant installed unit names for the owner's one-time cutover, no repo paths.

## LOC

| Area | Before | After |
|---|---:|---:|
| `scripts/deploy/` | 34,764 | 9,853 |
| `infra/` | 1,165 | 844 |
| **Total** | **35,929** | **10,697** |

(25,075 deleted + 157 edit-shrinkage across README/host-prepare/fingerprint/backup-units.)

## Focused verification (direct rc)

| Check | rc / result |
|---|---|
| `git diff --check` (changed paths) | 0 |
| `bash -n` all 15 retained deployment shell scripts | 0 |
| YAML parse `deploy-production.yml` + `source-readiness.yml` | OK |
| `docker compose --env-file <temp> -f infra/production/docker-compose.app.yml config --quiet` | 0 |
| `visudo -cf infra/production/solarsage-deploy.sudoers` | parsed OK |
| `test-prod-orchestrator.sh` ×2 | 0 — 28/28, byte-identical |
| `test-prod-github-wrapper.sh` | 0 — 56+10 |
| `test-prod-github-access.sh` | 0 |
| `test-prod-host-offsite-routing.sh` | 0 |
| `test-prod-namespace-layout.sh` | 0 (reduced inventory, mutations fail closed) |
| `test-prod-path-transaction.sh` | 0 |
| `test-prod-backup-units.sh` (reduced, staged) | 0 |
| API pytest `test_health.py` + `test_public_surface_security.py` | 5 passed |
| Sidecar pytest `test_health.py` | 2 passed |
| `npx vitest run __tests__/guardrails/preview-isolation.test.ts` | 7 passed |
| rg proof over workflows/infra/scripts/AGENTS.md/active docs | clean; only two intentional negative-guard fixtures remain (`test-prod-host-offsite-routing.sh:85` forbidden-invocation check, `test-prod-namespace-layout.sh:299` mutation-D decoy), by design to reject reintroduction |

## Explicit non-actions

No `--apply`/install, no service operation, no Docker/registry login or push, no DB command, no migration, no commit/push. Unrelated dirty worktree untouched (including the pre-existing `.env.production` the prod guard flags). Old matrix and stale one-job deploy validator were deleted, not repaired; they are not release gates. tmux session left alive.

## Post-review consistency fixes

- Dev-only `db-create` helper restored from HEAD and moved to the explicit dev path `scripts/dev/db-create.sh` (not root `scripts/`, so the namespace stale-path guard stays green and unweakened); its repo-root computation fixed to `cd "$(dirname "$0")/../.."` (statically proven: resolves to the repository root where `.env` and `infra/docker-compose.yml` live). `Makefile` target updated; no active references to `scripts/db-create.sh` remain.
- Active-text cleanup in `Makefile` and root `README.md`: stale "until W-DEPLOY", "requires missing systemd units" and "sidecar runs outside this repo" claims removed; `deploy`/`backup`/`logs`/`solarsage` targets stay disabled (fail-closed, hint-only) and now point to the canonical Compose orchestrator and `docs/DEPLOYMENT.md`/`docs/PRODUCTION_RUNBOOK.md`. Historical `grace/*` documents untouched.
- Verification for these fixes: `bash -n` helper 0; repo-root static proof OK; `make help` and disabled targets print hints and fail only (no service actions); `test-prod-namespace-layout.sh` green; rg stale phrases/paths clean; `git diff --check` 0.
- Docs/config ambiguity cleanup (final): root `README.md` now states the prepared manual-only production path; compose header comments (`docker-compose.yml`, `docker-compose.prod.yml`, `infra/docker-compose.yml`) marked dev/compatibility only with canon pointers to `infra/production/`; `scripts/dev/db-create.sh` NOTE updated; dangerously stale root `DEPLOYMENT.md` (systemd frontend, kill -9, dev domain, no active refs) deleted; `docs/DEPLOY.md` banner and `README_Структура_документации.md`/`MANIFEST.md` lines updated to "replaced"; `rollout/solarsage_v2_rollout_gates.md` and `ADR-001_Headless_Testing.md` no longer reference app systemd units and point to the canonical Compose orchestrator/runbook.
