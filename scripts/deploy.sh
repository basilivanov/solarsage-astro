#!/usr/bin/env bash
# STATUS: stale (pre-W-1.0).
#
# This script predates the Phase-1 stack lockdown and references infra that
# does not exist in the current canon:
#   - apps/web/ (the web app lives at the repo root, not under apps/web)
#   - systemd units astro-api / astro-worker / astro-web (no such units)
#   - Makefile targets `make install` / `make migrate` (apps/api uses
#     pyproject + alembic directly; bootstrap.sh is the canonical entry)
#   - VDS-hosted deployment model (the project deploys on Vercel; the
#     backend deployment surface will be re-derived in W-DEPLOY, TBD).
#
# Do NOT use as a runbook. The authoritative deployment flow will be
# defined in a dedicated W-DEPLOY wave (anchor in development-plan.xml).
# Until then this script is retained for product-history context only.
#
# Guard: refuse to run unless the operator explicitly opts into the stale
# behaviour. This prevents accidental execution from CI or muscle memory.
set -euo pipefail

if [[ "${GRACE_DEPLOY_ALLOW_STALE:-0}" != "1" ]]; then
  echo "[deploy] refusing to run: this script is marked stale (pre-W-1.0)." >&2
  echo "[deploy] see header for details. set GRACE_DEPLOY_ALLOW_STALE=1 to override." >&2
  exit 1
fi

cd "$(dirname "$0")/.."

echo "[deploy] git pull"
git pull --ff-only

echo "[deploy] backend deps + migrate"
( cd apps/api && make install && make migrate )

echo "[deploy] frontend build"
( cd apps/web && pnpm install --frozen-lockfile && pnpm build )

echo "[deploy] restart services"
sudo systemctl restart astro-api astro-worker astro-web

echo "[deploy] done."
sudo systemctl status astro-api --no-pager | head -n 5
