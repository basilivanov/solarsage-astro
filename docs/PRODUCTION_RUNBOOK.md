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
# failure_policy: none.
# END_MODULE_CONTRACT: M-DOC-PRODUCTION-RUNBOOK

# START_MODULE_MAP: M-DOC-PRODUCTION-RUNBOOK
# public_entrypoints: none
# semantic_blocks: none
# END_MODULE_MAP: M-DOC-PRODUCTION-RUNBOOK

# Production Operations Runbook — SolarSage Astro

This document serves as the canonical operator guide for the production deployment of SolarSage Astro on `astro.vasiliy-ivanov.ru`. It replaces `docs/DEPLOY.md` as the active operational runbook.

---

## 1. Production Topology & Ports

| Service | Internal Address | Host Port | Description |
|---|---|---|---|
| **Nginx** | `0.0.0.0:80`, `0.0.0.0:443` | 80/443 (Public) | Single entry point, SSL termination |
| **FastAPI Backend** | `127.0.0.1:8000` | None | uvicorn backend server (systemd) |
| **Next.js Frontend** | `127.0.0.1:3002` | None | Next.js production build server (systemd) |
| **SolarSage Sidecar** | `127.0.0.1:18091` | None | Astrological calculations engine (systemd) |
| **PostgreSQL DB (Host)** | `127.0.0.1:5433` | 5433 (Loopback) | PostgreSQL host binding port |
| **PostgreSQL DB (Container)** | `127.0.0.1:5432` | None | Container internal PostgreSQL port |

**Security Policy:** Only ports 22 (SSH), 80 (HTTP), and 443 (HTTPS) are exposed publicly. All other services bind strictly to loopback (`127.0.0.1`).

---

## 2. Required Environment Variables (`.env.production`)

The `/opt/solarsage-astro/.env.production` file must exist on the host with permissions `0600` or `0640` (owned by `astro:astro`). The following configuration keys must be defined:

- **APP_ENV**: Must be set to `production`.
- **APP_DOMAIN**: Must be set to `astro.vasiliy-ivanov.ru`.
- **DEV_MODE**: Must be set to `false`.
- **SESSION_COOKIE_SECURE**: Must be set to `true`.
- **DATABASE_URL**: PostgreSQL connection string (asyncpg driver) pointing to `127.0.0.1:5433`.
- **POSTGRES_USER**: Database administrative user.
- **POSTGRES_PASSWORD**: Database password.
- **POSTGRES_DB**: Database name.
- **TELEGRAM_BOT_TOKEN**: HTTP API token for the Telegram Bot.
- **BOT_USERNAME**: The username of the production bot (expected value: `AstroGrace_Bot`).
- **SOLARSAGE_URL**: Internal URL of the SolarSage sidecar (typically `http://127.0.0.1:18091`).
- **CORS_ALLOWED_ORIGINS**: Explicit allowed origin(s) for CORS, matching the production domain.
- **GRACE_USER_SALT**: Secret salt for user identity hash masking.
- **LLM_PROVIDER**: The active LLM API provider (e.g. `openrouter` or `anthropic`).
- **LLM_MODEL**: The exact model identifier for text generation.
- **LLM_MAX_TOKENS**: Maximum tokens budget for LLM calls.
- **SOLARSAGE_V2_ENABLED**: Rollout flag for V2 horizons pipeline.
- **SOLARSAGE_V2_DUAL_RUN**: Rollout flag for scoring comparison runs.
- **SOLARSAGE_V2_FRONTEND_ENABLED**: Rollout flag for displaying V2 UI elements.
- **SOLARSAGE_AUDIT_ARTIFACTS_ENABLED**: Rollout flag for saving calculation audits.

---

## 3. Deployments

### 3.1 First Bootstrap (Initial Server Setup)
1. Clone the repository to `/opt/solarsage-astro` as the `astro` user.
2. Create and secure `/opt/solarsage-astro/.env.production` (permissions `0600` or `0640`, owned by `astro:astro`).
3. Boot the database container:
   ```bash
   docker compose --env-file /opt/solarsage-astro/.env.production -f /opt/solarsage-astro/infra/production/docker-compose.yml up -d db
   ```
4. Initial Nginx Flow:
   - Apply a temporary HTTP ACME configuration routing port 80 to `/var/www/html` for Let's Encrypt challenges.
   - Run Certbot to issue the SSL certificate:
     ```bash
     sudo certbot certonly --webroot -w /var/www/html -d astro.vasiliy-ivanov.ru
     ```
   - Copy the canonical TLS config `/opt/solarsage-astro/infra/nginx/astro.vasiliy-ivanov.ru.conf` to `/etc/nginx/sites-available/` and link to `sites-enabled/`.
   - Test and reload Nginx:
     ```bash
     sudo nginx -t
     sudo systemctl reload nginx
     ```
5. Install systemd service templates:
   ```bash
   sudo cp /opt/solarsage-astro/infra/systemd/solarsage-*.service /etc/systemd/system/
   sudo cp /opt/solarsage-astro/infra/systemd/solarsage-backup.* /etc/systemd/system/
   sudo systemctl daemon-reload
   ```
6. Run the deployment script in bootstrap mode:
   ```bash
   bash /opt/solarsage-astro/scripts/prod-deploy.sh --current
   ```
7. Enable and start timers:
   ```bash
   sudo systemctl enable --now solarsage-backup.timer
   ```

### 3.2 Routine Deployments
Routine deployments are performed manually or triggered via GitHub Actions:
- **Manual:** Run `/opt/solarsage-astro/scripts/prod-deploy.sh` as the `astro` user.
- **GitHub Actions:** Trigger the `Deploy Production` workflow manually from the GitHub Actions tab. Note that the deployment workflow cannot be enabled or triggered until the production changes are merged into the remote `origin/main` branch.

---

## 4. Database Backups and Restore

### 4.1 Backup Automation
Backups are run daily at `03:20` local server time via `solarsage-backup.timer`.
Manual backup can be triggered with:
- `sudo systemctl start solarsage-backup.service` or `bash /opt/solarsage-astro/scripts/prod-backup.sh`

Backups are saved to `/var/backups/solarsage/db-YYYYMMDDTHHMMSSZ.dump` with permissions `0600` and are kept for 14 days. A corresponding `.sha256` checksum is created alongside.

### 4.2 Manual Database Restore
To restore the database from a backup dump without exposing the password in command logs:

1. Identify the backup file (e.g. `/var/backups/solarsage/db-20260715T032000Z.dump`).
2. Load environment variables safely:
   ```bash
   set +o history
   set -a
   source /opt/solarsage-astro/.env.production
   set +a
   set -o history
   ```
3. Drop and recreate the database schema inside the container:
   ```bash
   export PGPASSWORD="$POSTGRES_PASSWORD"
   # Terminate active connections
   psql -h 127.0.0.1 -p 5433 -U "$POSTGRES_USER" -d postgres -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '${POSTGRES_DB}';"
   # Drop and recreate
   dropdb -h 127.0.0.1 -p 5433 -U "$POSTGRES_USER" "$POSTGRES_DB"
   createdb -h 127.0.0.1 -p 5433 -U "$POSTGRES_USER" "$POSTGRES_DB"
   ```
4. Restore using `pg_restore`:
   ```bash
   pg_restore -h 127.0.0.1 -p 5433 -U "$POSTGRES_USER" -d "$POSTGRES_DB" "/var/backups/solarsage/db-20260715T032000Z.dump"
   ```
5. Unset password variable:
   ```bash
   unset PGPASSWORD
   ```

---

## 5. Database Migrations (Alembic)

To check the current migration head and status, run from `apps/api`:
```bash
cd /opt/solarsage-astro/apps/api
.venv/bin/alembic -c alembic.ini current
```
To manually apply migrations:
```bash
cd /opt/solarsage-astro/apps/api
.venv/bin/alembic -c alembic.ini upgrade head
```

**Rollback Warning:** Database schema rollbacks are not automated. In case of a migration failure, restore the database from the pre-deployment backup dump and check out the previous working Git commit.

---

## 6. Systemd Operations

```bash
# Check service status
sudo systemctl status solarsage-api.service
sudo systemctl status solarsage-sidecar.service
sudo systemctl status solarsage-frontend.service

# View live logs
sudo journalctl -u solarsage-api.service -f
sudo journalctl -u solarsage-sidecar.service -f
sudo journalctl -u solarsage-frontend.service -f

# Check backup timer status
sudo systemctl status solarsage-backup.timer
```

---

## 7. Nginx & SSL Certs

- **Nginx configuration location:** `/etc/nginx/sites-available/astro.vasiliy-ivanov.ru.conf`
- **Check config syntax:** `sudo nginx -t`
- **Reload Nginx:** `sudo systemctl reload nginx`
- **SSL Cert Renewal:** Certbot handles automatic renewal. Check status with:
  `sudo certbot renew --dry-run`

---

## 8. Incident Checklist

1. **API / Sidecar / Frontend down:** Check systemd status and log output for tracebacks or OOM kills.
2. **502 Bad Gateway from Nginx:** Verify FastAPI is running on `127.0.0.1:8000` and Next.js is running on `127.0.0.1:3002`.
3. **Database connection failure:** Verify the Docker container is active: `docker ps -a` and check loopback port `5433` binding.
4. **Cache Policy:** Do not perform a blanket invalidation of database cache tables unless a schema or calculation version contract changes. Cache rows remain valid across restarts.
5. **Telegram Bot Issues:** Ensure the production bot username is `@AstroGrace_Bot`. Do not run the Ductor Telegram bot agent (`vi_astro_bot`) on the production server. The Bot API configuration (description, commands, menu) and avatar must be configured manually via BotFather.
6. **Key Separation:** Ensure the GitHub deploy key (read-only for checkout) is separate from the GitHub Actions deployment private key (used to SSH into the host).
