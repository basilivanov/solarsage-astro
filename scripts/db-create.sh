#!/usr/bin/env bash

# ############################################################################
# AI_HEADER: MODULE_SCRIPTS_DB_CREATE
# ROLE: Tooling script
# DEPENDENCIES: local modules
# GRACE_ANCHORS: []
# SLICE: SLICE-GUARDRAILS-TOOLING
# #########################################// START_MODULE_CONTRACT
# purpose: DB access for db-create.sh
# owns:
#   - scripts/db-create.sh
# inputs: Query params, models
# outputs: Records / query results
# dependencies: local modules
# side_effects: Database reads/writes
# emitted_logs: n/a (pure)
# invariants:
#   - n/a
# failure_policy: log and raise
# END_MODULE_CONTRACT
# Create Postgres role + database for the dev-loop.
# Works against the docker-compose stack at infra/docker-compose.yml
# (container: astro-dev-postgres, default user/db: astro/astro).
#
# Reads POSTGRES_USER / POSTGRES_PASSWORD / POSTGRES_DB from .env if present,
# otherwise falls back to compose defaults.
#
# NOTE: This is a dev-only helper. Production provisioning is W-DEPLOY scope.

set -euo pipefail
cd "$(dirname "$0")/.."

if [[ -f .env ]]; then
  set -a; source .env; set +a
fi

: "${POSTGRES_USER:=astro}"
: "${POSTGRES_PASSWORD:=astro}"
: "${POSTGRES_DB:=astro}"

CONTAINER="${POSTGRES_CONTAINER:-astro-dev-postgres}"

if ! docker ps --format '{{.Names}}' | grep -qx "$CONTAINER"; then
  echo "ERROR: container '$CONTAINER' is not running."
  echo "Hint: 'docker compose -f infra/docker-compose.yml up -d' first."
  exit 1
fi

# Role
docker exec -i "$CONTAINER" psql -U postgres <<SQL
DO \$\$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='${POSTGRES_USER}') THEN
    CREATE ROLE ${POSTGRES_USER} LOGIN PASSWORD '${POSTGRES_PASSWORD}';
  END IF;
END
\$\$;
SQL

# Database
EXISTS=$(docker exec -i "$CONTAINER" psql -U postgres -tAc \
  "SELECT 1 FROM pg_database WHERE datname='${POSTGRES_DB}'" || true)
if [[ "$EXISTS" != "1" ]]; then
  docker exec -i "$CONTAINER" createdb -U postgres -O "${POSTGRES_USER}" "${POSTGRES_DB}"
fi

echo "OK: role=${POSTGRES_USER} db=${POSTGRES_DB} container=${CONTAINER}"
