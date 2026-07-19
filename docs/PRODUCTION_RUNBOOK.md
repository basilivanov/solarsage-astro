# ############################################################################
# AI_HEADER: DOC_PRODUCTION_RUNBOOK
# ROLE: Production operations and runbook guide for SolarSage Astro.
# DEPENDENCIES: none
# ############################################################################

# START_MODULE_CONTRACT: M-DOC-PRODUCTION-RUNBOOK
# purpose: Operator guide for production deployment, backups, restore, and troubleshooting.
# owns:
#   - docs/PRODUCTION_RUNBOOK.md
# inputs: none
# outputs: none
# dependencies: none
# invariants:
#   - No plaintext credentials, secrets, or tokens.
#   - Document correct Telegram bot name (@AstroGrace_Bot).
#   - Canonical path only: installed orchestrator, installed compose, app.env.
# failure_policy: none.
# END_MODULE_CONTRACT: M-DOC-PRODUCTION-RUNBOOK

# START_MODULE_MAP: M-DOC-PRODUCTION-RUNBOOK
# public_entrypoints: none
# semantic_blocks: none
# END_MODULE_MAP: M-DOC-PRODUCTION-RUNBOOK

# Production Operations Runbook — SolarSage Astro

This document is the canonical operator guide for the production deployment of SolarSage Astro on `astro.vasiliy-ivanov.ru`. It replaces `docs/DEPLOY.md` as the active operational runbook.

**Canon:** immutable per-SHA OCI images + the installed Compose app stack + the sole installed orchestrator. No build or package-manager runs on the production host. The old systemd/profile-engine deploy path is non-operational and lives only in Appendix A (parked).

---

## 1. Production Topology & Ports

| Service | Internal Address | Host Port | Description |
|---|---|---|---|
| **Nginx** | `0.0.0.0:80`, `0.0.0.0:443` | 80/443 (Public) | Single entry point, SSL termination |
| **FastAPI Backend** | `127.0.0.1:8000` | None | API container (`solarsage-app` compose project) |
| **Next.js Frontend** | `127.0.0.1:3002` | None | Frontend container (`solarsage-app` compose project) |
| **SolarSage Sidecar** | `127.0.0.1:18091` | None | Calculation engine container (`solarsage-app` compose project) |
| **PostgreSQL DB** | `127.0.0.1:5433` | 5433 (Loopback) | Separate `solarsage-prod` compose project. Accessible only via loopback. |

**Security Policy:** Only ports 22 (SSH), 80 (HTTP), and 443 (HTTPS) are exposed publicly. All other services bind strictly to loopback (`127.0.0.1`).

Canonical files on the host:

- Installed orchestrator: `/usr/local/libexec/solarsage/prod-orchestrator` (root:root `0755`, executed as **root**: directly by the owner via `sudo`, by the daily backup timer, or via the single sudoers capability `sudo -n -H` from the GitHub wrapper — `astro` is never in the docker group)
- Installed app compose: `/etc/solarsage/compose/docker-compose.app.yml` (root:root `0644`, directory root:root `0755`)
- Environment/credential file: `/etc/solarsage/app.env` (real non-symlink `root:astro 0640`)
- Tmpfiles declaration: `/etc/tmpfiles.d/solarsage.conf` (root:root `0644`; materializes `/run/solarsage-maintenance.lock` `root:astro 0660` on fresh/rebooted hosts)
- Orchestrator state directory: `/var/lib/solarsage/orchestrator` (`astro:astro 0700`; the release record inside is written by root)
- Local backups: `/var/backups/solarsage` (`astro:astro 0700`)

---

## 2. Required Operator Environment (`/etc/solarsage/app.env`)

The `/etc/solarsage/app.env` file must exist on the host as a real non-symlink file owned by `root:astro` with mode `0640`. The following keys must be defined:

- **APP_ENV**: `production`.
- **APP_DOMAIN**: `astro.vasiliy-ivanov.ru`.
- **REGISTRY**: OCI registry/namespace prefix (no tag).
- **DATABASE_URL**: Container-form asyncpg URL (`postgresql+asyncpg://<user>:<password>@solarsage-db:5432/<db>`). This is the container form on the shared Compose network. Orchestrator commands and backups always use the host form `127.0.0.1:5433` — do not confuse the two.
- **POSTGRES_USER**, **POSTGRES_PASSWORD**, **POSTGRES_DB**: Database credentials (used by the orchestrator for backups on `127.0.0.1:5433`).
- **TELEGRAM_BOT_TOKEN**: HTTP API token for the Telegram Bot.
- **GRACE_USER_SALT**: Secret salt for user identity hash masking.
- **CORS_ALLOWED_ORIGINS**: Explicit allowed origin(s) for CORS, matching the production domain.
- **LLM_PROVIDER** (optional, default `openrouter`) and **OPENROUTER_API_KEY**: active provider key.
- **ANTHROPIC_API_KEY** (optional): required when `LLM_PROVIDER=anthropic`.
- **RESTIC_REPOSITORY**: restic target repository for offsite backups.
- **OFFSITE_RESTIC_PASSWORD_FILE**: path to a real non-symlink `root:astro 0640` file containing the restic repository password (e.g. `/etc/solarsage/backup/restic-password`).

- **GEONAMES_USERNAME**: GeoNames account used by `/api/geo/*` city/timezone lookups (fail-closed: compose interpolation and the endpoint both refuse to run without it).
- **EXPECTED_CALCULATION_VERSION**: canonical calculation version the sidecar must report exactly (currently `ss-calc-1.2.0`). Required: the orchestrator's health proof compares the sidecar's `calculation_version` against this value.
- **EPHEMERIS_EXPECTED_ARTIFACT_ID** and **EPHEMERIS_EXPECTED_MANIFEST_SHA256**: exact identity pins of the installed Swiss Ephemeris artifact (see section 5.1). Required once the artifact is installed: health proof matches them exactly against the sidecar's reported `ephemeris_artifact_id` / `ephemeris_manifest_sha256`.

Optional keys: `APP_VERSION`, `LLM_MODEL`.

The env file must **not** contain `RELEASE_SHA`: the target release identity is supplied per invocation; a conflicting `RELEASE_SHA` in the env file fails closed.

---

## 3. Deployments & Server Provisioning

### 3.1 Fresh Host Provisioning Order (Canonical Flow)

For preparing a completely new Ubuntu 24.04 amd64 production host:

1. **Bootstrap Base OS and System Dependencies:**
   Copy the repository bundle to the host and run the OS bootstrap as root (idempotent setup of packages, Node.js 22, pnpm, Docker, UFW, Fail2ban):
   ```bash
   sudo /opt/solarsage-astro/scripts/deploy/prod-os-bootstrap.sh --apply
   ```

2. **Create Operator Directories and the Environment File:**
   Create the required operator-controlled directories and files before host preparation (no secret values in these commands; fill file contents interactively per section 2). The file-creation commands are deliberately non-destructive: they install an empty file ONLY when it is absent, so a repeated run never overwrites existing secrets:
   ```bash
   sudo install -d -o root -g root -m 0755 /etc/solarsage
   sudo install -d -o root -g root -m 0755 /etc/solarsage/keys
   sudo install -d -o root -g root -m 0755 /etc/solarsage/backup
   if [ ! -e /etc/solarsage/app.env ]; then
     sudo install -m 0640 -o root -g astro /dev/null /etc/solarsage/app.env
   else
     echo "/etc/solarsage/app.env already exists — keeping current contents"
   fi
   if [ ! -e /etc/solarsage/backup/restic-password ]; then
     sudo install -m 0640 -o root -g astro /dev/null /etc/solarsage/backup/restic-password
   else
     echo "/etc/solarsage/backup/restic-password already exists — keeping current contents"
   fi
   ```
   Then edit `/etc/solarsage/app.env` per section 2 (all required keys) and write the restic repository password into `/etc/solarsage/backup/restic-password`; keep ownership `root:astro` and mode `0640` on both files.

3. **Verify DNS Resolution:**
   ```bash
   getent ahosts astro.vasiliy-ivanov.ru
   ```

4. **Bootstrap SSL Certificate and Secure Nginx:**
   ```bash
   sudo /opt/solarsage-astro/scripts/deploy/prod-cert-prepare.sh --apply --email operator@example.com
   sudo certbot renew --dry-run
   sudo /opt/solarsage-astro/scripts/deploy/prod-cert-prepare.sh --check
   ```

5. **Apply Production Host Runtime Configuration:**
   Host preparation installs the forced-command wrapper, the orchestrator byte-exact, the app compose byte-exact, systemd auxiliary units, sudoers policies, and DB container configuration. It never starts/restarts/stops the app systemd units; it only disables their autostart (metadata-only, no `--now`, no downtime) so a repeated apply after cutover never restores it:
   ```bash
   sudo /opt/solarsage-astro/scripts/deploy/prod-host-prepare.sh --apply
   sudo /opt/solarsage-astro/scripts/deploy/prod-host-prepare.sh --check
   ```
   Both commands must return exit code `0`.

6. **Configure Private GitHub Access & Deploy Keys:**
   The checkout key generation is explicitly guarded: it runs ONLY when the key is absent; an existing key is never overwritten:
   ```bash
   sudo install -d -o astro -g astro -m 0700 /home/astro/.ssh
   if [ ! -e /home/astro/.ssh/solarsage_prod_server_ed25519 ]; then
     sudo -u astro -- ssh-keygen -t ed25519 -N "" -f /home/astro/.ssh/solarsage_prod_server_ed25519 -C "solarsage-prod-server-checkout"
   else
     echo "checkout key already exists — keeping current key"
   fi
   ```
   Register the checkout public key (`/home/astro/.ssh/solarsage_prod_server_ed25519.pub`) as a GitHub **read-only** deploy key. The GitHub Actions deployment private key (`PROD_SSH_PRIVATE_KEY`) lives only in GitHub environment secrets; its public key is placed at `/etc/solarsage/keys/github-actions-deploy.pub` (root:root `0644`). Host preparation already installed the forced-command wrapper, so access apply/preflight can validate it:
   ```bash
   sudo /opt/solarsage-astro/scripts/deploy/prod-github-access.sh --apply
   sudo -u astro -- /opt/solarsage-astro/scripts/deploy/prod-github-access.sh --preflight
   ```
   Once the transport is applied and the repository visibility is manually changed to private by the owner, the **source-readiness workflow must be green before the deploy workflow** (explicit private gate).

7. **First Backup (Manual Action):**
   ```bash
   sudo /usr/local/libexec/solarsage/prod-orchestrator backup --manual-confirm
   ```

7.5 **One-time Private Registry Login (GHCR):**
   The orchestrator runs as root and uses root's Docker config. Perform one standard root Docker login with a **read-only** packages credential (a GitHub PAT limited to `read:packages`, entered interactively — never in Git, command history files, or logs):
   ```bash
   sudo --login bash -c 'read -rs GHCR_TOKEN && printf "%s" "$GHCR_TOKEN" | docker login ghcr.io -u <github-username> --password-stdin && unset GHCR_TOKEN'
   ```
   The credential lives only in `/root/.docker/config.json` on the host. Preflight and pull fail closed on registry auth errors; no token is written to Git or logs.

8. **Deploy and Launch Application Services (Manual Action):**
   The first launch/deploy is NOT an automatic continuation of the bootstrap. The owner runs (or approves the manual `Deploy Production` workflow, which executes the same command remotely):
   ```bash
   sudo /usr/local/libexec/solarsage/prod-orchestrator deploy <full-40-char-hex-sha> --manual-confirm
   ```
   The orchestrator validates `/etc/solarsage/app.env`, the installed compose, and DB health on 5433; runs a pre-deploy `pg_dump -Fc` + checksum + Restic backup; pulls each `:<sha>` tag once, verifies the OCI revision label, resolves RepoDigests, and activates only pinned `registry/repo@sha256:<64 hex>` references; requires all three health endpoints to return the exact requested `release_sha` (sidecar additionally proves ephemeris/calculation identity); records active/previous SHA + digest refs only after proven health; on failed post-change health it attempts one exact rollback to the recorded previous active tuple.

---

### 3.2 Routine Deployments and Infrastructure Updates

- **Routine Code-only Deployments:** Use the manual Deploy Production workflow (`workflow_dispatch` on `main`, `production` environment approval). The workflow builds and pushes immutable images and executes exactly `deploy <sha>` on the host, which the forced-command wrapper routes through the single sudoers capability (`sudo -n -H`) to `/usr/local/libexec/solarsage/prod-orchestrator deploy <sha> --manual-confirm`.
- **Orchestrator commands (as root via owner sudo):**
  ```bash
  sudo /usr/local/libexec/solarsage/prod-orchestrator preflight <sha>
  sudo /usr/local/libexec/solarsage/prod-orchestrator deploy <sha> --manual-confirm
  sudo /usr/local/libexec/solarsage/prod-orchestrator rollback <sha> --manual-confirm
  sudo /usr/local/libexec/solarsage/prod-orchestrator status
  sudo /usr/local/libexec/solarsage/prod-orchestrator backup --manual-confirm
  sudo /usr/local/libexec/solarsage/prod-orchestrator restore <dump> --manual-confirm  # plan + isolated rehearsal only
  sudo /usr/local/libexec/solarsage/prod-orchestrator migrate <sha> --manual-confirm  # one-shot migrate profile only
  ```
- **Infrastructure Template Changes:** After any repository-owned infra template change, checkout the target commit, rerun host preparation, then deploy via the orchestrator:
  ```bash
  sudo /opt/solarsage-astro/scripts/deploy/prod-host-prepare.sh --apply
  sudo /opt/solarsage-astro/scripts/deploy/prod-host-prepare.sh --check
  sudo /usr/local/libexec/solarsage/prod-orchestrator deploy <full-40-char-hex-sha> --manual-confirm
  ```
  A repeated host-prepare is safe after cutover: it never re-enables the app systemd units (Compose owns the ports) and never stops them.
- **Fingerprint Mismatch:** Fail-closed protection; run `sudo /opt/solarsage-astro/scripts/deploy/prod-host-prepare.sh --apply` for the commit first.
- **One-time cutover prerequisite (manual, owner-ordered):** immediately before the first Compose deploy on a host where the old systemd app services are running, the owner stops and disables them once so the Compose stack can claim ports 8000/3002/18091:
  ```bash
  sudo systemctl stop solarsage-api.service solarsage-sidecar.service solarsage-frontend.service
  sudo systemctl disable solarsage-api.service solarsage-sidecar.service solarsage-frontend.service
  ```
  The actual stop is ONLY this explicit owner command. Host preparation never stops the units — it may already have disabled their autostart (metadata-only, without `--now`, no downtime).
- **Source Hardening:** Non-ignored untracked files are forbidden in the workspace during deployment stages.

---

### 3.3 Testing and Workflows Specifications

- **Manual-only Execution:** Both visual regression tests (`visual-regression.yml`) and real E2E tests (`e2e.yml`) are strictly manual-only (`workflow_dispatch`).
- **Required Secrets:** Real E2E tests require two repository secrets: `E2E_TELEGRAM_BOT_TOKEN` and `E2E_OPENROUTER_API_KEY` (low-cost model `openai/gpt-4.1-nano`). Do not use production tokens/keys for routine testing.
- **Suite Options:** `smoke` (default): Today/Calendar/Navigation specs on Chromium; `full`: all top-level real specs on Chromium.
- **Fail-closed Snapshot Policy:** Visual regression tests use `updateSnapshots: \"none\"`. Missing snapshots fail closed; update baselines only locally with `UPDATE_SNAPSHOTS=true`.

---

### 3.4 Deployment Transport Installation

The deployment transport uses a hardened SSH configuration with a forced command and a limited sudoers policy, installed and updated via `prod-host-prepare.sh --apply`:

1. **Verify Root SSH Access** before modifying sudoers or removing permissions.
2. **Configure SSH Authorized Keys:** add the GitHub Actions deployment public key to `/home/astro/.ssh/authorized_keys` prefixed with:
   ```text
   restrict,command="/usr/local/sbin/solarsage-github-deploy" ssh-ed25519 <ACTIONS_PUBLIC_KEY> solarsage-github-actions-prod
   ```
   Permissions: `chmod 0700 ~/.ssh`, `chmod 0600 ~/.ssh/authorized_keys`, owned `astro:astro`.
3. **Separate Deploy Keys:** the server-to-GitHub checkout key is read-only; never grant it write access; never reuse the Actions-to-server key for checkouts.
4. **GitHub Environment and Variable Configuration:** the `production` environment uses only the secrets `PROD_HOST`, `PROD_USER`, `PROD_SSH_PRIVATE_KEY`, `PROD_KNOWN_HOSTS`; deployment branch policy allows `main` only. The image registry namespace is NOT an environment variable: the `build` job has no `environment`, so `REGISTRY_NAMESPACE` must be a **repository-level Actions variable** (for example `ghcr.io/OWNER`) reachable by the build job:
   - UI path: repository **Settings → Secrets and variables → Actions → Variables → New repository variable**, name `REGISTRY_NAMESPACE`, value `ghcr.io/<owner>` (no tag).
   - Setup/check via CLI:
     ```bash
     gh variable set REGISTRY_NAMESPACE --body "ghcr.io/<owner>"
     gh variable get REGISTRY_NAMESPACE
     ```
   Keep the four production secrets in the `production` environment; only `REGISTRY_NAMESPACE` lives at repository level (non-secret).
5. **Secure Transport Verification:** any non-empty remote command other than the exact forms must be rejected with exit code `126`.
6. **Direct Operator Fallback:**
   ```bash
   sudo /usr/local/libexec/solarsage/prod-orchestrator deploy <full-40-char-hex-sha> --manual-confirm
   ```
7. **Provider-Specific LLM Key Names:** `OPENROUTER_API_KEY` when `LLM_PROVIDER=openrouter`; `ANTHROPIC_API_KEY` when `anthropic`.

---

## 4. Database Backups and Restore

### 4.1 Backup (Canonical: daily automated + manual fallback)

The canonical daily backup is automated: `solarsage-backup.timer` runs `solarsage-backup.service`, which executes exactly the installed orchestrator (`/usr/local/libexec/solarsage/prod-orchestrator backup --manual-confirm`) — no mutable checkout, no profile engine. The timer stays enabled/active; the parked old backup-maintenance timer/service and old backup scripts are never enabled.

Manual fallback / on-demand backup (as root):

```bash
sudo /usr/local/libexec/solarsage/prod-orchestrator backup --manual-confirm
```

Each backup runs `pg_dump -Fc` against `127.0.0.1:5433`, verifies with `pg_restore --list`, writes a `db-YYYYMMDDTHHMMSSZ.dump` + `.sha256` pair (mode `0600`) into `/var/backups/solarsage`, and copies the pair to the encrypted Restic repository (`RESTIC_REPOSITORY` + `OFFSITE_RESTIC_PASSWORD_FILE`). On a Restic failure the local dump and checksum are preserved and the command returns non-zero. Backup data is never deleted by these paths.

### 4.2 Encrypted Offsite Backup (Restic)

- **One-time Initialization** (as user `astro`):
  ```bash
  sudo -u astro -- env RESTIC_PASSWORD_FILE=/etc/solarsage/backup/restic-password RESTIC_REPOSITORY=<repository-url> restic init
  ```
  For SFTP repositories also pass `-o sftp.args="-i <key> -o IdentitiesOnly=yes -o UserKnownHostsFile=<known_hosts> -o StrictHostKeyChecking=yes -o BatchMode=yes"`.
- **Secret Boundary:** the restic password file and any SSH keys are operator-placed, `root:astro` or `astro:astro`, mode `0640` or `0600` (never `root:astro 0600`, which would be unreadable for `astro`). Never store them in Git.

### 4.3 Manual Restore (Plan + Isolated Rehearsal Only)

Restore in the canonical path is an explicit manual command that verifies the dump pair and rehearses into a unique throwaway postgres container on a free loopback port. It never touches the production DB and never removes a pre-existing container:

```bash
sudo /usr/local/libexec/solarsage/prod-orchestrator restore /var/backups/solarsage/db-YYYYMMDDTHHMMSSZ.dump --manual-confirm
```

A real production restore requires a separate explicit user command and a later accepted runbook.

### 4.4 Cache Policy

Today/Calendar cache is versioned by calculation/scoring/content/canon identity; no blanket cache invalidation is performed at deploy time. Schema-affecting cache transformations belong strictly to migrations.

---

## 5.1 Swiss Ephemeris Artifact (Canonical)

Production calculations must run on pinned Swiss Ephemeris files, never on
the Moshier fallback. Canonical layout (root-owned, immutable):

```text
/opt/solarsage-ephemeris/
  releases/<artifact-id>/{ephe/, manifest.json, manifest.sha256}
  current -> releases/<artifact-id>
  previous  # preserved prior release path for rollback
```

Install/verify with the fail-closed installer (no downloads, no fabricated
bytes, immutable releases, atomic pointer flip). Use the installed canonical
path — the offline engine oracle needs pyswisseph, so point
`EPHE_ORACLE_PYTHON` at an interpreter that has it (sidecar venv by default):

```bash
sudo EPHE_ORACLE_PYTHON=/opt/solarsage-astro/apps/solarsage/venv/bin/python \
  /usr/local/libexec/solarsage/prod-ephemeris-install --apply /path/to/staged-bundle
sudo /usr/local/libexec/solarsage/prod-ephemeris-install --check
```

After install, set `EPHEMERIS_EXPECTED_ARTIFACT_ID` and
`EPHEMERIS_EXPECTED_MANIFEST_SHA256` in `/etc/solarsage/app.env` to the
installed values and keep `EXPECTED_CALCULATION_VERSION` current. The
orchestrator's health proof requires the sidecar to report `engine=swieph`
and these exact identities; any Moshier fallback fails the deploy closed.

## 5. Database Migrations (Alembic)

Migrations run only through the explicit orchestrator command — exact SHA, maintenance lock, full preflight, digest-pinned one-shot `migrate` profile, pre-migration backup included. They are never automatic and never part of `deploy`:

```bash
sudo /usr/local/libexec/solarsage/prod-orchestrator migrate <full-40-char-hex-sha> --manual-confirm
```

Run migrations only after the pre-migration backup succeeded and before deploying the release that requires them. To inspect the current head without mutating:

```bash
cd /opt/solarsage-astro/apps/api && .venv/bin/alembic -c alembic.ini current
```

**Rollback Warning:** schema rollbacks are not automated. On migration failure, restore the database from the pre-deployment backup (section 4.3 rehearsal first) and roll back the release via the orchestrator.

---

## 6. Container Operations

```bash
# App stack status (read-only orchestrator view)
sudo /usr/local/libexec/solarsage/prod-orchestrator status

# Compose-level status and logs
sudo docker compose --env-file /etc/solarsage/app.env -f /etc/solarsage/compose/docker-compose.app.yml ps
sudo docker compose --env-file /etc/solarsage/app.env -f /etc/solarsage/compose/docker-compose.app.yml logs -f api
```

---

## 7. Nginx, Fail2ban, UFW, and SSL Certs

- **Nginx configuration location:** `/etc/nginx/sites-available/astro.vasiliy-ivanov.ru.conf`
- **Check config syntax:** `sudo nginx -t`
- **Reload Nginx:** `sudo systemctl reload nginx`
- **SSL Cert Renewal:** Certbot handles automatic renewal via `certbot.timer`; Nginx is reloaded by the deployment hook at `/etc/letsencrypt/renewal-hooks/deploy/20-solarsage-reload-nginx`.
- **Verify SSL status safely:**
  ```bash
  sudo certbot certificates
  sudo systemctl status certbot.timer
  sudo certbot renew --dry-run
  ```
- **UFW Firewall Status:** `sudo ufw status verbose`
- **Fail2ban Status & sshd Jail:** `sudo fail2ban-client status sshd`

---

## 8. Incident Checklist

1. **API / Sidecar / Frontend down:** `prod-orchestrator status`, compose `ps`/`logs` for the affected container.
2. **502 Bad Gateway from Nginx:** verify API health on `127.0.0.1:8000/api/health` and frontend on `127.0.0.1:3002/api/release-health`; compare `release_sha` with the recorded release.
3. **Database connection failure:** verify the `solarsage-prod` DB container is active and loopback port `5433` is bound: `docker ps` and `pg_isready -h 127.0.0.1 -p 5433`.
4. **Failed deploy health:** the orchestrator attempts one exact rollback automatically; check `status` for the recorded active/previous tuples. `recovery_required` output means the rollback could not be proven — investigate before retrying.
5. **Telegram Bot Issues:** the production bot username is `@AstroGrace_Bot`. Do not run the Ductor Telegram bot agent (`vi_astro_bot`) on the production server. Bot API configuration (description, commands, menu) and avatar are configured manually via BotFather.
6. **Key Separation:** the GitHub checkout deploy key (read-only) is separate from the GitHub Actions deployment private key (SSH to host).
7. **Private Repository Boundary:** SSH private keys and `/etc/solarsage/app.env` are operator-controlled and must never be committed to Git.
8. **Offsite Backup Alerting:** if the Restic copy fails, local backups are preserved, but a critical alert must be triggered and investigated before the next deploy.

---

## Appendix A — Removed parked code (181 cleanup)

The 181 cleanup removed the parked deployment slice from the repository (exact files and reachability proof: `docs/work/2026-07-15_production-server-bootstrap/181A_MANIFEST_DEAD_CODE_AUDIT.md`): the unfinished R14 promotion/GC runtime and its harnesses, the profile/env generation engine, the old backup/offsite/maintenance entrypoints replaced by the canonical orchestrator, the legacy operator tools, the exhaustive deploy matrix and the stale one-job deploy workflow validator. They are non-canonical and must not be recreated.

The only names that remain operationally relevant are the already-installed systemd unit names on the host, valid solely for the owner's one-time cutover stop/disable commands (their templates were removed from the repository and are never reinstalled): `solarsage-api.service`, `solarsage-sidecar.service`, `solarsage-frontend.service`, `solarsage.service`, `solarsage-frontend-preview-3001.service`, `solarsage-backup-maintenance.timer`, `solarsage-backup-maintenance.service`. The canonical env is `/etc/solarsage/app.env`; the canonical backup is the daily `solarsage-backup.timer`/`solarsage-backup.service` running the installed orchestrator (section 4).
