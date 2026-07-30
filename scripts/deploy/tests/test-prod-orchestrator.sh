#!/usr/bin/env bash
# ############################################################################
# AI_HEADER: TEST_PROD_ORCHESTRATOR — focused orchestrator contract harness
# ROLE: Sandbox contract checks for scripts/deploy/prod-orchestrator.sh:
#       exact CLI/confirmation/SHA validation, installed-boundary env contract,
#       digest-pinned activation (label/RepoDigest verification, stored-digest
#       rollback, byte-identical record after proven recovery), maintenance
#       flock, backup ordering with password-file contract, unique-container
#       restore rehearsal, secret-canary absence and deterministic exit codes.
# DEPENDENCIES: bash (5.2), sha256sum, flock
# GRACE_ANCHORS: [ORCH_HARNESS]
# ############################################################################

# START_MODULE_CONTRACT: M-TEST-PROD-ORCHESTRATOR
# purpose: Focused fail-closed contract matrix for prod-orchestrator.sh.
# owns:
#   - scripts/deploy/tests/test-prod-orchestrator.sh
# inputs: none
# outputs: exit 0 when all checks pass; exit 1 with named failures otherwise
# dependencies: bash, sha256sum, flock
# side_effects: Creates and removes one private /tmp sandbox; never touches
#   real /etc, /var, /opt runtime state, docker daemon, DB or registry.
# emitted_logs: none
# invariants:
#   - All external commands are sandbox mocks with argv/env ledgers.
#   - Exit codes are captured directly (if cmd; then rc=0; else rc=$?; fi).
#   - Secret canaries must never appear in outputs or ledgers.
#   - The real canonical compose file is read but never modified.
# failure_policy: Failed checks are named on stderr and in the final list.
# END_MODULE_CONTRACT: M-TEST-PROD-ORCHESTRATOR

# START_MODULE_MAP: M-TEST-PROD-ORCHESTRATOR
# public_entrypoints:
#   - main
# semantic_blocks:
#   - HARNESS_SETUP: sandbox layout, mocks, env file with canaries
#   - CONTRACT_CASES: OC01..OC31 orchestrator matrix
# END_MODULE_MAP: M-TEST-PROD-ORCHESTRATOR

set -euo pipefail
umask 027

# START_BLOCK: HARNESS_SETUP

TEST_DIR=$(mktemp -d "/tmp/solarsage-orchestrator-test.XXXXXX")
chmod 0700 "$TEST_DIR"
cleanup_sandbox() {
  rm -rf -- "$TEST_DIR"
}
trap cleanup_sandbox EXIT

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
REPO_ROOT=$(cd "$SCRIPT_DIR/../../.." && pwd)
ORCH="$REPO_ROOT/scripts/deploy/prod-orchestrator.sh"
CURRENT_USER=$(id -un)
CURRENT_GROUP=$(id -gn)
export TEST_DIR

SHA_A="a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2"
SHA_B="b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3"
SHA_C="cccccccccccccccccccccccccccccccccccccccc"
CANARY_TG="CANARY_TG_TOKEN_9f8e7d6c5b4a"
CANARY_OR="CANARY_OR_KEY_1a2b3c4d5e6f"
CANARY_PW="CANARY_DB_PASSWORD_7g8h9i"

fail() {
  echo "FAIL: $*" >&2
  exit 1
}

case_fail() {
  echo "FAIL: $*" >&2
  return 1
}

digest_for() {
  # Deterministic fixture digest ref: $1 = svc, $2 = sha.
  local prefix="${2:0:8}" hex=""
  local i
  for i in 1 2 3 4 5 6 7 8; do hex+="$prefix"; done
  printf 'ghcr.io/test/solarsage-%s@sha256:%s\n' "$1" "$hex"
}

mkdir -p "$TEST_DIR/bin" "$TEST_DIR/state" "$TEST_DIR/backups"

# --- Mock docker: argv/env ledgers, pull/inspect digest flow, compose config/up ---
cat > "$TEST_DIR/bin/docker" <<'MOCK'
#!/usr/bin/env bash
set -euo pipefail
TEST_DIR="${SS_MOCK_ROOT:?}"
printf '%s\n' "$*" >> "$TEST_DIR/ledger"
if [ "${1:-}" = "pull" ]; then
  tag="${2:-}"
  [ -f "$TEST_DIR/fail-pull" ] && exit 1
  case "$tag" in
    ghcr.io/test/solarsage-api:*|ghcr.io/test/solarsage-sidecar:*|ghcr.io/test/solarsage-frontend:*) ;;
    *) exit 2 ;;
  esac
  svc=$(printf '%s' "$tag" | sed -E 's|.*solarsage-([^:]+):.*|\1|')
  sha="${tag##*:}"
  digest="ghcr.io/test/solarsage-$svc@sha256:$(printf '%s' "$sha" | cut -c1-8 | awk '{printf $1$1$1$1$1$1$1$1}')"
  printf '%s %s\n' "$digest" "$sha" >> "$TEST_DIR/digest-map"
  exit 0
fi
if [ "${1:-}" = "image" ] && [ "${2:-}" = "inspect" ] && [ "${3:-}" = "--format" ]; then
  fmt="${4:-}"; tag="${5:-}"
  svc=$(printf '%s' "$tag" | sed -E 's|.*solarsage-([^:]+):.*|\1|')
  sha="${tag##*:}"
  case "$fmt" in
    *Config.Labels*)
      if [ -f "$TEST_DIR/fail-label-for" ] && [ "$(cat "$TEST_DIR/fail-label-for")" = "$svc" ]; then
        printf 'deadbeefdeadbeefdeadbeefdeadbeefdeadbeef\n'
      else
        printf '%s\n' "$sha"
      fi
      exit 0
      ;;
    *RepoDigests*)
      if [ -f "$TEST_DIR/fail-digest-for" ] && [ "$(cat "$TEST_DIR/fail-digest-for")" = "$svc" ]; then
        printf 'garbage-not-a-digest\n'
      else
        printf 'ghcr.io/test/solarsage-%s@sha256:%s\n' "$svc" "$(printf '%s' "$sha" | cut -c1-8 | awk '{printf $1$1$1$1$1$1$1$1}')"
      fi
      exit 0
      ;;
  esac
  exit 2
fi
if [ "${1:-}" = "inspect" ]; then
  # Plain container inspect: solarsage-api running state + Config.Image.
  printf 'inspect %s\n' "${*:2}" >> "$TEST_DIR/inspect-ledger"
  [ -f "$TEST_DIR/fail-inspect" ] && exit 1
  img=$(cat "$TEST_DIR/active-api-image" 2>/dev/null || echo "")
  [ -n "$img" ] || exit 1
  running="true"
  [ -f "$TEST_DIR/api-stopped" ] && running="false"
  printf '%s %s\n' "$running" "$img"
  exit 0
fi
args="$*"
case "$args" in
  "compose --env-file "*" -f "*" config --quiet")
    [ -f "$TEST_DIR/env-file-ok" ] || exit 1
    # Contract: the canonical compose interpolates ${RELEASE_SHA:?...}; fail
    # exactly like real compose when it is not exported into our environment.
    compose_file=$(printf '%s' "$args" | sed -n 's/.* -f \([^ ]*\) .*/\1/p')
    if [ -n "$compose_file" ] && grep -qF '${RELEASE_SHA:?' "$compose_file" && [ -z "${RELEASE_SHA:-}" ]; then
      exit 1
    fi
    exit 0
    ;;
  "compose --env-file "*" -f "*" config")
    printf 'image: %s\n' "${API_IMAGE:?}"
    printf 'image: %s\n' "${SIDECAR_IMAGE:?}"
    printf 'image: %s\n' "${FRONTEND_IMAGE:?}"
    printf 'image: %s\n' "${API_IMAGE:?}"
    exit 0
    ;;
  "compose --env-file "*" -f "*" up -d --wait api sidecar frontend")
    env | grep -E '^(API|SIDECAR|FRONTEND)_IMAGE=' >> "$TEST_DIR/env-ledger" || true
    env | grep -E '^RELEASE_SHA=' >> "$TEST_DIR/env-ledger" || true
    sha=$(grep -F "${API_IMAGE:?} " "$TEST_DIR/digest-map" | head -1 | awk '{print $2}' || echo "")
    [ -n "$sha" ] || exit 3
    if [ -f "$TEST_DIR/fail-up-for" ] && [ "$(cat "$TEST_DIR/fail-up-for")" = "$sha" ]; then
      exit 1
    fi
    [ -f "$TEST_DIR/fail-up" ] && exit 1
    printf '%s' "$sha" > "$TEST_DIR/active-sha"
    exit 0
    ;;
  "compose --env-file "*" -f "*" ps")
    printf 'solarsage-api running\n'
    exit 0
    ;;
  "compose --env-file "*" -f "*" --profile migrate run --rm migrate alembic current --check-heads")
    env | grep -E '^(API|SIDECAR|FRONTEND)_IMAGE=' >> "$TEST_DIR/env-ledger" || true
    [ -f "$TEST_DIR/fail-check-heads" ] && exit 1
    exit 0
    ;;
  "compose --env-file "*" -f "*" --profile migrate run --rm migrate")
    env | grep -E '^(API|SIDECAR|FRONTEND)_IMAGE=' >> "$TEST_DIR/env-ledger" || true
    [ -f "$TEST_DIR/fail-migrate" ] && exit 1
    exit 0
    ;;
  "compose --env-file "*" -f "*" --profile billing-rebill run --rm --no-deps billing-rebill")
    env | grep -E '^(API|SIDECAR|FRONTEND)_IMAGE=' >> "$TEST_DIR/env-ledger" || true
    env | grep -E '^RELEASE_SHA=' >> "$TEST_DIR/env-ledger" || true
    [ -f "$TEST_DIR/fail-billing-rebill" ] && exit 1
    # Mirror the real job contract: canonical structured envelope, never raw print.
    printf '%s\n' '{"event":"billing.rebill_skipped","level":"info","msg":"rebill skipped: YOOKASSA_RECURRENT_ENABLED=false","module":"M-JOBS-BILLING-REBILL","block":"REBILL_JOB","slice":"W-6.1"}'
    exit 0
    ;;
  "run -d --name solarsage-restore-rehearsal-"*)
    name=""
    prev=""
    for a in "$@"; do
      if [ "$prev" = "--name" ]; then name="$a"; fi
      prev="$a"
    done
    [ -n "$name" ] || exit 2
    printf '%s\n' "$name" >> "$TEST_DIR/containers"
    exit 0
    ;;
  "rm -f solarsage-restore-rehearsal-"*)
    [ -f "$TEST_DIR/fail-rm-rehearsal" ] && exit 1
    name="${args#rm -f }"
    { grep -vxF "$name" "$TEST_DIR/containers" || true; } > "$TEST_DIR/containers.tmp"
    mv "$TEST_DIR/containers.tmp" "$TEST_DIR/containers"
    exit 0
    ;;
  "rm -f "*)
    exit 0
    ;;
  *)
    exit 2
    ;;
esac
MOCK

# --- Mock curl: per-port health identity from the active-sha registry ---
cat > "$TEST_DIR/bin/curl" <<'MOCK'
#!/usr/bin/env bash
set -euo pipefail
TEST_DIR="${SS_MOCK_ROOT:?}"
url="${@: -1}"
printf 'curl %s\n' "$url" >> "$TEST_DIR/ledger"
active=$(cat "$TEST_DIR/active-sha" 2>/dev/null || echo "")
if [ -f "$TEST_DIR/fail-health-all" ]; then
  active="dddddddddddddddddddddddddddddddddddddddd"
elif [ -f "$TEST_DIR/fail-health-for" ]; then
  if [ "$active" = "$(cat "$TEST_DIR/fail-health-for")" ]; then
    active="dddddddddddddddddddddddddddddddddddddddd"
  fi
fi
case "$url" in
  *:8000/api/geo/autocomplete*)
    if [ -f "$TEST_DIR/fail-smoke-for" ] && [ "$active" = "$(cat "$TEST_DIR/fail-smoke-for")" ]; then
      exit 22
    fi
    printf '[{"name":"Moscow","country":"Russia","lat":55.75,"lon":37.62,"timezone_id":"Europe/Moscow"}]\n' ;;
  *:8000/api/health)
    printf '{"status":"ok","version":"0.1.0","git_sha":"g","release_sha":"%s"}\n' "$active" ;;
  *:18091/v1/health)
    printf '{"ok":true,"version":"g","engine":"swieph","calculation_version":"ss-calc-1.3.0","ephemeris_artifact_id":"se-test-artifact","ephemeris_manifest_sha256":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa","fallback":false,"release_sha":"%s"}\n' "$active" ;;
  *:3002/api/release-health)
    printf '{"status":"ok","release_sha":"%s"}\n' "$active" ;;
  *:3002/)
    if [ -f "$TEST_DIR/fail-smoke-for" ] && [ "$active" = "$(cat "$TEST_DIR/fail-smoke-for")" ]; then
      exit 22
    fi
    printf '<html>ok</html>\n' ;;
  *)
    exit 22 ;;
esac
exit 0
MOCK

cat > "$TEST_DIR/bin/pg_isready" <<'MOCK'
#!/usr/bin/env bash
set -euo pipefail
TEST_DIR="${SS_MOCK_ROOT:?}"
printf 'pg_isready %s\n' "$*" >> "$TEST_DIR/ledger"
[ -f "$TEST_DIR/fail-db" ] && exit 1
exit 0
MOCK

cat > "$TEST_DIR/bin/pg_dump" <<'MOCK'
#!/usr/bin/env bash
set -euo pipefail
TEST_DIR="${SS_MOCK_ROOT:?}"
printf 'pg_dump %s\n' "$*" >> "$TEST_DIR/ledger"
if [ -n "${RESTIC_PASSWORD_FILE:-}" ]; then
  echo "RESTIC_PASSWORD_FILE leaked into pg_dump environment" >&2
  exit 3
fi
[ -f "$TEST_DIR/fail-dump" ] && exit 1
out=""
prev=""
for a in "$@"; do
  if [ "$prev" = "-f" ]; then out="$a"; fi
  prev="$a"
done
[ -n "$out" ] || exit 2
printf 'DUMP-FIXTURE\n' > "$out"
exit 0
MOCK

cat > "$TEST_DIR/bin/pg_restore" <<'MOCK'
#!/usr/bin/env bash
set -euo pipefail
TEST_DIR="${SS_MOCK_ROOT:?}"
printf 'pg_restore %s\n' "$*" >> "$TEST_DIR/ledger"
[ -f "$TEST_DIR/fail-restore-list" ] && exit 1
exit 0
MOCK

cat > "$TEST_DIR/bin/psql" <<'MOCK'
#!/usr/bin/env bash
set -euo pipefail
TEST_DIR="${SS_MOCK_ROOT:?}"
printf 'psql %s\n' "$*" >> "$TEST_DIR/ledger"
[ -f "$TEST_DIR/fail-psql" ] && exit 1
printf '1\n'
exit 0
MOCK

cat > "$TEST_DIR/bin/restic" <<'MOCK'
#!/usr/bin/env bash
set -euo pipefail
TEST_DIR="${SS_MOCK_ROOT:?}"
printf 'restic %s\n' "$*" >> "$TEST_DIR/ledger"
if [ "${RESTIC_PASSWORD_FILE:-}" != "$TEST_DIR/restic-password" ]; then
  echo "RESTIC_PASSWORD_FILE missing or wrong" >&2
  exit 3
fi
[ -f "$TEST_DIR/fail-restic" ] && exit 1
exit 0
MOCK

cat > "$TEST_DIR/bin/date" <<'MOCK'
#!/usr/bin/env bash
printf '20260717T000000Z\n'
MOCK

chmod 0755 "$TEST_DIR/bin/"*

# --- Env file with canaries (never allowed in outputs) ---
make_env_file() {
  cat > "$TEST_DIR/app.env" <<EOF
REGISTRY=ghcr.io/test
POSTGRES_USER=astro
POSTGRES_PASSWORD=$CANARY_PW
POSTGRES_DB=astro
DATABASE_URL=postgresql+asyncpg://astro:$CANARY_PW@solarsage-db:5432/astro
APP_DOMAIN=astro.example.com
TELEGRAM_BOT_TOKEN=$CANARY_TG
GRACE_USER_SALT=canary-salt-0123456789abcdef0123456789
CORS_ALLOWED_ORIGINS=https://astro.example.com
OPENROUTER_API_KEY=$CANARY_OR
RESTIC_REPOSITORY=canary-repo
OFFSITE_RESTIC_PASSWORD_FILE=$TEST_DIR/restic-password
EXPECTED_CALCULATION_VERSION=ss-calc-1.3.0
EPHEMERIS_EXPECTED_ARTIFACT_ID=se-test-artifact
EPHEMERIS_EXPECTED_MANIFEST_SHA256=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
EOF
  chmod 0640 "$TEST_DIR/app.env"
  printf 'canary-restic-password-content\n' > "$TEST_DIR/restic-password"
  chmod 0640 "$TEST_DIR/restic-password"
  : > "$TEST_DIR/env-file-ok"
}
export SS_MOCK_ROOT="$TEST_DIR"

reset_sandbox() {
  rm -f "$TEST_DIR/ledger" "$TEST_DIR/env-ledger" "$TEST_DIR/active-sha" \
        "$TEST_DIR/digest-map" "$TEST_DIR/containers" \
        "$TEST_DIR/fail-pull" "$TEST_DIR/fail-up" "$TEST_DIR/fail-up-for" \
        "$TEST_DIR/fail-db" "$TEST_DIR/fail-dump" "$TEST_DIR/fail-restore-list" \
        "$TEST_DIR/fail-restic" "$TEST_DIR/fail-health-all" "$TEST_DIR/fail-health-for" "$TEST_DIR/fail-smoke-for" \
        "$TEST_DIR/fail-label-for" "$TEST_DIR/fail-digest-for" "$TEST_DIR/fail-psql" \
        "$TEST_DIR/fail-migrate" "$TEST_DIR/fail-check-heads" "$TEST_DIR/fail-rm-rehearsal" \
        "$TEST_DIR/fail-inspect" "$TEST_DIR/fail-billing-rebill" "$TEST_DIR/api-stopped" \
        "$TEST_DIR/active-api-image" "$TEST_DIR/inspect-ledger"
  rm -rf "$TEST_DIR/state" "$TEST_DIR/backups"
  mkdir -p "$TEST_DIR/state" "$TEST_DIR/backups"
  : > "$TEST_DIR/ledger"
  : > "$TEST_DIR/env-ledger"
  : > "$TEST_DIR/digest-map"
  : > "$TEST_DIR/containers"
  printf '%s' "$SHA_A" > "$TEST_DIR/active-sha"
  : > "$TEST_DIR/maintenance.lock"
  make_env_file
}

run_orch() {
  # Direct exit-code capture; stdout/stderr stored for assertions.
  set +e
  SS_MOCK_ROOT="$TEST_DIR" \
  ORCH_APP_COMPOSE="$REPO_ROOT/infra/production/docker-compose.app.yml" \
  ORCH_ENV_FILE="$TEST_DIR/app.env" \
  ORCH_STATE_DIR="$TEST_DIR/state" \
  ORCH_BACKUP_DIR="$TEST_DIR/backups" \
  ORCH_LOCK_FILE="$TEST_DIR/maintenance.lock" \
  ORCH_ENV_OWNER="$CURRENT_USER" \
  ORCH_ENV_GROUP="$CURRENT_GROUP" \
  ORCH_DOCKER="$TEST_DIR/bin/docker" \
  ORCH_CURL="$TEST_DIR/bin/curl" \
  ORCH_PG_DUMP="$TEST_DIR/bin/pg_dump" \
  ORCH_PG_RESTORE="$TEST_DIR/bin/pg_restore" \
  ORCH_PG_ISREADY="$TEST_DIR/bin/pg_isready" \
  ORCH_PSQL="$TEST_DIR/bin/psql" \
  ORCH_RESTIC="$TEST_DIR/bin/restic" \
  ORCH_DATE="$TEST_DIR/bin/date" \
  bash "$ORCH" "$@" > "$TEST_DIR/out" 2> "$TEST_DIR/err"
  RC=$?
  set -e
}

expect_rc() {
  # $1 = expected rc, $2 = label
  if [ "$RC" -ne "$1" ]; then
    case_fail "$2: expected rc=$1 got rc=$RC out=[$(cat "$TEST_DIR/out")] err=[$(cat "$TEST_DIR/err")]"
    return 1
  fi
  return 0
}

assert_no_canary() {
  if grep -qE "CANARY_" "$TEST_DIR/out" "$TEST_DIR/err" "$TEST_DIR/ledger" 2>/dev/null; then
    case_fail "$1: secret canary leaked into output or ledger"
    return 1
  fi
  return 0
}

assert_out_has() {
  grep -qF -- "$1" "$TEST_DIR/out" && return 0
  case_fail "stdout missing [$1]; out=[$(cat "$TEST_DIR/out")]"
  return 1
}

assert_err_has() {
  grep -qF -- "$1" "$TEST_DIR/err" && return 0
  case_fail "stderr missing [$1]; err=[$(cat "$TEST_DIR/err")]"
  return 1
}

seed_digest_map_for() {
  # $1 = sha: seed digest-map entries for all three services.
  local svc
  for svc in api sidecar frontend; do
    printf '%s %s\n' "$(digest_for "$svc" "$1")" "$1" >> "$TEST_DIR/digest-map"
  done
}

write_record_fixture() {
  # $1 = active sha (may be empty), $2 = previous sha (may be empty).
  local active="$1" previous="$2"
  {
    printf 'active=%s\n' "$active"
    if [ -n "$active" ]; then
      printf 'active_api_image=%s\n' "$(digest_for api "$active")"
      printf 'active_sidecar_image=%s\n' "$(digest_for sidecar "$active")"
      printf 'active_frontend_image=%s\n' "$(digest_for frontend "$active")"
    else
      printf 'active_api_image=\nactive_sidecar_image=\nactive_frontend_image=\n'
    fi
    printf 'previous=%s\n' "$previous"
    if [ -n "$previous" ]; then
      printf 'previous_api_image=%s\n' "$(digest_for api "$previous")"
      printf 'previous_sidecar_image=%s\n' "$(digest_for sidecar "$previous")"
      printf 'previous_frontend_image=%s\n' "$(digest_for frontend "$previous")"
    else
      printf 'previous_api_image=\nprevious_sidecar_image=\nprevious_frontend_image=\n'
    fi
  } > "$TEST_DIR/state/release-record"
  chmod 0600 "$TEST_DIR/state/release-record"
  [ -z "$active" ] || seed_digest_map_for "$active"
  [ -z "$previous" ] || seed_digest_map_for "$previous"
}

write_migration_marker_fixture() {
  # $1 = sha, $2 = optional dump timestamp (default matches the mocked date).
  # Seeds a valid migration marker plus its backup dump pair in the sandbox.
  local sha="$1" ts="${2:-20260717T000000Z}"
  local base="db-$ts.dump" dump="$TEST_DIR/backups/db-$ts.dump"
  printf 'DUMP-FIXTURE\n' > "$dump"
  (cd "$TEST_DIR/backups" && sha256sum "$base" > "$base.sha256")
  chmod 0600 "$dump" "$dump.sha256"
  {
    printf 'target_sha=%s\n' "$sha"
    printf 'api_image=%s\n' "$(digest_for api "$sha")"
    printf 'backup_dump=%s\n' "$dump"
    printf 'verified_at=%s\n' "$ts"
    printf 'status=heads_applied\n'
  } > "$TEST_DIR/state/migration-record"
  chmod 0600 "$TEST_DIR/state/migration-record"
}

MANIFEST="$TEST_DIR/case_ids"
: > "$MANIFEST"
FAILURES="$TEST_DIR/failures"
: > "$FAILURES"
EXECUTED="$TEST_DIR/executed"
: > "$EXECUTED"
CASE_COUNT=0

try_case() {
  local label="$1"
  shift
  printf '%s\n' "$label" >> "$EXECUTED"
  if "$@"; then
    printf '%s\n' "$label" >> "$MANIFEST"
    CASE_COUNT=$((CASE_COUNT + 1))
  else
    printf '%s\n' "$label" >> "$FAILURES"
  fi
}

# END_BLOCK: HARNESS_SETUP

# START_BLOCK: CONTRACT_CASES

oc01() {
  reset_sandbox
  run_orch
  expect_rc 78 "OC01"
}
try_case "OC01 no arguments rejected" oc01

oc02() {
  reset_sandbox
  run_orch bogus-command
  expect_rc 78 "OC02"
}
try_case "OC02 unknown command rejected" oc02

oc03() {
  reset_sandbox
  run_orch deploy "$SHA_A"
  expect_rc 78 "OC03"
}
try_case "OC03 deploy without manual confirmation rejected" oc03

oc04() {
  reset_sandbox
  run_orch deploy "not-a-sha" --manual-confirm
  expect_rc 78 "OC04"
}
try_case "OC04 deploy malformed sha rejected" oc04

oc05() {
  reset_sandbox
  run_orch preflight "$SHA_A"
  local rc=0
  expect_rc 0 "OC05" || rc=1
  assert_out_has "Preflight OK for $SHA_A." || rc=1
  assert_no_canary "OC05" || rc=1
  return $rc
}
try_case "OC05 preflight success" oc05

oc06() {
  reset_sandbox
  chmod 0644 "$TEST_DIR/app.env"
  run_orch preflight "$SHA_A"
  expect_rc 78 "OC06"
}
try_case "OC06 preflight env file wrong mode rejected" oc06

oc07() {
  reset_sandbox
  sed -i '/^REGISTRY=/d' "$TEST_DIR/app.env"
  run_orch preflight "$SHA_A"
  expect_rc 78 "OC07"
}
try_case "OC07 preflight missing registry rejected" oc07

oc07b() {
  reset_sandbox
  chmod 0644 "$TEST_DIR/restic-password"
  run_orch preflight "$SHA_A"
  expect_rc 78 "OC07B"
}
try_case "OC07B preflight restic password file wrong mode rejected" oc07b

oc08() {
  reset_sandbox
  write_migration_marker_fixture "$SHA_B"
  run_orch deploy "$SHA_B" --manual-confirm
  local rc=0
  expect_rc 0 "OC08" || rc=1
  [ "$rc" -eq 0 ] || return 1
  assert_out_has "Deploy of $SHA_B completed successfully." || rc=1
  # Exact order: backup pair -> restic -> pull x3 -> inspect label x3 -> inspect digest x3 -> up.
  grep -qF "pg_dump " "$TEST_DIR/ledger" || { case_fail "OC08 pre-deploy backup missing"; rc=1; }
  grep -qF "pg_restore --list " "$TEST_DIR/ledger" || { case_fail "OC08 backup verification missing"; rc=1; }
  grep -qF "restic backup " "$TEST_DIR/ledger" || { case_fail "OC08 restic missing"; rc=1; }
  [ "$(grep -c '^pull ghcr.io/test/solarsage-' "$TEST_DIR/ledger")" -eq 3 ] || { case_fail "OC08 expected 3 tag pulls"; rc=1; }
  [ "$(grep -c 'Config.Labels' "$TEST_DIR/ledger")" -eq 3 ] || { case_fail "OC08 expected 3 label inspects"; rc=1; }
  [ "$(grep -c 'RepoDigests' "$TEST_DIR/ledger")" -eq 3 ] || { case_fail "OC08 expected 3 digest inspects"; rc=1; }
  local d_line p_line u_line
  d_line=$(grep -nx "pg_dump .*" "$TEST_DIR/ledger" | head -1 | cut -d: -f1)
  p_line=$(grep -nx "pull ghcr.io/test/solarsage-api:$SHA_B" "$TEST_DIR/ledger" | head -1 | cut -d: -f1)
  u_line=$(grep -nx "compose --env-file * up -d --wait api sidecar frontend" "$TEST_DIR/ledger" | head -1 | cut -d: -f1 || echo "")
  [ -n "$d_line" ] && [ -n "$p_line" ] || { case_fail "OC08 backup/pull ledger lines missing"; rc=1; }
  [ "$d_line" -lt "$p_line" ] || { case_fail "OC08 backup did not precede pull"; rc=1; }
  grep -qF "up -d --wait api sidecar frontend" "$TEST_DIR/ledger" || { case_fail "OC08 up missing"; rc=1; }
  # Activation used resolved digest references.
  grep -qF "API_IMAGE=$(digest_for api "$SHA_B")" "$TEST_DIR/env-ledger" || { case_fail "OC08 api digest not activated"; rc=1; }
  grep -qF "SIDECAR_IMAGE=$(digest_for sidecar "$SHA_B")" "$TEST_DIR/env-ledger" || { case_fail "OC08 sidecar digest not activated"; rc=1; }
  grep -qF "FRONTEND_IMAGE=$(digest_for frontend "$SHA_B")" "$TEST_DIR/env-ledger" || { case_fail "OC08 frontend digest not activated"; rc=1; }
  # Record tuple.
  local expected_record
  expected_record="active=$SHA_B
active_api_image=$(digest_for api "$SHA_B")
active_sidecar_image=$(digest_for sidecar "$SHA_B")
active_frontend_image=$(digest_for frontend "$SHA_B")
previous=
previous_api_image=
previous_sidecar_image=
previous_frontend_image="
  [ "$(cat "$TEST_DIR/state/release-record")" = "$expected_record" ] || { case_fail "OC08 record mismatch: [$(cat "$TEST_DIR/state/release-record")]"; rc=1; }
  [ "$(stat -c '%a' "$TEST_DIR/state/release-record")" = "600" ] || { case_fail "OC08 record mode"; rc=1; }
  grep -qF "curl http://127.0.0.1:8000/api/health" "$TEST_DIR/ledger" || { case_fail "OC08 api health missing"; rc=1; }
  grep -qF "curl http://127.0.0.1:18091/v1/health" "$TEST_DIR/ledger" || { case_fail "OC08 sidecar health missing"; rc=1; }
  grep -qF "curl http://127.0.0.1:3002/api/release-health" "$TEST_DIR/ledger" || { case_fail "OC08 frontend health missing"; rc=1; }
  assert_no_canary "OC08" || rc=1
  return $rc
}
try_case "OC08 deploy success digest-pinned with exact order and record" oc08

oc09() {
  reset_sandbox
  write_record_fixture "$SHA_A" ""
  write_migration_marker_fixture "$SHA_B"
  cp "$TEST_DIR/state/release-record" "$TEST_DIR/record-before"
  printf '%s' "$SHA_B" > "$TEST_DIR/fail-health-for"
  run_orch deploy "$SHA_B" --manual-confirm
  local rc=0
  expect_rc 78 "OC09" || rc=1
  assert_err_has "rollback to previous active $SHA_A is proven" || rc=1
  cmp -s "$TEST_DIR/record-before" "$TEST_DIR/state/release-record" || { case_fail "OC09 record changed after proven recovery: [$(cat "$TEST_DIR/state/release-record")]"; rc=1; }
  [ "$(grep -c '^pull ' "$TEST_DIR/ledger")" -eq 3 ] || { case_fail "OC09 rollback must not re-pull old tags"; rc=1; }
  [ "$(grep -cF ' up -d --wait api sidecar frontend' "$TEST_DIR/ledger")" -eq 2 ] || { case_fail "OC09 expected 2 ups"; rc=1; }
  grep -qF "API_IMAGE=$(digest_for api "$SHA_A")" "$TEST_DIR/env-ledger" || { case_fail "OC09 rollback did not use recorded digest"; rc=1; }
  assert_no_canary "OC09" || rc=1
  return $rc
}
try_case "OC09 deploy health failure proves rollback with byte-identical record" oc09

oc10() {
  reset_sandbox
  write_record_fixture "$SHA_A" ""
  write_migration_marker_fixture "$SHA_B"
  cp "$TEST_DIR/state/release-record" "$TEST_DIR/record-before"
  : > "$TEST_DIR/fail-health-all"
  run_orch deploy "$SHA_B" --manual-confirm
  local rc=0
  expect_rc 78 "OC10" || rc=1
  assert_err_has "recovery_required" || rc=1
  cmp -s "$TEST_DIR/record-before" "$TEST_DIR/state/release-record" || { case_fail "OC10 record must stay unchanged"; rc=1; }
  return $rc
}
try_case "OC10 deploy failure with unproven rollback is recovery_required" oc10

oc11() {
  reset_sandbox
  write_record_fixture "$SHA_A" "$SHA_B"
  run_orch rollback "$SHA_B" --manual-confirm
  local rc=0
  expect_rc 0 "OC11" || rc=1
  [ "$rc" -eq 0 ] || return 1
  [ "$(grep -c '^pull ' "$TEST_DIR/ledger")" -eq 0 ] || { case_fail "OC11 rollback pulled a tag: [$(grep '^pull ' "$TEST_DIR/ledger")]"; rc=1; }
  grep -qF "API_IMAGE=$(digest_for api "$SHA_B")" "$TEST_DIR/env-ledger" || { case_fail "OC11 rollback did not use stored previous digest"; rc=1; }
  local expected_record
  expected_record="active=$SHA_B
active_api_image=$(digest_for api "$SHA_B")
active_sidecar_image=$(digest_for sidecar "$SHA_B")
active_frontend_image=$(digest_for frontend "$SHA_B")
previous=$SHA_A
previous_api_image=$(digest_for api "$SHA_A")
previous_sidecar_image=$(digest_for sidecar "$SHA_A")
previous_frontend_image=$(digest_for frontend "$SHA_A")"
  [ "$(cat "$TEST_DIR/state/release-record")" = "$expected_record" ] || { case_fail "OC11 record: [$(cat "$TEST_DIR/state/release-record")]"; rc=1; }
  run_orch rollback "$SHA_C" --manual-confirm
  expect_rc 78 "OC11-unrecorded" || rc=1
  return $rc
}
try_case "OC11 rollback uses stored digests without old-tag pull" oc11

oc12() {
  reset_sandbox
  write_record_fixture "$SHA_A" ""
  run_orch status
  local rc=0
  expect_rc 0 "OC12" || rc=1
  assert_out_has "recorded active:   $SHA_A" || rc=1
  if grep -qE " pull | up -d |pg_dump|restic backup" "$TEST_DIR/ledger"; then
    case_fail "OC12 status mutated state: [$(cat "$TEST_DIR/ledger")]"
    rc=1
  fi
  return $rc
}
try_case "OC12 status is read-only" oc12

oc13() {
  reset_sandbox
  run_orch backup --manual-confirm
  local rc=0
  expect_rc 0 "OC13" || rc=1
  [ "$rc" -eq 0 ] || return 1
  assert_out_has "Backup completed: db-20260717T000000Z.dump (+sha256, restic)." || rc=1
  [ -f "$TEST_DIR/backups/db-20260717T000000Z.dump" ] || { case_fail "OC13 dump missing"; rc=1; }
  [ -f "$TEST_DIR/backups/db-20260717T000000Z.dump.sha256" ] || { case_fail "OC13 checksum missing"; rc=1; }
  [ "$(stat -c '%a' "$TEST_DIR/backups/db-20260717T000000Z.dump")" = "600" ] || { case_fail "OC13 dump mode"; rc=1; }
  (cd "$TEST_DIR/backups" && sha256sum -c "db-20260717T000000Z.dump.sha256") >/dev/null || { case_fail "OC13 checksum invalid"; rc=1; }
  local d_line l_line s_line
  d_line=$(grep -nx "pg_dump .*" "$TEST_DIR/ledger" | head -1 | cut -d: -f1)
  l_line=$(grep -nx "pg_restore --list .*" "$TEST_DIR/ledger" | head -1 | cut -d: -f1)
  s_line=$(grep -nx "restic backup .*" "$TEST_DIR/ledger" | head -1 | cut -d: -f1)
  [ "$d_line" -lt "$l_line" ] && [ "$l_line" -lt "$s_line" ] || { case_fail "OC13 backup order wrong: $d_line $l_line $s_line"; rc=1; }
  assert_no_canary "OC13" || rc=1
  return $rc
}
try_case "OC13 backup ordering pair checksum restic password file" oc13

oc13b() {
  reset_sandbox
  : > "$TEST_DIR/fail-restic"
  run_orch backup --manual-confirm
  local rc=0
  expect_rc 78 "OC13B" || rc=1
  assert_err_has "local dump and checksum are preserved" || rc=1
  [ -f "$TEST_DIR/backups/db-20260717T000000Z.dump" ] || { case_fail "OC13B dump not preserved"; rc=1; }
  [ -f "$TEST_DIR/backups/db-20260717T000000Z.dump.sha256" ] || { case_fail "OC13B checksum not preserved"; rc=1; }
  return $rc
}
try_case "OC13B restic failure preserves local dump pair" oc13b

oc14() {
  reset_sandbox
  run_orch restore "$TEST_DIR/backups/db-20260717T000000Z.dump" --manual-confirm
  expect_rc 78 "OC14-missing-dump"
}
try_case "OC14 restore missing dump rejected" oc14

oc15() {
  reset_sandbox
  printf 'solarsage-restore-rehearsal\n' > "$TEST_DIR/containers"
  printf 'DUMP-FIXTURE\n' > "$TEST_DIR/dump.dump"
  (cd "$TEST_DIR" && sha256sum "dump.dump" > "dump.dump.sha256")
  run_orch restore "$TEST_DIR/dump.dump" --manual-confirm
  local rc=0
  expect_rc 0 "OC15" || rc=1
  [ "$rc" -eq 0 ] || return 1
  assert_out_has "Restore rehearsal OK (isolated target only; production DB untouched)." || rc=1
  # Unique name created and cleaned; the pre-existing fixed-name container is untouched.
  if grep -qxF "rm -f solarsage-restore-rehearsal" "$TEST_DIR/ledger"; then
    case_fail "OC15 pre-existing fixed-name container was removed"
    rc=1
  fi
  grep -qE "^run -d --name solarsage-restore-rehearsal-[0-9]+ " "$TEST_DIR/ledger" || { case_fail "OC15 unique rehearsal container not created"; rc=1; }
  grep -qE "^rm -f solarsage-restore-rehearsal-[0-9]+$" "$TEST_DIR/ledger" || { case_fail "OC15 created container not cleaned"; rc=1; }
  grep -qxF "solarsage-restore-rehearsal" "$TEST_DIR/containers" || { case_fail "OC15 pre-existing container missing after rehearsal"; rc=1; }
  if grep -qE "pg_restore .*-p 5433" "$TEST_DIR/ledger"; then
    case_fail "OC15 production DB port was used by restore"
    rc=1
  fi
  printf 'corrupted\n' >> "$TEST_DIR/dump.dump"
  run_orch restore "$TEST_DIR/dump.dump" --manual-confirm
  expect_rc 78 "OC15-checksum" || rc=1
  return $rc
}
try_case "OC15 restore rehearsal unique container and collision safety" oc15

oc16() {
  local orch="$REPO_ROOT/scripts/deploy/prod-orchestrator.sh"
  local rc=0
  if grep -vE '^\s*#' "$orch" | grep -nE 'compose[[:space:]]+(build|down)|down[[:space:]]+-v|pnpm[[:space:]]|pip[[:space:]]+install'; then
    case_fail "OC16 forbidden construct in orchestrator source"
    rc=1
  fi
  if grep -vE '^\s*#' "$REPO_ROOT/infra/production/docker-compose.app.yml" | grep -nE ':latest("|\s|$)'; then
    case_fail "OC16 mutable latest tag in canonical compose"
    rc=1
  fi
  if grep -vE '^\s*#' "$REPO_ROOT/infra/production/docker-compose.app.yml" | grep -nE '^\s+-\s+"(0\.0\.0\.0|\[::\])'; then
    case_fail "OC16 non-loopback binding in canonical compose"
    rc=1
  fi
  return $rc
}
try_case "OC16 static no-build no-latest loopback constraints" oc16

oc17() {
  reset_sandbox
  run_orch preflight "$SHA_A"
  local rc1="$RC"
  run_orch preflight "$SHA_A"
  local rc2="$RC"
  [ "$rc1" -eq 0 ] && [ "$rc2" -eq 0 ] && return 0
  case_fail "OC17 non-deterministic exit codes: $rc1/$rc2"
  return 1
}
try_case "OC17 deterministic exit code on repeat" oc17

oc18() {
  reset_sandbox
  printf 'api' > "$TEST_DIR/fail-label-for"
  run_orch deploy "$SHA_B" --manual-confirm
  local rc=0
  expect_rc 78 "OC18" || rc=1
  assert_err_has "image label revision mismatch for api" || rc=1
  if grep -qF "up -d --wait" "$TEST_DIR/ledger"; then
    case_fail "OC18 activation happened despite label mismatch"
    rc=1
  fi
  [ ! -e "$TEST_DIR/state/release-record" ] || { case_fail "OC18 record must not be written"; rc=1; }
  return $rc
}
try_case "OC18 image label revision mismatch rejected before activation" oc18

oc19() {
  reset_sandbox
  printf 'sidecar' > "$TEST_DIR/fail-digest-for"
  run_orch deploy "$SHA_B" --manual-confirm
  local rc=0
  expect_rc 78 "OC19" || rc=1
  assert_err_has "malformed or missing RepoDigest for sidecar" || rc=1
  if grep -qF "up -d --wait" "$TEST_DIR/ledger"; then
    case_fail "OC19 activation happened despite malformed digest"
    rc=1
  fi
  return $rc
}
try_case "OC19 malformed RepoDigest rejected before activation" oc19

oc20() {
  reset_sandbox
  write_record_fixture "$SHA_A" ""
  write_migration_marker_fixture "$SHA_B"
  cp "$TEST_DIR/state/release-record" "$TEST_DIR/record-before"
  printf '%s' "$SHA_B" > "$TEST_DIR/fail-up-for"
  run_orch deploy "$SHA_B" --manual-confirm
  local rc=0
  expect_rc 78 "OC20" || rc=1
  assert_err_has "rollback to previous active $SHA_A is proven" || rc=1
  cmp -s "$TEST_DIR/record-before" "$TEST_DIR/state/release-record" || { case_fail "OC20 record changed after proven recovery"; rc=1; }
  [ "$(grep -cF ' up -d --wait api sidecar frontend' "$TEST_DIR/ledger")" -eq 2 ] || { case_fail "OC20 expected 2 ups (failed change plus one rollback)"; rc=1; }
  grep -qF "API_IMAGE=$(digest_for api "$SHA_A")" "$TEST_DIR/env-ledger" || { case_fail "OC20 rollback did not use recorded digest"; rc=1; }
  return $rc
}
try_case "OC20 up --wait nonzero followed by one proven rollback" oc20

oc21() {
  reset_sandbox
  write_record_fixture "$SHA_A" "$SHA_C"
  cp "$TEST_DIR/state/release-record" "$TEST_DIR/record-before"
  run_orch deploy "$SHA_A" --manual-confirm
  local rc=0
  expect_rc 0 "OC21" || rc=1
  assert_out_has "proven no-op" || rc=1
  cmp -s "$TEST_DIR/record-before" "$TEST_DIR/state/release-record" || { case_fail "OC21 same-SHA deploy changed the record"; rc=1; }
  if grep -qE "^pull | up -d " "$TEST_DIR/ledger"; then
    case_fail "OC21 same-SHA deploy mutated containers: [$(cat "$TEST_DIR/ledger")]"
    rc=1
  fi
  return $rc
}
try_case "OC21 same-SHA deploy is a proven no-op preserving history" oc21

oc22() {
  reset_sandbox
  run_orch deploy "$SHA_B" --manual-confirm &
  local bg_pid=$!
  # Hold the lock so the second mutating command must fail busy.
  exec 9<>"$TEST_DIR/maintenance.lock"
  flock -n 9 || { case_fail "OC22 harness cannot take lock"; return 1; }
  wait "$bg_pid" || true
  run_orch backup --manual-confirm
  local rc=0
  expect_rc 75 "OC22" || rc=1
  exec 9>&-
  return $rc
}
try_case "OC22 mutating command under held lock fails busy rc75" oc22

oc23() {
  reset_sandbox
  printf 'DUMP-FIXTURE\n' > "$TEST_DIR/dump.dump"
  (cd "$TEST_DIR" && sha256sum "dump.dump" > "dump.dump.sha256")
  : > "$TEST_DIR/fail-psql"
  run_orch restore "$TEST_DIR/dump.dump" --manual-confirm
  local rc=0
  expect_rc 78 "OC23" || rc=1
  assert_err_has "rehearsal database creation failed" || rc=1
  # The aborted rehearsal must not leak the created unique container.
  if grep -qE "^rm -f solarsage-restore-rehearsal-[0-9]+$" "$TEST_DIR/ledger"; then
    :
  else
    case_fail "OC23 aborted rehearsal did not clean the created container"
    rc=1
  fi
  if grep -qx "solarsage-restore-rehearsal-*" "$TEST_DIR/containers" 2>/dev/null; then
    case_fail "OC23 created container leaked after abort"
    rc=1
  fi
  return $rc
}
try_case "OC23 aborted rehearsal cleans only the created container" oc23

oc24() {
  reset_sandbox
  # Conflicting RELEASE_SHA inside the env file must fail closed, never substitute identity.
  printf 'RELEASE_SHA=%s\n' "$SHA_C" >> "$TEST_DIR/app.env"
  run_orch deploy "$SHA_B" --manual-confirm
  local rc=0
  expect_rc 78 "OC24-conflict" || rc=1
  assert_err_has "env file RELEASE_SHA conflicts with the requested target SHA" || rc=1
  if grep -qE "^pull | up -d " "$TEST_DIR/ledger"; then
    case_fail "OC24 activation happened despite RELEASE_SHA conflict"
    rc=1
  fi
  # A matching value is irrelevant: the requested identity is restored and used.
  reset_sandbox
  printf 'RELEASE_SHA=%s\n' "$SHA_B" >> "$TEST_DIR/app.env"
  write_migration_marker_fixture "$SHA_B"
  run_orch deploy "$SHA_B" --manual-confirm
  expect_rc 0 "OC24-match" || rc=1
  grep -qF "pull ghcr.io/test/solarsage-api:$SHA_B" "$TEST_DIR/ledger" || { case_fail "OC24 requested SHA was substituted by env"; rc=1; }
  return $rc
}
try_case "OC24 env RELEASE_SHA conflict fails closed; requested SHA restored" oc24

oc25() {
  # START_BLOCK: OC25_MIGRATE_PROVEN_MARKER
  reset_sandbox
  run_orch migrate "$SHA_B" --manual-confirm
  local rc=0
  expect_rc 0 "OC25" || rc=1
  [ "$rc" -eq 0 ] || return 1
  assert_out_has "Migration for $SHA_B completed successfully (heads applied and checked; marker recorded; no app activation, no release record change)." || rc=1
  # Exact order: backup pair -> restic -> pull x3 -> upgrade head -> check-heads.
  grep -qF "pg_dump " "$TEST_DIR/ledger" || { case_fail "OC25 pre-migration backup missing"; rc=1; }
  grep -qF "restic backup " "$TEST_DIR/ledger" || { case_fail "OC25 restic missing"; rc=1; }
  [ "$(grep -c '^pull ghcr.io/test/solarsage-' "$TEST_DIR/ledger")" -eq 3 ] || { case_fail "OC25 expected 3 tag pulls"; rc=1; }
  grep -qF -- "--profile migrate run --rm migrate" "$TEST_DIR/ledger" || { case_fail "OC25 migrate run missing"; rc=1; }
  grep -qF -- "--profile migrate run --rm migrate alembic current --check-heads" "$TEST_DIR/ledger" || { case_fail "OC25 head check run missing"; rc=1; }
  grep -qF "API_IMAGE=$(digest_for api "$SHA_B")" "$TEST_DIR/env-ledger" || { case_fail "OC25 migrate did not use pinned api digest"; rc=1; }
  local d_line u_line c_line
  d_line=$(grep -nx "pg_dump .*" "$TEST_DIR/ledger" | head -1 | cut -d: -f1)
  u_line=$(grep -nF -- "--profile migrate run --rm migrate" "$TEST_DIR/ledger" | grep -vF "check-heads" | head -1 | cut -d: -f1)
  c_line=$(grep -nF -- "migrate alembic current --check-heads" "$TEST_DIR/ledger" | head -1 | cut -d: -f1)
  [ -n "$d_line" ] && [ -n "$u_line" ] && [ -n "$c_line" ] || { case_fail "OC25 order lines missing"; rc=1; }
  { [ "$d_line" -lt "$u_line" ] && [ "$u_line" -lt "$c_line" ]; } || { case_fail "OC25 order wrong: backup=$d_line upgrade=$u_line check=$c_line"; rc=1; }
  # Atomic marker: exact contents and mode.
  local marker="$TEST_DIR/state/migration-record"
  [ -f "$marker" ] && [ ! -L "$marker" ] || { case_fail "OC25 marker missing"; rc=1; }
  local expected_marker
  expected_marker="target_sha=$SHA_B
api_image=$(digest_for api "$SHA_B")
backup_dump=$TEST_DIR/backups/db-20260717T000000Z.dump
verified_at=20260717T000000Z
status=heads_applied"
  [ "$(cat "$marker")" = "$expected_marker" ] || { case_fail "OC25 marker mismatch: [$(cat "$marker")]"; rc=1; }
  [ "$(stat -c '%a' "$marker")" = "600" ] || { case_fail "OC25 marker mode"; rc=1; }
  # Never activates app services, never writes the release record.
  if grep -qF "up -d --wait" "$TEST_DIR/ledger"; then
    case_fail "OC25 migration activated app services"
    rc=1
  fi
  [ ! -e "$TEST_DIR/state/release-record" ] || { case_fail "OC25 migration mutated the release record"; rc=1; }
  # Upgrade failure: no marker write; a pre-existing marker stays byte-identical.
  reset_sandbox
  write_migration_marker_fixture "$SHA_A"
  cp "$TEST_DIR/state/migration-record" "$TEST_DIR/marker-before"
  : > "$TEST_DIR/fail-migrate"
  run_orch migrate "$SHA_B" --manual-confirm
  expect_rc 78 "OC25-failure" || rc=1
  assert_err_has "migration run failed" || rc=1
  cmp -s "$TEST_DIR/marker-before" "$TEST_DIR/state/migration-record" || { case_fail "OC25-failure previous marker changed"; rc=1; }
  [ ! -e "$TEST_DIR/state/release-record" ] || { case_fail "OC25-failure record must not be written"; rc=1; }
  # Head-check failure: no marker write; previous marker stays byte-identical.
  reset_sandbox
  write_migration_marker_fixture "$SHA_A"
  cp "$TEST_DIR/state/migration-record" "$TEST_DIR/marker-before"
  : > "$TEST_DIR/fail-check-heads"
  run_orch migrate "$SHA_B" --manual-confirm
  expect_rc 78 "OC25-headcheck" || rc=1
  assert_err_has "migration head check failed" || rc=1
  cmp -s "$TEST_DIR/marker-before" "$TEST_DIR/state/migration-record" || { case_fail "OC25-headcheck previous marker changed"; rc=1; }
  # CLI gates.
  reset_sandbox
  run_orch migrate "not-a-sha" --manual-confirm
  expect_rc 78 "OC25-badsha" || rc=1
  run_orch migrate "$SHA_B"
  expect_rc 78 "OC25-noconfirm" || rc=1
  assert_no_canary "OC25" || rc=1
  return $rc
  # END_BLOCK: OC25_MIGRATE_PROVEN_MARKER
}
try_case "OC25 migrate proven heads check writes atomic marker without activation" oc25

oc26() {
  reset_sandbox
  printf 'DUMP-FIXTURE\n' > "$TEST_DIR/dump.dump"
  (cd "$TEST_DIR" && sha256sum "dump.dump" > "dump.dump.sha256")
  : > "$TEST_DIR/fail-rm-rehearsal"
  run_orch restore "$TEST_DIR/dump.dump" --manual-confirm
  local rc=0
  expect_rc 78 "OC26" || rc=1
  assert_err_has "rehearsal container cleanup failed" || rc=1
  # EXIT trap retries cleanup and emits one generic warning without secrets.
  assert_err_has "Warning: rehearsal cleanup failed" || rc=1
  assert_no_canary "OC26" || rc=1
  return $rc
}
try_case "OC26 restore cleanup failure is generic warning rc78" oc26

oc27() {
  # START_BLOCK: OC27_RELEASE_SHA_EXPORT_CONTRACT
  # Proves the canonical fix: RELEASE_SHA is EXPORTED at the invocation
  # boundary so docker compose interpolation (${RELEASE_SHA:?}) receives it.
  reset_sandbox
  local rc=0
  # Positive: preflight must pass; the mock config --quiet fails like real
  # compose when RELEASE_SHA is absent from the child environment.
  run_orch preflight "$SHA_B"
  expect_rc 0 "OC27 preflight" || rc=1
  [ "$rc" -eq 0 ] || return 1
  # Negative control: the identical compose config argv without RELEASE_SHA in
  # the environment must fail in the mock — the contract check is not vacuous.
  if SS_MOCK_ROOT="$TEST_DIR" "$TEST_DIR/bin/docker" compose --env-file "$TEST_DIR/app.env" -f "$REPO_ROOT/infra/production/docker-compose.app.yml" config --quiet >/dev/null 2>&1; then
    case_fail "OC27 negative control: config --quiet passed without RELEASE_SHA"
    rc=1
  fi
  # Activation path: deploy must hand RELEASE_SHA to the up call.
  reset_sandbox
  write_migration_marker_fixture "$SHA_B"
  run_orch deploy "$SHA_B" --manual-confirm
  expect_rc 0 "OC27 deploy" || rc=1
  [ "$rc" -eq 0 ] || return 1
  grep -qF "RELEASE_SHA=$SHA_B" "$TEST_DIR/env-ledger" || { case_fail "OC27 RELEASE_SHA not exported to compose up"; rc=1; }
  assert_no_canary "OC27" || rc=1
  return $rc
  # END_BLOCK: OC27_RELEASE_SHA_EXPORT_CONTRACT
}
try_case "OC27 RELEASE_SHA exported to compose config and activation" oc27

oc28() {
  # START_BLOCK: OC28_SMOKE_GATE
  # Smoke failure must behave exactly like a health failure: one rollback to
  # the recorded previous, record byte-identical, no release fixation.
  reset_sandbox
  write_record_fixture "$SHA_A" ""
  write_migration_marker_fixture "$SHA_B"
  cp "$TEST_DIR/state/release-record" "$TEST_DIR/record-before"
  printf '%s' "$SHA_B" > "$TEST_DIR/fail-smoke-for"
  run_orch deploy "$SHA_B" --manual-confirm
  local rc=0
  expect_rc 78 "OC28" || rc=1
  assert_err_has "rollback to previous active $SHA_A is proven" || rc=1
  cmp -s "$TEST_DIR/record-before" "$TEST_DIR/state/release-record" || { case_fail "OC28 record changed after smoke failure"; rc=1; }
  [ "$(grep -cF ' up -d --wait api sidecar frontend' "$TEST_DIR/ledger")" -eq 2 ] || { case_fail "OC28 expected 2 ups (activation + rollback)"; rc=1; }
  grep -qF "API_IMAGE=$(digest_for api "$SHA_A")" "$TEST_DIR/env-ledger" || { case_fail "OC28 rollback did not use recorded digest"; rc=1; }
  assert_no_canary "OC28" || rc=1
  return $rc
  # END_BLOCK: OC28_SMOKE_GATE
}
try_case "OC28 deploy smoke failure proves rollback with byte-identical record" oc28

oc29() {
  # START_BLOCK: OC29_MIGRATION_GATE
  # A new deploy target must fail closed before any activation when the
  # migration marker is missing, stale, symlinked, digest-mismatched or its
  # recorded backup pair is corrupted.
  local rc=0
  # Missing marker.
  reset_sandbox
  run_orch deploy "$SHA_B" --manual-confirm
  expect_rc 78 "OC29-missing" || rc=1
  assert_err_has "migration marker is missing" || rc=1
  if grep -qF "up -d --wait" "$TEST_DIR/ledger"; then
    case_fail "OC29-missing activated without a marker"
    rc=1
  fi
  [ ! -e "$TEST_DIR/state/release-record" ] || { case_fail "OC29-missing record written"; rc=1; }
  # Stale marker (recorded for a different target SHA).
  reset_sandbox
  write_migration_marker_fixture "$SHA_C"
  run_orch deploy "$SHA_B" --manual-confirm
  expect_rc 78 "OC29-stale" || rc=1
  assert_err_has "is stale" || rc=1
  if grep -qF "up -d --wait" "$TEST_DIR/ledger"; then
    case_fail "OC29-stale activated with a stale marker"
    rc=1
  fi
  # Symlink marker.
  reset_sandbox
  write_migration_marker_fixture "$SHA_B"
  rm -f "$TEST_DIR/state/migration-record"
  printf 'target_sha=%s\n' "$SHA_B" > "$TEST_DIR/state/migration-target"
  ln -s "$TEST_DIR/state/migration-target" "$TEST_DIR/state/migration-record"
  run_orch deploy "$SHA_B" --manual-confirm
  expect_rc 78 "OC29-symlink" || rc=1
  assert_err_has "migration marker is missing or not a regular file" || rc=1
  if grep -qF "up -d --wait" "$TEST_DIR/ledger"; then
    case_fail "OC29-symlink activated with a symlink marker"
    rc=1
  fi
  # Digest mismatch (marker api digest is not the resolved api digest).
  reset_sandbox
  write_migration_marker_fixture "$SHA_B"
  sed -i "s|^api_image=.*|api_image=$(digest_for api "$SHA_C")|" "$TEST_DIR/state/migration-record"
  run_orch deploy "$SHA_B" --manual-confirm
  expect_rc 78 "OC29-digest" || rc=1
  assert_err_has "api digest does not match" || rc=1
  if grep -qF "up -d --wait" "$TEST_DIR/ledger"; then
    case_fail "OC29-digest activated with a digest mismatch"
    rc=1
  fi
  # Corrupted recorded backup pair. The marker uses the SAME timestamp the
  # deploy's own pre-deploy backup will get: backup_now must pick the -1
  # suffix instead of overwriting, so the corrupted marker dump is never
  # "healed" by the new deploy backup.
  reset_sandbox
  write_migration_marker_fixture "$SHA_B"
  printf 'corrupted\n' >> "$TEST_DIR/backups/db-20260717T000000Z.dump"
  run_orch deploy "$SHA_B" --manual-confirm
  expect_rc 78 "OC29-checksum" || rc=1
  assert_err_has "checksum verification failed" || rc=1
  if grep -qF "up -d --wait" "$TEST_DIR/ledger"; then
    case_fail "OC29-checksum activated with a corrupted dump"
    rc=1
  fi
  [ -f "$TEST_DIR/backups/db-20260717T000000Z-1.dump" ] || { case_fail "OC29-checksum deploy backup did not use the -1 suffix"; rc=1; }
  # Same-second collision happy path: migrate records the base-name dump,
  # the deploy pre-deploy backup takes the deterministic -1 suffix, and the
  # recorded pre-migration pair stays byte-identical through a green deploy.
  reset_sandbox
  run_orch migrate "$SHA_B" --manual-confirm
  expect_rc 0 "OC29-collision-migrate" || rc=1
  [ "$rc" -eq 0 ] || return 1
  cp "$TEST_DIR/backups/db-20260717T000000Z.dump" "$TEST_DIR/dump-before"
  cp "$TEST_DIR/backups/db-20260717T000000Z.dump.sha256" "$TEST_DIR/dump-before.sha256"
  run_orch deploy "$SHA_B" --manual-confirm
  expect_rc 0 "OC29-collision-deploy" || rc=1
  [ -f "$TEST_DIR/backups/db-20260717T000000Z-1.dump" ] || { case_fail "OC29-collision deploy backup did not take the -1 suffix"; rc=1; }
  cmp -s "$TEST_DIR/dump-before" "$TEST_DIR/backups/db-20260717T000000Z.dump" || { case_fail "OC29-collision pre-migration dump was overwritten"; rc=1; }
  cmp -s "$TEST_DIR/dump-before.sha256" "$TEST_DIR/backups/db-20260717T000000Z.dump.sha256" || { case_fail "OC29-collision pre-migration checksum was overwritten"; rc=1; }
  grep -qxF "backup_dump=$TEST_DIR/backups/db-20260717T000000Z.dump" "$TEST_DIR/state/migration-record" || { case_fail "OC29-collision marker dump path changed"; rc=1; }
  assert_no_canary "OC29" || rc=1
  return $rc
  # END_BLOCK: OC29_MIGRATION_GATE
}
try_case "OC29 deploy requires valid migration marker before activation" oc29

oc30() {
  local rc=0
  reset_sandbox
  write_record_fixture "$SHA_A" ""
  write_migration_marker_fixture "$SHA_B"
  run_orch status
  expect_rc 0 "OC30" || rc=1
  assert_out_has "migration marker:" || rc=1
  assert_out_has "target=$SHA_B" || rc=1
  assert_out_has "verified_at=20260717T000000Z status=heads_applied" || rc=1
  if grep -qE " pull | up -d |pg_dump|restic backup" "$TEST_DIR/ledger"; then
    case_fail "OC30 status mutated state: [$(cat "$TEST_DIR/ledger")]"
    rc=1
  fi
  reset_sandbox
  run_orch status
  expect_rc 0 "OC30-none" || rc=1
  assert_out_has "migration marker:            none" || rc=1
  return $rc
}
try_case "OC30 status prints read-only migration marker evidence" oc30

oc31() {
  # START_BLOCK: OC31_BILLING_REBILL_CANONICAL
  local rc=0
  # Happy path: valid record + matching running container -> fixed job argv
  # with record-validated pinned digests. The record is never sourced.
  reset_sandbox
  write_record_fixture "$SHA_A" ""
  printf '%s\n' "$(digest_for api "$SHA_A")" > "$TEST_DIR/active-api-image"
  run_orch billing-rebill
  expect_rc 0 "OC31" || rc=1
  assert_out_has '"event":"billing.rebill_skipped"' || rc=1
  assert_out_has "rebill skipped: YOOKASSA_RECURRENT_ENABLED=false" || rc=1
  grep -qF -- "--profile billing-rebill run --rm --no-deps billing-rebill" "$TEST_DIR/ledger" || { case_fail "OC31 rebill run missing"; rc=1; }
  grep -qF "API_IMAGE=$(digest_for api "$SHA_A")" "$TEST_DIR/env-ledger" || { case_fail "OC31 rebill did not use the record api digest"; rc=1; }
  grep -qF "RELEASE_SHA=$SHA_A" "$TEST_DIR/env-ledger" || { case_fail "OC31 rebill did not use the record SHA"; rc=1; }
  grep -qF "solarsage-api" "$TEST_DIR/inspect-ledger" || { case_fail "OC31 container identity was not verified"; rc=1; }
  # No record at all: fail closed before any container/job interaction.
  reset_sandbox
  run_orch billing-rebill
  expect_rc 78 "OC31-norecord" || rc=1
  assert_err_has "no active release record" || rc=1
  if grep -qF "billing-rebill" "$TEST_DIR/ledger"; then
    case_fail "OC31 ran the job without a release record"
    rc=1
  fi
  # Tampered record with embedded shell: PARSED, never sourced — the payload
  # must not execute and the malformed field fails closed.
  reset_sandbox
  write_record_fixture "$SHA_A" ""
  printf '%s\n' "$(digest_for api "$SHA_A")" > "$TEST_DIR/active-api-image"
  sed -i "s|^active=.*|active=\$(touch $TEST_DIR/pwned)|" "$TEST_DIR/state/release-record"
  run_orch billing-rebill
  expect_rc 78 "OC31-tampered" || rc=1
  assert_err_has "record active SHA is malformed" || rc=1
  [ ! -e "$TEST_DIR/pwned" ] || { case_fail "OC31 record was sourced/evaluated — shell payload executed"; rc=1; }
  if grep -qF "billing-rebill" "$TEST_DIR/ledger"; then
    case_fail "OC31 ran the job with a tampered record"
    rc=1
  fi
  # Container missing: nothing to rebill against.
  reset_sandbox
  write_record_fixture "$SHA_A" ""
  : > "$TEST_DIR/fail-inspect"
  run_orch billing-rebill
  expect_rc 78 "OC31-nocontainer" || rc=1
  assert_err_has "api container solarsage-api not found" || rc=1
  # Container stopped.
  reset_sandbox
  write_record_fixture "$SHA_A" ""
  printf '%s\n' "$(digest_for api "$SHA_A")" > "$TEST_DIR/active-api-image"
  : > "$TEST_DIR/api-stopped"
  run_orch billing-rebill
  expect_rc 78 "OC31-stopped" || rc=1
  assert_err_has "is not running" || rc=1
  # Container image mismatch vs the active record: stale/mid-deploy state.
  reset_sandbox
  write_record_fixture "$SHA_A" ""
  printf '%s\n' "$(digest_for api "$SHA_B")" > "$TEST_DIR/active-api-image"
  run_orch billing-rebill
  expect_rc 78 "OC31-mismatch" || rc=1
  assert_err_has "does not match the active release record" || rc=1
  if grep -qF "billing-rebill" "$TEST_DIR/ledger"; then
    case_fail "OC31 ran the job against a mismatched container"
    rc=1
  fi
  # Image matches the record but the record SHA is a DIFFERENT valid SHA than
  # the live api reports: the health identity proof must stop the job.
  reset_sandbox
  write_record_fixture "$SHA_C" ""
  printf '%s\n' "$(digest_for api "$SHA_C")" > "$TEST_DIR/active-api-image"
  run_orch billing-rebill
  expect_rc 78 "OC31-shamismatch" || rc=1
  assert_err_has "api health release SHA does not match the active release record" || rc=1
  if grep -qF "billing-rebill" "$TEST_DIR/ledger"; then
    case_fail "OC31 ran the job despite the live SHA mismatch"
    rc=1
  fi
  # Job failure propagates non-zero.
  reset_sandbox
  write_record_fixture "$SHA_A" ""
  printf '%s\n' "$(digest_for api "$SHA_A")" > "$TEST_DIR/active-api-image"
  : > "$TEST_DIR/fail-billing-rebill"
  run_orch billing-rebill
  expect_rc 1 "OC31-jobfail" || rc=1
  # CLI gate: no extra arguments accepted.
  reset_sandbox
  run_orch billing-rebill extra
  expect_rc 78 "OC31-extra" || rc=1
  assert_no_canary "OC31" || rc=1
  return $rc
  # END_BLOCK: OC31_BILLING_REBILL_CANONICAL
}
try_case "OC31 billing-rebill canonical validating subcommand" oc31

# END_BLOCK: CONTRACT_CASES

EXPECTED_IDS="$TEST_DIR/expected_ids"
cat > "$EXPECTED_IDS" <<'EOF'
OC01 no arguments rejected
OC02 unknown command rejected
OC03 deploy without manual confirmation rejected
OC04 deploy malformed sha rejected
OC05 preflight success
OC06 preflight env file wrong mode rejected
OC07 preflight missing registry rejected
OC07B preflight restic password file wrong mode rejected
OC08 deploy success digest-pinned with exact order and record
OC09 deploy health failure proves rollback with byte-identical record
OC10 deploy failure with unproven rollback is recovery_required
OC11 rollback uses stored digests without old-tag pull
OC12 status is read-only
OC13 backup ordering pair checksum restic password file
OC13B restic failure preserves local dump pair
OC14 restore missing dump rejected
OC15 restore rehearsal unique container and collision safety
OC16 static no-build no-latest loopback constraints
OC17 deterministic exit code on repeat
OC18 image label revision mismatch rejected before activation
OC19 malformed RepoDigest rejected before activation
OC20 up --wait nonzero followed by one proven rollback
OC21 same-SHA deploy is a proven no-op preserving history
OC22 mutating command under held lock fails busy rc75
OC23 aborted rehearsal cleans only the created container
OC24 env RELEASE_SHA conflict fails closed; requested SHA restored
OC25 migrate proven heads check writes atomic marker without activation
OC26 restore cleanup failure is generic warning rc78
OC27 RELEASE_SHA exported to compose config and activation
OC28 deploy smoke failure proves rollback with byte-identical record
OC29 deploy requires valid migration marker before activation
OC30 status prints read-only migration marker evidence
OC31 billing-rebill canonical validating subcommand
EOF

LEDGER_OK=0
cmp -s "$EXPECTED_IDS" "$EXECUTED" && LEDGER_OK=1
if [ "$LEDGER_OK" -ne 1 ]; then
  echo "execution ledger mismatch, declared but not executed:" >&2
  { grep -vxF -f "$EXECUTED" "$EXPECTED_IDS" || true; } >&2
fi

if [ -s "$FAILURES" ]; then
  echo ""
  echo "Failed checks ($(wc -l < "$FAILURES" | tr -d ' ')):"
  cat "$FAILURES"
fi

if [ "$LEDGER_OK" -ne 1 ] || [ -s "$FAILURES" ]; then
  exit 1
fi

cmp -s "$EXPECTED_IDS" "$MANIFEST" || fail "pass manifest mismatch"

echo ""
echo "All $CASE_COUNT test-prod-orchestrator checks passed!"
exit 0
