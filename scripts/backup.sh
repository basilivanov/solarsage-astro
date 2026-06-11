#!/usr/bin/env bash

// ############################################################################
// AI_HEADER: MODULE_SCRIPTS_BACKUP
// ROLE: Tooling script
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-GUARDRAILS-TOOLING
// ############################################################################

// START_MODULE_CONTRACT
// purpose: Tooling script — scripts/backup.sh
// owns:
//   - scripts/backup.sh
// inputs: varies
// outputs: varies
// dependencies: local modules
// side_effects: varies
// emitted_logs: n/a
// invariants:
//   - n/a
// failure_policy: log and raise
// END_MODULE_CONTRACT

// START_MODULE_MAP
// mapping:
//   - export: default
//     contract: main export
// END_MODULE_MAP

# Ежедневный бэкап: pg_dump + копия dump.rdb. Хранит 14 дней.
set -euo pipefail
cd "$(dirname "$0")/.."
set -a; source .env; set +a

DEST=/var/backups/astro
DATE=$(date -u +%Y%m%d-%H%M)
mkdir -p "$DEST"

PGPASSWORD=$POSTGRES_PASSWORD pg_dump \
  -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" \
  -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
  --no-owner --format=custom \
  -f "$DEST/db-$DATE.dump"

if [ -f /var/lib/redis/dump.rdb ]; then
  cp /var/lib/redis/dump.rdb "$DEST/redis-$DATE.rdb"
fi

# rotation: keep 14 days
find "$DEST" -type f -mtime +14 -delete

echo "[backup] $DEST"
ls -lh "$DEST" | tail -n 5
