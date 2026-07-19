#!/bin/bash
# ############################################################################
# AI_HEADER: PROD_ORCHESTRATOR — sole minimal app deploy entrypoint
# ROLE: Manual-gate deploy/rollback/status/backup/restore orchestrator for the
#       canonical Compose app stack using immutable digest-pinned OCI images.
# DEPENDENCIES: bash (5.2), docker compose v2, pg_dump/pg_restore/pg_isready,
#               restic, sha256sum, curl, python3.12, flock
# GRACE_ANCHORS: [ORCH_CLI, ORCH_PREFLIGHT, ORCH_DEPLOY, ORCH_BACKUP, ORCH_RESTORE]
# ############################################################################

# START_MODULE_CONTRACT: M-PROD-ORCHESTRATOR
# purpose: One small linear production app deploy path; the only app deploy
#   entrypoint of the minimal Compose production contour.
# owns:
#   - scripts/deploy/prod-orchestrator.sh
# inputs:
#   - preflight <sha> | deploy <sha> --manual-confirm |
#     rollback <sha> --manual-confirm | status |
#     backup --manual-confirm | restore <dump> --manual-confirm
# outputs: exit 0 on proven success, non-zero otherwise (75 on busy lock).
# dependencies:
#   - /etc/solarsage/compose/docker-compose.app.yml (installed canonical stack)
#   - infra/production/docker-compose.yml (separate DB project, port 5433)
#   - /etc/solarsage/app.env (real non-symlink root:astro 0640)
#   - /run/solarsage-maintenance.lock (existing global maintenance lock)
# side_effects:
#   - docker pull of exact SHA tags with label/digest verification, then
#     docker compose up -d --wait of pinned digest references (deploy/rollback)
#   - pg_dump -Fc + pg_restore --list + SHA256 pair + restic backup
#   - small root-owned active/previous SHA+digest record after proven health
#   - restore rehearsal into a unique throwaway postgres container only
# emitted_logs: none
# invariants:
#   - No build/package-manager on the host; activation uses only pinned
#     registry/repo@sha256:<64 hex> digest references, never mutable tags.
#   - Health identity must equal the requested full SHA on api/sidecar/frontend.
#   - Mutating commands hold a simple non-blocking flock on the global
#     maintenance lock; no journal/state machine is built here.
#   - Proven recovery after failed deploy/rollback leaves the complete record
#     unchanged; same-SHA commands are proven no-ops preserving history.
#   - No down -v, no DB volume mutation, no Nginx/systemd mutation, no arbitrary
#     user-supplied shell, no secret values in stdout/stderr.
#   - status is read-only; backup/restore are explicit manual commands.
# failure_policy: fails closed on any validation, backup, pull, up or health
#   failure; one exact rollback attempt after failed post-change health.
# END_MODULE_CONTRACT: M-PROD-ORCHESTRATOR

# START_MODULE_MAP: M-PROD-ORCHESTRATOR
# public_entrypoints:
#   - main
# semantic_blocks:
#   - ORCH_CLI: argument parsing and confirmation gate
#   - ORCH_PREFLIGHT: env/registry/compose/DB/restic validation
#   - ORCH_DEPLOY: backup, digest resolve, up --wait, health proof, record
#   - ORCH_BACKUP: pg_dump pair + checksum + restic via password file
#   - ORCH_RESTORE: plan + isolated unique-container rehearsal only
# owned_tests:
#   - scripts/deploy/tests/test-prod-orchestrator.sh
# END_MODULE_MAP: M-PROD-ORCHESTRATOR

set -euo pipefail
umask 027

# START_BLOCK: ORCH_CONFIG

APP_COMPOSE="${ORCH_APP_COMPOSE:-/etc/solarsage/compose/docker-compose.app.yml}"
ENV_FILE="${ORCH_ENV_FILE:-/etc/solarsage/app.env}"
STATE_DIR="${ORCH_STATE_DIR:-/var/lib/solarsage/orchestrator}"
BACKUP_DIR="${ORCH_BACKUP_DIR:-/var/backups/solarsage}"
LOCK_FILE="${ORCH_LOCK_FILE:-/run/solarsage-maintenance.lock}"
RECORD_FILE="$STATE_DIR/release-record"
RESTORE_PORT="${ORCH_RESTORE_PORT:-55439}"

# Installed env/credential contract identity (root:astro when installed).
ORCH_ENV_OWNER="${ORCH_ENV_OWNER:-root}"
ORCH_ENV_GROUP="${ORCH_ENV_GROUP:-astro}"

DOCKER="${ORCH_DOCKER:-/usr/bin/docker}"
CURL="${ORCH_CURL:-/usr/bin/curl}"
PYTHON="${ORCH_PYTHON:-/usr/bin/python3.12}"
PG_DUMP="${ORCH_PG_DUMP:-/usr/bin/pg_dump}"
PG_RESTORE="${ORCH_PG_RESTORE:-/usr/bin/pg_restore}"
PG_ISREADY="${ORCH_PG_ISREADY:-/usr/bin/pg_isready}"
PSQL="${ORCH_PSQL:-/usr/bin/psql}"
RESTIC="${ORCH_RESTIC:-/usr/bin/restic}"
SHA256SUM="${ORCH_SHA256SUM:-/usr/bin/sha256sum}"
DATE_BIN="${ORCH_DATE:-/bin/date}"

DIGEST_RE='^[^/[:space:]@]+(/[^/[:space:]@]+)*@sha256:[0-9a-f]{64}$'

fail() {
  echo "Error: $*" >&2
  exit 78
}

usage() {
  echo "Usage: $0 preflight <sha>" >&2
  echo "       $0 deploy <sha> --manual-confirm" >&2
  echo "       $0 rollback <sha> --manual-confirm" >&2
  echo "       $0 status" >&2
  echo "       $0 backup --manual-confirm" >&2
  echo "       $0 restore <dump> --manual-confirm" >&2
  echo "       $0 migrate <sha> --manual-confirm" >&2
  exit 78
}

require_sha() {
  [[ "$1" =~ ^[0-9a-f]{40}$ ]] || fail "invalid SHA format (full 40 lowercase hex required)"
}

require_confirm() {
  [ "${1:-}" = "--manual-confirm" ] || fail "explicit --manual-confirm flag is required"
}

compose() {
  "$DOCKER" compose --env-file "$ENV_FILE" -f "$APP_COMPOSE" "$@"
}

acquire_lock() {
  [ -f "$LOCK_FILE" ] && [ ! -L "$LOCK_FILE" ] || fail "maintenance lock file is missing or not a regular file"
  exec 9>"$LOCK_FILE"
  if ! flock -n 9; then
    echo "Error: another mutating orchestrator operation is running." >&2
    exit 75
  fi
}

# END_BLOCK: ORCH_CONFIG

# START_BLOCK: ORCH_PREFLIGHT

validate_secret_file() {
  # $1 = path of a root:astro 0640-style credential file contract.
  local path="$1"
  [ -f "$path" ] && [ ! -L "$path" ] || fail "credential file $path is missing or not a regular file"
  [ -r "$path" ] || fail "credential file $path is not readable"
  local info
  info=$(stat -c "%U:%G:%a" "$path")
  [ "$info" = "$ORCH_ENV_OWNER:$ORCH_ENV_GROUP:640" ] \
    || fail "credential file $path metadata is $info, expected $ORCH_ENV_OWNER:$ORCH_ENV_GROUP:640"
}

load_env_file() {
  # The requested target SHA is an invocation identity, never an env value.
  # A conflicting RELEASE_SHA inside the env file is a hard failure; a matching
  # one is irrelevant because the requested value is restored after sourcing.
  local preserved_release_sha="${RELEASE_SHA:-}"
  validate_secret_file "$ENV_FILE"
  set +x
  set -a
  # shellcheck source=/dev/null
  . "$ENV_FILE"
  set +a
  if [ -n "$preserved_release_sha" ]; then
    if [ -n "${RELEASE_SHA:-}" ] && [ "$RELEASE_SHA" != "$preserved_release_sha" ]; then
      fail "env file RELEASE_SHA conflicts with the requested target SHA"
    fi
    RELEASE_SHA="$preserved_release_sha"
  fi
  local var
  for var in REGISTRY POSTGRES_USER POSTGRES_PASSWORD POSTGRES_DB \
             DATABASE_URL APP_DOMAIN TELEGRAM_BOT_TOKEN GRACE_USER_SALT \
             CORS_ALLOWED_ORIGINS OPENROUTER_API_KEY \
             RESTIC_REPOSITORY OFFSITE_RESTIC_PASSWORD_FILE \
             EXPECTED_CALCULATION_VERSION; do
    [ -n "${!var:-}" ] || fail "required env value $var is missing"
  done
  case "$REGISTRY" in
    *[!a-z0-9./:_-]*|*":latest"*|*":") fail "registry/repository reference is invalid" ;;
  esac
  validate_secret_file "$OFFSITE_RESTIC_PASSWORD_FILE"
}

preflight_compose() {
  [ -f "$APP_COMPOSE" ] && [ ! -L "$APP_COMPOSE" ] || fail "canonical app compose file is missing"
  if grep -vE '^\s*#' "$APP_COMPOSE" | grep -nE ':latest("|\s|$)'; then
    fail "mutable latest tag found in canonical app compose"
  fi
  if grep -vE '^\s*#' "$APP_COMPOSE" | grep -nE '^\s+-\s+"(0\.0\.0\.0|\[::\])'; then
    fail "non-loopback host binding found in canonical app compose"
  fi
  # Interpolation proof with synthetic valid-format digest references; real
  # digest references are validated exactly after pull at activation time.
  local svc
  for svc in api sidecar frontend; do
    local var
    var=$(printf '%s' "$svc" | tr '[:lower:]' '[:upper:]')_IMAGE
    export "$var"="$REGISTRY/solarsage-$svc@sha256:0000000000000000000000000000000000000000000000000000000000000000"
  done
  compose config --quiet || fail "compose config validation failed"
}

preflight_db() {
  "$PG_ISREADY" -h 127.0.0.1 -p 5433 -U "$POSTGRES_USER" -d "$POSTGRES_DB" >/dev/null 2>&1 \
    || fail "database health check failed on 127.0.0.1:5433"
}

preflight_restic() {
  command -v "$RESTIC" >/dev/null 2>&1 || fail "restic command is absent"
}

run_preflight() {
  require_sha "$RELEASE_SHA"
  load_env_file
  preflight_compose
  preflight_db
  preflight_restic
}

# END_BLOCK: ORCH_PREFLIGHT

# START_BLOCK: ORCH_BACKUP

backup_now() {
  mkdir -p "$BACKUP_DIR"
  chmod 0700 "$BACKUP_DIR"
  local ts dump
  ts=$("$DATE_BIN" -u +%Y%m%dT%H%M%SZ)
  dump="$BACKUP_DIR/db-$ts.dump"
  PGPASSWORD="$POSTGRES_PASSWORD" "$PG_DUMP" \
    -h 127.0.0.1 -p 5433 -U "$POSTGRES_USER" -F c -d "$POSTGRES_DB" -f "$dump" \
    || fail "pg_dump failed"
  "$PG_RESTORE" --list "$dump" >/dev/null || fail "pg_restore --list verification failed"
  (cd "$BACKUP_DIR" && "$SHA256SUM" "$(basename "$dump")" > "$(basename "$dump").sha256") \
    || fail "checksum write failed"
  chmod 0600 "$dump" "$dump.sha256"
  if ! RESTIC_PASSWORD_FILE="$OFFSITE_RESTIC_PASSWORD_FILE" "$RESTIC" backup "$dump" "$dump.sha256" >/dev/null; then
    echo "Error: restic offsite backup failed; local dump and checksum are preserved in $BACKUP_DIR." >&2
    exit 78
  fi
  printf '%s\n' "$dump"
}

# END_BLOCK: ORCH_BACKUP

# START_BLOCK: ORCH_DEPLOY

health_release_sha() {
  # $1 = port, $2 = path; prints .release_sha or empty on any failure.
  "$CURL" -fsS --max-time 5 "http://127.0.0.1:$1$2" 2>/dev/null \
    | "$PYTHON" -c 'import json,sys
try:
    print(json.load(sys.stdin).get("release_sha", ""))
except Exception:
    print("")' 2>/dev/null || true
}

health_field_nonempty() {
  # $1 = port, $2 = path, $3 = json field; prints field value or empty.
  "$CURL" -fsS --max-time 5 "http://127.0.0.1:$1$2" 2>/dev/null \
    | "$PYTHON" -c 'import json,sys
try:
    print(json.load(sys.stdin).get(sys.argv[1], ""))
except Exception:
    print("")' "$3" 2>/dev/null || true
}

prove_health() {
  # $1 = expected full SHA; rc 0 only when all identities match exactly.
  # Sidecar must prove exact ephemeris identity (engine=swieph, canonical
  # calculation version, artifact present; optional exact artifact pins).
  local want="$1"
  [ "$(health_release_sha 8000 /api/health)" = "$want" ] || return 1
  [ "$(health_release_sha 18091 /v1/health)" = "$want" ] || return 1
  [ "$(health_field_nonempty 18091 /v1/health engine)" = "swieph" ] || return 1
  [ "$(health_field_nonempty 18091 /v1/health calculation_version)" = "$EXPECTED_CALCULATION_VERSION" ] || return 1
  [ -n "$(health_field_nonempty 18091 /v1/health ephemeris_artifact_id)" ] || return 1
  [ -n "$(health_field_nonempty 18091 /v1/health ephemeris_manifest_sha256)" ] || return 1
  if [ -n "${EPHEMERIS_EXPECTED_ARTIFACT_ID:-}" ]; then
    [ "$(health_field_nonempty 18091 /v1/health ephemeris_artifact_id)" = "$EPHEMERIS_EXPECTED_ARTIFACT_ID" ] || return 1
  fi
  if [ -n "${EPHEMERIS_EXPECTED_MANIFEST_SHA256:-}" ]; then
    [ "$(health_field_nonempty 18091 /v1/health ephemeris_manifest_sha256)" = "$EPHEMERIS_EXPECTED_MANIFEST_SHA256" ] || return 1
  fi
  [ "$(health_release_sha 3002 /api/release-health)" = "$want" ] || return 1
  return 0
}

resolve_images() {
  # Pull each :<sha> tag once, verify the OCI revision label equals the exact
  # SHA, and resolve the matching RepoDigest. Prints three digest refs.
  local sha="$1" svc tag label digest out=()
  for svc in api sidecar frontend; do
    tag="$REGISTRY/solarsage-$svc:$sha"
    "$DOCKER" pull "$tag" >/dev/null || fail "docker pull failed for $svc"
    label=$("$DOCKER" image inspect --format '{{index .Config.Labels "org.opencontainers.image.revision"}}' "$tag")
    [ "$label" = "$sha" ] || fail "image label revision mismatch for $svc"
    digest=$("$DOCKER" image inspect --format '{{index .RepoDigests 0}}' "$tag")
    [[ "$digest" =~ $DIGEST_RE ]] || fail "malformed or missing RepoDigest for $svc"
    case "$digest" in
      "$REGISTRY/solarsage-$svc@sha256:"*) ;;
      *) fail "RepoDigest repository mismatch for $svc" ;;
    esac
    out+=("$digest")
  done
  printf '%s\n' "${out[@]}"
}

record_field() {
  # $1 = field name; prints value or empty.
  grep -E "^$1=" "$RECORD_FILE" 2>/dev/null | head -1 | cut -d= -f2- || echo ""
}

read_record_tuple() {
  # Sets globals: REC_ACTIVE, REC_ACTIVE_API, REC_ACTIVE_SIDECAR,
  # REC_ACTIVE_FRONTEND, REC_PREVIOUS, REC_PREVIOUS_API,
  # REC_PREVIOUS_SIDECAR, REC_PREVIOUS_FRONTEND.
  # rc 78 on any malformed field format.
  REC_ACTIVE=""; REC_ACTIVE_API=""; REC_ACTIVE_SIDECAR=""; REC_ACTIVE_FRONTEND=""
  REC_PREVIOUS=""; REC_PREVIOUS_API=""; REC_PREVIOUS_SIDECAR=""; REC_PREVIOUS_FRONTEND=""
  if [ -f "$RECORD_FILE" ] && [ ! -L "$RECORD_FILE" ]; then
    REC_ACTIVE=$(record_field active)
    REC_ACTIVE_API=$(record_field active_api_image)
    REC_ACTIVE_SIDECAR=$(record_field active_sidecar_image)
    REC_ACTIVE_FRONTEND=$(record_field active_frontend_image)
    REC_PREVIOUS=$(record_field previous)
    REC_PREVIOUS_API=$(record_field previous_api_image)
    REC_PREVIOUS_SIDECAR=$(record_field previous_sidecar_image)
    REC_PREVIOUS_FRONTEND=$(record_field previous_frontend_image)
    if [ -n "$REC_ACTIVE" ]; then
      [[ "$REC_ACTIVE" =~ ^[0-9a-f]{40}$ ]] || fail "record active SHA is malformed"
      [[ "$REC_ACTIVE_API" =~ $DIGEST_RE ]] || fail "record active api digest is malformed"
      [[ "$REC_ACTIVE_SIDECAR" =~ $DIGEST_RE ]] || fail "record active sidecar digest is malformed"
      [[ "$REC_ACTIVE_FRONTEND" =~ $DIGEST_RE ]] || fail "record active frontend digest is malformed"
    fi
    if [ -n "$REC_PREVIOUS" ]; then
      [[ "$REC_PREVIOUS" =~ ^[0-9a-f]{40}$ ]] || fail "record previous SHA is malformed"
      [[ "$REC_PREVIOUS_API" =~ $DIGEST_RE ]] || fail "record previous api digest is malformed"
      [[ "$REC_PREVIOUS_SIDECAR" =~ $DIGEST_RE ]] || fail "record previous sidecar digest is malformed"
      [[ "$REC_PREVIOUS_FRONTEND" =~ $DIGEST_RE ]] || fail "record previous frontend digest is malformed"
    fi
  fi
}

write_record() {
  # $1..$8 = active sha, 3 active digests, previous sha, 3 previous digests.
  mkdir -p "$STATE_DIR"
  chmod 0700 "$STATE_DIR"
  local tmp
  tmp=$(mktemp "$STATE_DIR/.release-record.XXXXXX")
  chmod 0600 "$tmp"
  {
    printf 'active=%s\n' "$1"
    printf 'active_api_image=%s\n' "$2"
    printf 'active_sidecar_image=%s\n' "$3"
    printf 'active_frontend_image=%s\n' "$4"
    printf 'previous=%s\n' "$5"
    printf 'previous_api_image=%s\n' "$6"
    printf 'previous_sidecar_image=%s\n' "$7"
    printf 'previous_frontend_image=%s\n' "$8"
  } > "$tmp"
  mv -fT "$tmp" "$RECORD_FILE"
  chmod 0600 "$RECORD_FILE"
}

up_wait() {
  # $1..$3 = api/sidecar/frontend digest references. rc of compose up.
  local rc=0
  set +e
  API_IMAGE="$1" SIDECAR_IMAGE="$2" FRONTEND_IMAGE="$3" \
    compose up -d --wait api sidecar frontend >/dev/null
  rc=$?
  set -e
  return $rc
}

validate_activation_config() {
  # $1..$3 = digest references; compose config must validate and reference them exactly.
  local api_img="$1" sidecar_img="$2" frontend_img="$3" config_out
  API_IMAGE="$api_img" SIDECAR_IMAGE="$sidecar_img" FRONTEND_IMAGE="$frontend_img" \
    compose config --quiet || fail "compose config validation failed at activation"
  config_out=$(API_IMAGE="$api_img" SIDECAR_IMAGE="$sidecar_img" FRONTEND_IMAGE="$frontend_img" compose config)
  printf '%s\n' "$config_out" | grep -qF "image: $api_img" \
    || fail "compose does not reference the resolved api digest"
  printf '%s\n' "$config_out" | grep -qF "image: $sidecar_img" \
    || fail "compose does not reference the resolved sidecar digest"
  printf '%s\n' "$config_out" | grep -qF "image: $frontend_img" \
    || fail "compose does not reference the resolved frontend digest"
}

activate_with_digests() {
  # $1 = sha, $2..$4 = digest refs, $5 = fallback sha (may be empty),
  # $6..$8 = fallback digest refs. Never fails the whole script on up --wait
  # nonzero: one exact rollback attempt follows any post-change failure.
  local sha="$1" a_api="$2" a_sidecar="$3" a_frontend="$4"
  local fb_sha="$5" fb_api="$6" fb_sidecar="$7" fb_frontend="$8"
  validate_activation_config "$a_api" "$a_sidecar" "$a_frontend"
  if up_wait "$a_api" "$a_sidecar" "$a_frontend"; then
    if prove_health "$sha"; then
      return 0
    fi
  fi
  echo "Warning: activation or health identity proof failed for $sha" >&2
  if [ -z "$fb_sha" ]; then
    return 1
  fi
  # Exact rollback with recorded digest references; never re-pulls an old tag.
  if up_wait "$fb_api" "$fb_sidecar" "$fb_frontend"; then
    if prove_health "$fb_sha"; then
      return 2
    fi
  fi
  return 1
}

deploy_cmd() {
  local sha="$1"
  require_sha "$sha"
  export RELEASE_SHA="$sha"
  run_preflight
  read_record_tuple
  local active="$REC_ACTIVE" a_api="$REC_ACTIVE_API" a_sidecar="$REC_ACTIVE_SIDECAR" a_frontend="$REC_ACTIVE_FRONTEND"
  if [ "$sha" = "$active" ]; then
    if prove_health "$sha"; then
      echo "Deploy of $sha is a proven no-op (already active)."
      return 0
    fi
    echo "Warning: active release $sha failed health; attempting one recovery." >&2
    local rc_same=0
    activate_with_digests "$sha" "$a_api" "$a_sidecar" "$a_frontend" "" "" "" "" || rc_same=$?
    if [ "$rc_same" -eq 0 ]; then
      echo "Error: active release $sha recovered after re-activation." >&2
      return 78
    fi
    echo "Error: active release $sha could not be recovered. recovery_required." >&2
    return 78
  fi
  echo "Pre-deploy backup starting..."
  backup_now >/dev/null
  echo "Pre-deploy backup completed."
  local resolved_out
  if ! resolved_out=$(resolve_images "$sha"); then
    return 78
  fi
  local digests=()
  while IFS= read -r line; do
    digests+=("$line")
  done <<< "$resolved_out"
  if [ "${#digests[@]}" -ne 3 ]; then
    fail "digest resolution returned an incomplete result"
  fi
  local rc=0
  activate_with_digests "$sha" "${digests[@]}" "$active" "$a_api" "$a_sidecar" "$a_frontend" || rc=$?
  if [ "$rc" -eq 0 ]; then
    write_record "$sha" "${digests[@]}" "$active" "$a_api" "$a_sidecar" "$a_frontend"
    echo "Deploy of $sha completed successfully."
    return 0
  fi
  if [ "$rc" -eq 2 ]; then
    echo "Error: deploy of $sha failed; rollback to previous active $active is proven." >&2
    return 78
  fi
  echo "Error: deploy of $sha failed and rollback could not be proven. recovery_required." >&2
  return 78
}

rollback_cmd() {
  local sha="$1"
  require_sha "$sha"
  export RELEASE_SHA="$sha"
  run_preflight
  read_record_tuple
  local active="$REC_ACTIVE" previous="$REC_PREVIOUS"
  if [ "$sha" = "$active" ]; then
    if prove_health "$sha"; then
      echo "Rollback to $sha is a proven no-op (already active)."
      return 0
    fi
    echo "Error: rollback target $sha is active but unhealthy. recovery_required." >&2
    return 78
  fi
  if [ "$sha" != "$previous" ]; then
    fail "rollback target $sha is not in the recorded release allow-list"
  fi
  local rc=0
  activate_with_digests "$sha" "$REC_PREVIOUS_API" "$REC_PREVIOUS_SIDECAR" "$REC_PREVIOUS_FRONTEND" \
    "$active" "$REC_ACTIVE_API" "$REC_ACTIVE_SIDECAR" "$REC_ACTIVE_FRONTEND" || rc=$?
  if [ "$rc" -eq 0 ]; then
    write_record "$sha" "$REC_PREVIOUS_API" "$REC_PREVIOUS_SIDECAR" "$REC_PREVIOUS_FRONTEND" \
      "$active" "$REC_ACTIVE_API" "$REC_ACTIVE_SIDECAR" "$REC_ACTIVE_FRONTEND"
    echo "Rollback to $sha completed successfully."
    return 0
  fi
  if [ "$rc" -eq 2 ]; then
    echo "Error: rollback to $sha failed; previous active $active is proven." >&2
    return 78
  fi
  echo "Error: rollback to $sha failed and recovery could not be proven. recovery_required." >&2
  return 78
}

status_cmd() {
  read_record_tuple
  echo "recorded active:   ${REC_ACTIVE:-none}"
  [ -z "$REC_ACTIVE" ] || echo "  api=$REC_ACTIVE_API sidecar=$REC_ACTIVE_SIDECAR frontend=$REC_ACTIVE_FRONTEND"
  echo "recorded previous: ${REC_PREVIOUS:-none}"
  [ -z "$REC_PREVIOUS" ] || echo "  api=$REC_PREVIOUS_API sidecar=$REC_PREVIOUS_SIDECAR frontend=$REC_PREVIOUS_FRONTEND"
  echo "api health release_sha:      $(health_release_sha 8000 /api/health)"
  echo "sidecar health release_sha:  $(health_release_sha 18091 /v1/health)"
  echo "frontend health release_sha: $(health_release_sha 3002 /api/release-health)"
  return 0
}

migrate_cmd() {
  # START_FUNCTION_CONTRACT: F-M-PROD-ORCHESTRATOR.migrate_cmd
  # purpose: Run exactly one one-shot Alembic migration pass for a pinned
  #   target release: exact SHA, maintenance lock, env/DB/restic/compose
  #   preflight, digest resolution/verification, pre-migration backup, and only
  #   the one-shot migrate profile with pinned digest env. Never activates app
  #   services, never mutates the release record; never runs automatically.
  # inputs: $1 - full 40-hex target SHA.
  # returns: 0 on a completed one-shot migration run; non-zero otherwise.
  # side_effects: pre-migration backup, digest pulls/inspects, one-shot
  #   migrate container run. No app up, no release record write.
  # END_FUNCTION_CONTRACT: F-M-PROD-ORCHESTRATOR.migrate_cmd
  local sha="$1"
  require_sha "$sha"
  export RELEASE_SHA="$sha"
  run_preflight
  echo "Pre-migration backup starting..."
  backup_now >/dev/null
  echo "Pre-migration backup completed."
  local resolved_out
  if ! resolved_out=$(resolve_images "$sha"); then
    return 78
  fi
  local digests=()
  while IFS= read -r line; do
    digests+=("$line")
  done <<< "$resolved_out"
  if [ "${#digests[@]}" -ne 3 ]; then
    fail "digest resolution returned an incomplete result"
  fi
  validate_activation_config "${digests[@]}"
  if ! RELEASE_SHA="$sha" API_IMAGE="${digests[0]}" SIDECAR_IMAGE="${digests[1]}" FRONTEND_IMAGE="${digests[2]}" \
       compose --profile migrate run --rm migrate; then
    echo "Error: migration run failed for $sha." >&2
    return 78
  fi
  echo "Migration for $sha completed successfully (one-shot profile only; no app activation, no release record change)."
  return 0
}

# END_BLOCK: ORCH_DEPLOY

# START_BLOCK: ORCH_RESTORE

restore_cmd() {
  local dump="$1"
  [ -f "$dump" ] && [ ! -L "$dump" ] || fail "restore dump is missing or not a regular file"
  [ -f "$dump.sha256" ] || fail "restore checksum file is missing"
  (cd "$(dirname "$dump")" && "$SHA256SUM" -c "$(basename "$dump").sha256") >/dev/null \
    || fail "restore dump checksum mismatch"
  "$PG_RESTORE" --list "$dump" >/dev/null || fail "restore dump failed pg_restore --list"
  echo "=== Restore plan (isolated rehearsal only in this slice) ==="
  echo "1. Verify dump pair and pg_restore --list (done)."
  echo "2. Restore into an isolated throwaway postgres:15 container on 127.0.0.1:$RESTORE_PORT."
  echo "3. Sanity-check the rehearsal database and destroy the created container."
  echo "Real production restore requires a separate explicit user command and an accepted runbook."
  # Unique safe name: this invocation never removes a pre-existing container
  # and cleans only the exact container it creates. A simple cleanup trap
  # covers EXIT/INT/TERM/HUP so an aborted rehearsal never leaks the container.
  local name="solarsage-restore-rehearsal-$$"
  local created=0
  rehearsal_cleanup() {
    if [ "$created" -eq 1 ]; then
      if "$DOCKER" rm -f "$name" >/dev/null 2>&1; then
        created=0
      else
        return 1
      fi
    fi
    return 0
  }
  trap 'rehearsal_cleanup || echo "Warning: rehearsal cleanup failed" >&2' EXIT
  trap 'exit 130' INT
  trap 'exit 143' TERM
  trap 'exit 129' HUP
  "$DOCKER" run -d --name "$name" \
    -e POSTGRES_PASSWORD=rehearsal \
    -p "127.0.0.1:$RESTORE_PORT:5432" \
    postgres:15 >/dev/null || fail "rehearsal container start failed"
  created=1
  local i
  for i in $(seq 1 30); do
    if PGPASSWORD=rehearsal "$PG_ISREADY" -h 127.0.0.1 -p "$RESTORE_PORT" -U postgres -d postgres >/dev/null 2>&1; then
      break
    fi
    sleep 1
  done
  if ! PGPASSWORD=rehearsal "$PG_ISREADY" -h 127.0.0.1 -p "$RESTORE_PORT" -U postgres -d postgres >/dev/null 2>&1; then
    fail "rehearsal database never became ready"
  fi
  if ! PGPASSWORD=rehearsal "$PSQL" -h 127.0.0.1 -p "$RESTORE_PORT" -U postgres -d postgres \
    -c "CREATE DATABASE rehearsal" >/dev/null; then
    fail "rehearsal database creation failed"
  fi
  if ! PGPASSWORD=rehearsal "$PG_RESTORE" -h 127.0.0.1 -p "$RESTORE_PORT" -U postgres \
    -d rehearsal --no-owner "$dump" >/dev/null; then
    fail "rehearsal pg_restore failed"
  fi
  if ! PGPASSWORD=rehearsal "$PSQL" -h 127.0.0.1 -p "$RESTORE_PORT" -U postgres -d rehearsal \
    -tAc "SELECT 1" >/dev/null; then
    fail "rehearsal sanity query failed"
  fi
  if ! rehearsal_cleanup; then
    fail "rehearsal container cleanup failed"
  fi
  trap - EXIT INT TERM HUP
  echo "Restore rehearsal OK (isolated target only; production DB untouched)."
  return 0
}

# END_BLOCK: ORCH_RESTORE

# START_BLOCK: ORCH_CLI

main() {
  [ $# -ge 1 ] || usage
  local cmd="$1"
  shift
  case "$cmd" in
    preflight)
      [ $# -eq 1 ] || usage
      export RELEASE_SHA="$1"
      run_preflight
      echo "Preflight OK for $RELEASE_SHA."
      return 0
      ;;
    deploy)
      [ $# -eq 2 ] || usage
      require_confirm "$2"
      acquire_lock
      deploy_cmd "$1"
      ;;
    rollback)
      [ $# -eq 2 ] || usage
      require_confirm "$2"
      acquire_lock
      rollback_cmd "$1"
      ;;
    status)
      [ $# -eq 0 ] || usage
      status_cmd
      ;;
    backup)
      [ $# -eq 1 ] || usage
      require_confirm "$1"
      acquire_lock
      RELEASE_SHA="0000000000000000000000000000000000000000"
      load_env_file
      preflight_db
      preflight_restic
      local dump
      dump=$(backup_now)
      echo "Backup completed: $(basename "$dump") (+sha256, restic)."
      return 0
      ;;
    restore)
      [ $# -eq 2 ] || usage
      require_confirm "$2"
      acquire_lock
      restore_cmd "$1"
      ;;
    migrate)
      [ $# -eq 2 ] || usage
      require_confirm "$2"
      acquire_lock
      migrate_cmd "$1"
      ;;
    *)
      usage
      ;;
  esac
}

main "$@"

# END_BLOCK: ORCH_CLI
