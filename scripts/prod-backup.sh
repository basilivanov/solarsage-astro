#!/usr/bin/env bash
# ############################################################################
# AI_HEADER: TOOL_PROD_BACKUP
# ROLE: Daily PostgreSQL database backup automation script.
# DEPENDENCIES: pg_dump, docker-compose, find
# GRACE_ANCHORS: [BACKUP_SCRIPT]
# ############################################################################

# START_MODULE_CONTRACT: M-TOOL-PROD-BACKUP
# purpose: Safely backup production database to /var/backups/solarsage.
# owns:
#   - scripts/prod-backup.sh
# inputs:
#   - /opt/solarsage-astro/.env.production
# outputs:
#   - database dump and checksum files under /var/backups/solarsage
# dependencies: none
# invariants:
#   - Strict permissions (umask 077).
#   - No secret leaking in logs or outputs.
#   - Retention period: 14 days.
# failure_policy: fails non-zero on any error, cleaning up partial files.
# END_MODULE_CONTRACT: M-TOOL-PROD-BACKUP

# START_MODULE_MAP: M-TOOL-PROD-BACKUP
# public_entrypoints:
#   - main
# semantic_blocks:
#   - BACKUP_SCRIPT: backup execution flow
# END_MODULE_MAP: M-TOOL-PROD-BACKUP

# START_BLOCK: BACKUP_SCRIPT
set -euo pipefail
umask 077

ENV_FILE="/opt/solarsage-astro/.env.production"
BACKUP_DIR="/var/backups/solarsage"

if [ ! -f "$ENV_FILE" ]; then
    echo "Error: Env file $ENV_FILE not found." >&2
    exit 1
fi

TIMESTAMP=$(date -u +"%Y%m%dT%H%M%SZ")
DUMP_FILE="$BACKUP_DIR/db-$TIMESTAMP.dump"
SHA_FILE="$DUMP_FILE.sha256"

cleanup() {
    local exit_code=$?
    unset PGPASSWORD
    if [ "$exit_code" -ne 0 ]; then
        echo "Backup failed with exit code $exit_code. Cleaning up partial files..." >&2
        rm -f "$DUMP_FILE" "$SHA_FILE"
    fi
}
trap cleanup EXIT

# Load variables safely using set -a / set +a without echoing them
set +x
set -a
# shellcheck source=/dev/null
source "$ENV_FILE"
set +a

# Required variables check
: "${POSTGRES_USER:?postgres user required}"
: "${POSTGRES_PASSWORD:?postgres password required}"
: "${POSTGRES_DB:?postgres db required}"

mkdir -p "$BACKUP_DIR"

# Perform backup using pg_dump on host, connecting to loopback 5433
export PGPASSWORD="$POSTGRES_PASSWORD"
if ! pg_dump -h 127.0.0.1 -p 5433 -U "$POSTGRES_USER" -F c -d "$POSTGRES_DB" -f "$DUMP_FILE"; then
    echo "Error: pg_dump failed." >&2
    exit 1
fi

# Generate checksum
if ! sha256sum "$DUMP_FILE" > "$SHA_FILE"; then
    echo "Error: sha256sum generation failed." >&2
    exit 1
fi

# Cleanup old backups (retention 14 days)
find "$BACKUP_DIR" -type f \( -name "db-*.dump" -o -name "db-*.dump.sha256" \) -mtime +14 -delete

echo "Backup completed successfully."
# END_BLOCK: BACKUP_SCRIPT
