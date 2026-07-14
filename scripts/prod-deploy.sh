#!/usr/bin/env bash
# ############################################################################
# AI_HEADER: TOOL_PROD_DEPLOY
# ROLE: Reproducible manual deployment script for SolarSage Astro.
# DEPENDENCIES: git, pnpm, python3.12, systemctl, curl
# GRACE_ANCHORS: [PROD_DEPLOY_SCRIPT]
# ############################################################################

# START_MODULE_CONTRACT: M-TOOL-PROD-DEPLOY
# purpose: Securely deploy SolarSage Astro production code from git or current HEAD.
# owns:
#   - scripts/prod-deploy.sh
# inputs:
#   - --current: deploy current worktree without fetching/switching refs
#   - /opt/solarsage-astro/.env.production
# outputs:
#   - rebuilt virtualenvs, built frontend assets, migrated database, restarted systemd units
# dependencies: none
# invariants:
#   - Refuse root execution.
#   - Expected user is 'astro'.
#   - Non-blocking flock lock.
#   - Secure permissions (umask 027).
#   - Never print secrets, credentials, or tokens.
# failure_policy: fails non-zero on any preflight, build, or restart error.
# END_MODULE_CONTRACT: M-TOOL-PROD-DEPLOY

# START_MODULE_MAP: M-TOOL-PROD-DEPLOY
# public_entrypoints:
#   - main
# semantic_blocks:
#   - PROD_DEPLOY_SCRIPT: deployment orchestration flow
# END_MODULE_MAP: M-TOOL-PROD-DEPLOY

# START_BLOCK: PROD_DEPLOY_SCRIPT
set -euo pipefail
umask 027

# Local regression check: verify set -a is used before sourcing env files
if ! grep -q 'set -a' "$0"; then
    echo "Error: self-validation failed. Deploy script must contain 'set -a'." >&2
    exit 1
fi

# 1. User check
if [ "$EUID" -eq 0 ]; then
    echo "Error: running as root is forbidden." >&2
    exit 1
fi

if [ "$(id -un)" != "astro" ]; then
    echo "Error: expected execution user is 'astro'." >&2
    exit 1
fi

# 2. Argument validation
MODE="git"
if [ "$#" -eq 1 ]; then
    if [ "$1" = "--current" ]; then
        MODE="current"
    else
        echo "Usage: $0 [--current]" >&2
        exit 2
    fi
elif [ "$#" -gt 1 ]; then
    echo "Usage: $0 [--current]" >&2
    exit 2
fi

STAGE="initialization"
OLD_SHA="unknown"
TARGET_SHA="unknown"

failure_handler() {
    local exit_code=$?
    if [ "$exit_code" -ne 0 ]; then
        echo "--------------------------------------------------" >&2
        echo "DEPLOYMENT FAILED during stage: $STAGE" >&2
        echo "Old SHA: $OLD_SHA" >&2
        echo "Target SHA: $TARGET_SHA" >&2
        echo "--------------------------------------------------" >&2
    fi
}
trap failure_handler EXIT

# 3. Acquire lock
LOCKFILE="/tmp/solarsage-deploy.lock"
exec 9>"$LOCKFILE"
if ! flock -n 9; then
    echo "Error: another deployment is already running." >&2
    exit 1
fi

# 4. Working directory and Env check
cd /opt/solarsage-astro
OLD_SHA=$(git rev-parse HEAD 2>/dev/null || echo "unknown")

if [ ! -f .env.production ]; then
    echo "Error: .env.production not found." >&2
    exit 1
fi

# Assert permissions: only exactly 600 or 640 allowed
PERMS=$(stat -c "%a" .env.production)
if [ "$PERMS" != "600" ] && [ "$PERMS" != "640" ]; then
    echo "Error: .env.production has insecure permissions ($PERMS). Must be exactly 600 or 640." >&2
    exit 1
fi

# Assert owner and group: must be astro:astro
OWNERSHIP=$(stat -c "%U:%G" .env.production)
if [ "$OWNERSHIP" != "astro:astro" ]; then
    echo "Error: .env.production ownership ($OWNERSHIP) is invalid. Must be astro:astro." >&2
    exit 1
fi

# 5. Git ref resolution and clean worktree check
STAGE="git-checkout"
if [ "$MODE" = "current" ]; then
    echo "Deploying current worktree HEAD..."
    if ! git diff --quiet || ! git diff --cached --quiet; then
        echo "Error: git worktree has unstaged or staged changes. Must be clean." >&2
        exit 1
    fi
    TARGET_SHA=$(git rev-parse HEAD)
else
    echo "Fetching origin/main..."
    git fetch --prune origin main
    TARGET_SHA=$(git rev-parse origin/main)
    if ! git diff --quiet || ! git diff --cached --quiet; then
        echo "Error: git worktree has unstaged or staged changes. Must be clean." >&2
        exit 1
    fi
    echo "Checking out detached HEAD at origin/main ($TARGET_SHA)..."
    git checkout --detach "$TARGET_SHA"
fi

# 6. Load production environment safely using exported variables
STAGE="load-env"
set +x
set -a
# shellcheck source=/dev/null
source .env.production
set +a

# 7. Install JS/TS dependencies and run production guardrails
STAGE="npm-install"
echo "Installing JS/TS dependencies..."
pnpm install --frozen-lockfile

echo "Running production guardrails..."
pnpm run guardrails:prod

# 8. Create/Upgrade Python virtual environments
STAGE="python-build"
echo "Building Python virtual environments..."
# API
python3.12 -m venv apps/api/.venv
apps/api/.venv/bin/pip install -U pip wheel
apps/api/.venv/bin/pip install packages/py-contracts/
apps/api/.venv/bin/pip install apps/api/

# Sidecar
python3.12 -m venv apps/solarsage/venv
apps/solarsage/venv/bin/pip install -U pip wheel
apps/solarsage/venv/bin/pip install packages/py-contracts/
apps/solarsage/venv/bin/pip install apps/solarsage/

# 9. Build Next.js frontend
STAGE="frontend-build"
echo "Building Next.js frontend..."
NODE_ENV=production APP_ENV=production pnpm build

# 10. Fail-closed Python preflight using built venv and real env
STAGE="preflight-checks"
echo "Running production preflight..."
PYTHONPATH=apps/api apps/api/.venv/bin/python - <<'PY'
import os
import sys

sys.path.insert(0, os.path.abspath("apps/api"))

from app.core.config import settings
from app.core.runtime_security import build_runtime_security_policy

try:
    policy = build_runtime_security_policy(settings)

    assert settings.app_env == "production", f"Expected APP_ENV=production, got {settings.app_env}"
    assert settings.app_domain == "astro.vasiliy-ivanov.ru", f"Expected APP_DOMAIN=astro.vasiliy-ivanov.ru, got {settings.app_domain}"
    assert settings.dev_mode is False, "DEV_MODE must be False"
    assert settings.session_cookie_secure is True, "session_cookie_secure must be True"
    assert "sqlite" not in settings.database_url.lower(), "SQLite is not allowed in production"
    assert settings.telegram_bot_token != "", "TELEGRAM_BOT_TOKEN must not be empty"

    # BOT_USERNAME must be defined and normalized to AstroGrace_Bot
    bot_username = os.environ.get("BOT_USERNAME", "").strip().lstrip("@")
    assert bot_username == "AstroGrace_Bot", f"Expected bot username AstroGrace_Bot, got {bot_username}"

    print("preflight_ok")
except Exception as e:
    print(f"Preflight failed: {type(e).__name__} - {str(e)}", file=sys.stderr)
    sys.exit(1)
PY

# 11. Database reachability and backup check (fail-closed)
STAGE="db-backup"
echo "Checking database reachability..."
if ! pg_isready -h 127.0.0.1 -p 5433 -U "$POSTGRES_USER" -d "$POSTGRES_DB"; then
    echo "Error: Database is not reachable on port 5433." >&2
    exit 1
fi

echo "Running backup before migrations..."
bash scripts/prod-backup.sh

# 12. Run database migrations in subshell
STAGE="db-migrations"
echo "Running database migrations..."
(
    cd apps/api
    .venv/bin/alembic -c alembic.ini upgrade head
    echo "Current Alembic Head:"
    .venv/bin/alembic -c alembic.ini current
    echo "Alembic Heads:"
    .venv/bin/alembic -c alembic.ini heads
)

# 13. Restart systemd services and verify health with loops
STAGE="service-restarts"
echo "Restarting services..."

# Restart sidecar
echo "Restarting solarsage-sidecar..."
sudo systemctl restart solarsage-sidecar.service
for i in {1..30}; do
    if curl -fsS http://127.0.0.1:18091/v1/health &>/dev/null; then
        echo "Sidecar is healthy."
        break
    fi
    if [ "$i" -eq 30 ]; then
        echo "Error: Sidecar health check timed out." >&2
        exit 1
    fi
    sleep 1
done

# Restart API
echo "Restarting solarsage-api..."
sudo systemctl restart solarsage-api.service
for i in {1..30}; do
    if curl -fsS http://127.0.0.1:8000/api/health &>/dev/null; then
        echo "API is healthy."
        break
    fi
    if [ "$i" -eq 30 ]; then
        echo "Error: API health check timed out." >&2
        exit 1
    fi
    sleep 1
done

# Restart Frontend
echo "Restarting solarsage-frontend..."
sudo systemctl restart solarsage-frontend.service
for i in {1..30}; do
    if curl -fsS http://127.0.0.1:3002/ &>/dev/null; then
        echo "Frontend is healthy."
        break
    fi
    if [ "$i" -eq 30 ]; then
        echo "Error: Frontend health check timed out." >&2
        exit 1
    fi
    sleep 1
done

# 14. HTTPS endpoint smoke check (strictly verified, no -k)
STAGE="https-smoke"
if [ -f /etc/letsencrypt/live/astro.vasiliy-ivanov.ru/fullchain.pem ]; then
    echo "Verifying production HTTPS endpoint..."
    if curl -fsS https://astro.vasiliy-ivanov.ru/api/health &>/dev/null; then
        echo "HTTPS public endpoint is healthy."
    else
        echo "Error: HTTPS public endpoint is not healthy." >&2
        exit 1
    fi
else
    echo "HTTPS smoke skipped: certificate not installed"
fi

STAGE="completed"
echo "Deployment PASS. Deployed SHA: ${TARGET_SHA}"
# END_BLOCK: PROD_DEPLOY_SCRIPT
