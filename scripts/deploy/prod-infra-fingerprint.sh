#!/usr/bin/env bash
# ############################################################################
# AI_HEADER: PROD_INFRA_FINGERPRINT — compute deterministic sha256 hash of infra files
# ROLE: Provides a pure, deterministic fingerprint of repository-owned infrastructure.
# DEPENDENCIES: bash, sha256sum, stat, cat, cut, printf
# ############################################################################

# START_MODULE_CONTRACT: M-PROD-INFRA-FINGERPRINT
# purpose: Compute a collision-unambiguous SHA-256 hash over the hardcoded list of infrastructure files.
# owns:
#   - scripts/deploy/prod-infra-fingerprint.sh
# inputs: none
# outputs:
#   - Exactly one 64-character lowercase hex SHA-256 hash printed to stdout.
# dependencies: none
# side_effects: none
# emitted_logs: none
# invariants:
#   - No network, Git operations, file writes, or environment reads.
#   - Exits non-zero on any missing file or unexpected error.
# failure_policy: fails non-zero on missing files or processing errors.
# END_MODULE_CONTRACT: M-PROD-INFRA-FINGERPRINT

# START_MODULE_MAP: M-PROD-INFRA-FINGERPRINT
# public_entrypoints:
#   - main
# semantic_blocks:
#   - FINGERPRINT_GENERATION: core hashing loop
# END_MODULE_MAP: M-PROD-INFRA-FINGERPRINT

# START_BLOCK: FINGERPRINT_GENERATION
set -euo pipefail
set -o pipefail

# Determine repository root relative to script location
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Hardcoded canonical ordered owned paths
# Note: Fingerprint prevalidation also rejects symlinks
FILES=(
  "infra/nginx/00-solarsage-default-reject.conf"
  "infra/nginx/astro.vasiliy-ivanov.ru.conf"
  "infra/certbot/deploy-hooks/20-solarsage-reload-nginx"
  "infra/fail2ban/jail.d/solarsage-sshd.local"
  "infra/production/docker-compose.yml"
  "infra/production/docker-compose.app.yml"
  "infra/production/solarsage-deploy.sudoers"
  "infra/production/solarsage-github-deploy"
  "infra/production/tmpfiles.d/solarsage.conf"
  "infra/ssh/github.com.known_hosts"
  "infra/systemd/solarsage-db.service"
  "infra/systemd/solarsage-backup.service"
  "infra/systemd/solarsage-backup.timer"
  "scripts/deploy/prod-orchestrator.sh"
  "scripts/deploy/prod-host-prepare.sh"
  "scripts/deploy/prod-infra-fingerprint.sh"
  "scripts/deploy/lib/prod-path-transaction.sh"
  "scripts/deploy/prod-github-access.sh"
)

# Set stable locale to avoid stat/other variations
export LC_ALL=C

# Prevalidate the entire ordered file list before producing any stdout
for rel_path in "${FILES[@]}"; do
  full_path="$REPO_ROOT/$rel_path"
  if [ ! -e "$full_path" ] || [ -L "$full_path" ] || [ ! -f "$full_path" ]; then
    echo "Error: File '$rel_path' not found, is a symlink, or is not a regular file." >&2
    exit 1
  fi
done

# Stream framed path/size/content records directly through a pipe/group into sha256sum
# Capture the pipeline result in a shell variable and print it only after the pipeline succeeds.
# No temp file and no filesystem write.
if ! fingerprint=$( {
  for rel_path in "${FILES[@]}"; do
    full_path="$REPO_ROOT/$rel_path"
    printf "%s\0%d\0" "$rel_path" "$(stat -c %s "$full_path")"
    cat "$full_path"
    printf "\0"
  done
} | sha256sum | cut -d' ' -f1 ); then
  exit 1
fi

printf '%s\n' "$fingerprint"
# END_BLOCK: FINGERPRINT_GENERATION
