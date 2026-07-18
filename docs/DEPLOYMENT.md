# AI_HEADER
# module: M-DEPLOY-DOCS
# wave: W-DEPLOY
# purpose: Deployment documentation

# Deployment Guide

## Prerequisites

- Docker 20.10+ and Docker Compose 2.0+ on the production host
- Host Nginx on 80/443 proxying to canonical loopback ports (existing)
- Separate PostgreSQL compose project on 127.0.0.1:5433 (existing, unchanged)
- Domain with SSL certificate (production)

## Canonical production path (minimal Compose path)

The canonical production path is one manually invoked orchestrator over
immutable per-SHA OCI images and Docker Compose. There is no build or
package-manager run on the production host.

Canonical runtime:

```text
Nginx 80/443 -> 127.0.0.1:3002 frontend
             -> 127.0.0.1:8000 API
API -> sidecar 127.0.0.1:18091
DB  -> 127.0.0.1:5433 (separate solarsage-prod compose project)
```

Canonical files:

- App stack: `infra/production/docker-compose.app.yml`
  (api/sidecar/frontend, loopback-only, digest-pinned images)
- DB stack (separate, unchanged): `infra/production/docker-compose.yml` (port 5433)
- Sole entrypoint: `scripts/deploy/prod-orchestrator.sh`
  (installed by host preparation as `/usr/local/libexec/solarsage/prod-orchestrator`, root:root `0755`)
- Installed app compose: `/etc/solarsage/compose/docker-compose.app.yml` (root:root `0644`)
- Root-owned env/credential file on the host: `/etc/solarsage/app.env`
  (real non-symlink `root:astro 0640`)
- Orchestrator state directory: `/var/lib/solarsage/orchestrator` (`astro:astro 0700`)

## Orchestrator commands

Always use the installed path, executed as **root** (owner `sudo`; the GitHub
forced wrapper reaches it through the single sudoers capability
`sudo -n -H`; `astro` is never in the docker group):

```bash
sudo /usr/local/libexec/solarsage/prod-orchestrator preflight <sha>
sudo /usr/local/libexec/solarsage/prod-orchestrator deploy <sha> --manual-confirm
sudo /usr/local/libexec/solarsage/prod-orchestrator rollback <sha> --manual-confirm
sudo /usr/local/libexec/solarsage/prod-orchestrator status
sudo /usr/local/libexec/solarsage/prod-orchestrator backup --manual-confirm
sudo /usr/local/libexec/solarsage/prod-orchestrator restore <dump> --manual-confirm   # plan + isolated rehearsal only
sudo /usr/local/libexec/solarsage/prod-orchestrator migrate <sha> --manual-confirm   # one-shot migrate profile only
```

The canonical daily backup is automated: `solarsage-backup.timer` runs
`solarsage-backup.service`, which executes exactly the installed orchestrator
`backup --manual-confirm`. The manual `backup` command above is the on-demand
fallback of the same canonical path.

Every deploy/rollback:

1. requires the exact full 40-hex SHA and explicit `--manual-confirm`;
2. validates the env/credential file, registry, Compose config and DB health on 5433;
3. runs a pre-deploy `pg_dump -Fc` + `pg_restore --list` + SHA256 pair and a Restic offsite copy;
4. pulls each `:<sha>` tag once, verifies the OCI revision label equals the
   exact SHA, resolves the RepoDigests, and activates only pinned
   `registry/repo@sha256:<64 hex>` references (never mutable tags);
5. requires API, sidecar and frontend health to return the exact requested
   `release_sha` (sidecar additionally proves ephemeris/calculation identity);
6. records active/previous SHA + digest references only after all health checks pass;
7. on failed health after a change, attempts one exact rollback to the recorded
   previous active tuple using stored digest references (never re-pulls old tags).

Images are built and pushed only by the manual `Deploy Production` GitHub
workflow (`workflow_dispatch` on `main`, `production` environment approval,
exact SSH command `deploy <sha>`). No push to `main` deploys by itself.

CI configuration: `REGISTRY_NAMESPACE` (for example `ghcr.io/OWNER`, no tag)
must be a **repository-level Actions variable** (Settings → Secrets and
variables → Actions → Variables), because the `build` job runs without an
`environment` and cannot see environment-scoped variables. The four deploy
secrets (`PROD_HOST`, `PROD_USER`, `PROD_SSH_PRIVATE_KEY`, `PROD_KNOWN_HOSTS`)
remain in the `production` environment.

## One-time cutover prerequisite

Before the first Compose deploy, the old systemd application services must be
stopped and disabled so the Compose stack can claim ports 8000/3002/18091:

```bash
sudo systemctl stop solarsage-api.service solarsage-sidecar.service solarsage-frontend.service
sudo systemctl disable solarsage-api.service solarsage-sidecar.service solarsage-frontend.service
```

This is a one-time manual action performed by the owner; it is never executed
by the orchestrator, the workflow or host preparation.

## Secrets

- Source-controlled files contain no secret values or defaults.
- The host supplies `/etc/solarsage/app.env` (`root:astro 0640`) with
  `REGISTRY`, `POSTGRES_USER`/`POSTGRES_PASSWORD`/`POSTGRES_DB`,
  `DATABASE_URL` (container form `...@solarsage-db:5432/...`), `APP_DOMAIN`,
  `TELEGRAM_BOT_TOKEN`, `GRACE_USER_SALT`, `CORS_ALLOWED_ORIGINS`,
  `OPENROUTER_API_KEY`, `RESTIC_REPOSITORY` and
  `OFFSITE_RESTIC_PASSWORD_FILE` (path to a `root:astro 0640` password file).
- The host DB URL for orchestrator commands and backups is `127.0.0.1:5433`;
  the container-internal `DATABASE_URL` uses the DB container name on the
  shared network. Do not confuse the two forms.
- No `.env`, Telegram token, OpenRouter key, DB password or SSH material is
  copied into image layers.

## Backup and restore

- Daily automated backup via `solarsage-backup.timer`; explicit manual fallback:
  `sudo /usr/local/libexec/solarsage/prod-orchestrator backup --manual-confirm`
  (`pg_dump -Fc` + `pg_restore --list` + SHA256 pair in `/var/backups/solarsage`,
  Restic offsite copy; local pair is preserved even on Restic failure).
- Explicit manual restore rehearsal: `sudo /usr/local/libexec/solarsage/prod-orchestrator restore <dump> --manual-confirm`
  restores into a unique throwaway postgres container only. A real production
  restore requires a separate explicit user command and an accepted runbook.

## Removed parked code (181 cleanup)

The unfinished R14 promotion/GC runtime, the profile/env engine, the old
backup/offsite/maintenance entrypoints, the legacy operator tools, the
exhaustive test matrix and the stale one-job deploy workflow validator were
removed from the repository in the 181 cleanup
(`docs/work/2026-07-15_production-server-bootstrap/181A_MANIFEST_DEAD_CODE_AUDIT.md`).
They are non-canonical and must not be recreated.
