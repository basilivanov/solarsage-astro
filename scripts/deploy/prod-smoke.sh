#!/bin/bash
# ############################################################################
# AI_HEADER: PROD_SMOKE — post-deploy smoke gate for production
# ROLE: Standalone post-deploy E2E and infrastructure smoke testing script.
# DEPENDENCIES: bash (5.1+), curl, python3, docker (host-only)
# GRACE_ANCHORS: [SMOKE_CLI, SMOKE_CHECKS, SMOKE_REPORT]
# ############################################################################

# START_MODULE_CONTRACT: M-PROD-SMOKE
# purpose: Post-deploy smoke gate for production contour. Validates infra,
#   external endpoints, webhook fail-closed & end-to-end auth/profile flows.
# owns:
#   - scripts/deploy/prod-smoke.sh
# inputs:
#   - [--quick] : run infrastructure and external checks only
#   - [--expected-sha <sha>] : verify /api/health against specific git SHA
# outputs: exit 0 if all checks pass, non-zero (number of failed checks) otherwise
# dependencies:
#   - /etc/solarsage/app.env (host secrets)
#   - /var/lib/solarsage/orchestrator/release-record (release record)
#   - /opt/solarsage-astro/scripts/generate-telegram-test-initdata.py
# side_effects: creates temporary cookies in memory/tmp during test execution
# emitted_logs: none
# failure_policy: set -u; non-zero exit code if any check fails
# END_MODULE_CONTRACT: M-PROD-SMOKE

# START_MODULE_MAP: M-PROD-SMOKE
# public_entrypoints:
#   - main
# semantic_blocks:
#   - SMOKE_CLI: argument parsing & configuration
#   - SMOKE_CHECKS: individual check functions
#   - SMOKE_REPORT: summary reporting & exit handling
# END_MODULE_MAP: M-PROD-SMOKE

set -u

# Globals
QUICK_MODE=false
EXPECTED_SHA=""
FAILED_CHECKS=()
PASSED_COUNT=0
TOTAL_COUNT=0

# Configuration paths & defaults
ENV_FILE="/etc/solarsage/app.env"
RELEASE_RECORD="/var/lib/solarsage/orchestrator/release-record"
INITDATA_SCRIPT="/opt/solarsage-astro/scripts/generate-telegram-test-initdata.py"
PROD_DOMAIN="https://astro.vasiliy-ivanov.ru"
BACKUP_DIR="/var/backups/solarsage"

# Helper for reporting
pass_check() {
    local name="$1"
    PASSED_COUNT=$((PASSED_COUNT + 1))
    TOTAL_COUNT=$((TOTAL_COUNT + 1))
    echo "PASS ${name}"
}

fail_check() {
    local name="$1"
    local reason="$2"
    FAILED_CHECKS+=("${name}: ${reason}")
    TOTAL_COUNT=$((TOTAL_COUNT + 1))
    echo "FAIL ${name} — ${reason}"
}

skip_check() {
    local name="$1"
    local reason="$2"
    echo "SKIP ${name} (${reason})"
}

# START_BLOCK: SMOKE_CHECKS

check_containers() {
    local name="containers"
    if ! command -v docker &>/dev/null; then
        fail_check "$name" "docker command not found"
        return
    fi

    local ps_output
    ps_output=$(docker ps --format '{{.Names}} {{.Status}}' 2>/dev/null)
    if [ $? -ne 0 ]; then
        fail_check "$name" "cannot query docker ps (check permissions / root)"
        return
    fi

    local required_containers=("solarsage-api" "solarsage-sidecar" "solarsage-frontend" "solarsage-db")
    local missing=()
    local unhealthy=()

    for container in "${required_containers[@]}"; do
        local line
        line=$(echo "$ps_output" | grep -E "^${container}\b" || true)
        if [ -z "$line" ]; then
            missing+=("$container")
        elif [[ "$line" != *"healthy"* ]]; then
            unhealthy+=("$container")
        fi
    done

    if [ ${#missing[@]} -gt 0 ]; then
        fail_check "$name" "missing containers: ${missing[*]}"
    elif [ ${#unhealthy[@]} -gt 0 ]; then
        fail_check "$name" "not healthy: ${unhealthy[*]}"
    else
        pass_check "$name"
    fi
}

check_sidecar() {
    local name="sidecar"
    local res
    res=$(curl -sf --max-time 5 http://127.0.0.1:18091/v1/health 2>/dev/null || true)
    if [ -n "$res" ]; then
        pass_check "$name"
    else
        fail_check "$name" "HTTP query to http://127.0.0.1:18091/v1/health failed or returned empty"
    fi
}

check_egress_openrouter() {
    local name="egress-openrouter"
    local code
    code=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 https://openrouter.ai/api/v1/models 2>/dev/null || echo "000")
    if [ "$code" = "200" ] || [ "$code" = "401" ]; then
        pass_check "$name"
    else
        fail_check "$name" "HTTP status $code from https://openrouter.ai/api/v1/models"
    fi
}

check_egress_telegram() {
    local name="egress-telegram"
    local code
    code=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 https://api.telegram.org/ 2>/dev/null || echo "000")
    if [ "$code" = "200" ] || [ "$code" = "302" ]; then
        pass_check "$name"
    else
        fail_check "$name" "HTTP status $code from https://api.telegram.org/"
    fi
}

check_egress_yookassa() {
    local name="egress-yookassa"
    local code
    code=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 https://api.yookassa.ru/ 2>/dev/null || echo "000")
    if [ "$code" = "404" ] || [ "$code" = "401" ]; then
        pass_check "$name"
    else
        fail_check "$name" "HTTP status $code from https://api.yookassa.ru/"
    fi
}

check_backup_freshness() {
    local name="backup-freshness"
    if [ ! -d "$BACKUP_DIR" ]; then
        fail_check "$name" "directory $BACKUP_DIR does not exist"
        return
    fi

    local fresh_file
    fresh_file=$(find "$BACKUP_DIR" -maxdepth 1 -name 'db-*.dump' -mtime -2 2>/dev/null | head -n 1)
    if [ -n "$fresh_file" ]; then
        pass_check "$name"
    else
        fail_check "$name" "no db-*.dump file found in $BACKUP_DIR newer than 48 hours"
    fi
}

check_frontend() {
    local name="frontend"
    local code
    code=$(curl -sf -o /dev/null -w "%{http_code}" --max-time 10 "${PROD_DOMAIN}/" 2>/dev/null || echo "000")
    if [ "$code" = "200" ]; then
        pass_check "$name"
    else
        fail_check "$name" "HTTP status $code from ${PROD_DOMAIN}/"
    fi
}

check_api_health() {
    local name="api-health"
    local response
    response=$(curl -sf --max-time 10 "${PROD_DOMAIN}/api/health" 2>/dev/null || true)
    if [ -z "$response" ]; then
        fail_check "$name" "Failed to reach ${PROD_DOMAIN}/api/health"
        return
    fi

    local target_sha="$EXPECTED_SHA"
    if [ -z "$target_sha" ] && [ -f "$RELEASE_RECORD" ]; then
        target_sha=$(grep '^active=' "$RELEASE_RECORD" 2>/dev/null | cut -d= -f2 || true)
    fi

    local parse_res
    parse_res=$(python3 -c "
import sys, json
try:
    data = json.loads(sys.argv[1])
    status = data.get('status')
    sha = data.get('release_sha', '')
    expected = sys.argv[2]
    if status != 'ok':
        print(f'STATUS_NOT_OK:{status}')
    elif expected and sha != expected:
        print(f'SHA_MISMATCH:{sha}!= {expected}')
    else:
        print('OK')
except Exception as e:
    print(f'PARSING_ERROR:{e}')
" "$response" "$target_sha" 2>/dev/null)

    if [ "$parse_res" = "OK" ]; then
        pass_check "$name"
    else
        fail_check "$name" "$parse_res"
    fi
}

check_webhook_fail_closed() {
    local name="webhook-fail-closed"
    local code_no_secret
    code_no_secret=$(curl -s -o /dev/null -w "%{http_code}" -X POST "${PROD_DOMAIN}/api/telegram/webhook" \
        -H "Content-Type: application/json" \
        -d '{"update_id":1}' --max-time 10 2>/dev/null || echo "000")

    if [ "$code_no_secret" != "403" ]; then
        fail_check "$name" "expected HTTP 403 without secret header, got $code_no_secret"
        return
    fi

    if [ ! -f "$ENV_FILE" ]; then
        fail_check "$name" "cannot verify with valid secret: $ENV_FILE not found"
        return
    fi

    local secret
    secret=$(grep '^TELEGRAM_WEBHOOK_SECRET=' "$ENV_FILE" 2>/dev/null | cut -d= -f2- | tr -d '"' | tr -d "'" || true)
    if [ -z "$secret" ]; then
        fail_check "$name" "TELEGRAM_WEBHOOK_SECRET not found in $ENV_FILE"
        return
    fi

    local update_payload='{"update_id":900000001,"message":{"message_id":1,"from":{"id":1,"is_bot":false,"first_name":"Smoke"},"chat":{"id":1,"type":"private"},"date":1784900000,"text":"/start"}}'
    local valid_res
    valid_res=$(curl -s -X POST "${PROD_DOMAIN}/api/telegram/webhook" \
        -H "Content-Type: application/json" \
        -H "X-Telegram-Bot-Api-Secret-Token: ${secret}" \
        -d "$update_payload" --max-time 10 2>/dev/null || true)

    if [[ "$valid_res" == *"sendMessage"* ]]; then
        pass_check "$name"
    else
        fail_check "$name" "webhook with valid secret did not return sendMessage body"
    fi
}

check_auth_and_profile() {
    local name_auth="auth"
    local name_profile="profile"

    if [ "$QUICK_MODE" = true ]; then
        skip_check "$name_auth" "quick mode"
        skip_check "$name_profile" "quick mode"
        return
    fi

    if [ ! -f "$ENV_FILE" ]; then
        fail_check "$name_auth" "$ENV_FILE missing"
        fail_check "$name_profile" "dependency auth failed"
        return
    fi

    if [ ! -f "$INITDATA_SCRIPT" ]; then
        fail_check "$name_auth" "$INITDATA_SCRIPT missing"
        fail_check "$name_profile" "dependency auth failed"
        return
    fi

    local bot_token
    bot_token=$(grep '^TELEGRAM_BOT_TOKEN=' "$ENV_FILE" 2>/dev/null | cut -d= -f2- | tr -d '"' | tr -d "'" || true)
    if [ -z "$bot_token" ]; then
        fail_check "$name_auth" "TELEGRAM_BOT_TOKEN missing in $ENV_FILE"
        fail_check "$name_profile" "dependency auth failed"
        return
    fi

    local initdata
    initdata=$(TELEGRAM_BOT_TOKEN="$bot_token" python3 "$INITDATA_SCRIPT" 2>/dev/null | grep -E '^(query_id|user)=' | head -n 1 || true)

    if [ -z "$initdata" ]; then
        fail_check "$name_auth" "failed to generate initData"
        fail_check "$name_profile" "dependency auth failed"
        return
    fi

    local cookie_jar
    cookie_jar=$(mktemp)
    trap 'rm -f "$cookie_jar"' EXIT

    local json_payload
    json_payload=$(python3 -c "import json, sys; print(json.dumps({'initData': sys.argv[1]}))" "$initdata")

    local auth_response
    auth_response=$(curl -s -c "$cookie_jar" -X POST "${PROD_DOMAIN}/api/auth/telegram" \
        -H "Content-Type: application/json" \
        -d "$json_payload" --max-time 10 2>/dev/null || true)

    if [[ "$auth_response" == *"userId"* ]]; then
        pass_check "$name_auth"
    else
        fail_check "$name_auth" "POST /api/auth/telegram response missing userId"
        fail_check "$name_profile" "dependency auth failed"
        rm -f "$cookie_jar"
        return
    fi

    # Check profile endpoint using cookie
    local profile_response
    profile_response=$(curl -s -b "$cookie_jar" "${PROD_DOMAIN}/api/profile" --max-time 10 2>/dev/null || true)

    if [[ "$profile_response" == *"id"* ]] || [[ "$profile_response" == *"userId"* ]] || [[ "$profile_response" == *"tgUserId"* ]]; then
        pass_check "$name_profile"
    else
        fail_check "$name_profile" "GET /api/profile failed or unexpected response"
    fi

    rm -f "$cookie_jar"
}

# END_BLOCK: SMOKE_CHECKS

# START_BLOCK: SMOKE_CLI

parse_args() {
    while [ $# -gt 0 ]; do
        case "$1" in
            --quick)
                QUICK_MODE=true
                shift
                ;;
            --expected-sha)
                if [ -n "${2:-}" ]; then
                    EXPECTED_SHA="$2"
                    shift 2
                else
                    echo "Error: --expected-sha requires a non-empty argument" >&2
                    exit 1
                fi
                ;;
            -h|--help)
                echo "Usage: $0 [--quick] [--expected-sha <sha>]"
                exit 0
                ;;
            *)
                echo "Unknown option: $1" >&2
                exit 1
                ;;
        esac
    done
}

# END_BLOCK: SMOKE_CLI

# START_BLOCK: SMOKE_REPORT

main() {
    parse_args "$@"

    echo "=== Production Post-Deploy Smoke Gate ==="
    echo "Target domain: ${PROD_DOMAIN}"
    [ "$QUICK_MODE" = true ] && echo "Mode: Quick (infra + external only)"
    [ -n "$EXPECTED_SHA" ] && echo "Expected SHA: ${EXPECTED_SHA}"
    echo "----------------------------------------"

    # 1-6 Infra checks
    check_containers
    check_sidecar
    check_egress_openrouter
    check_egress_telegram
    check_egress_yookassa
    check_backup_freshness

    # 7-9 External checks
    check_frontend
    check_api_health
    check_webhook_fail_closed

    # 10-11 Auth & E2E checks
    check_auth_and_profile

    echo "----------------------------------------"
    local failed_count=${#FAILED_CHECKS[@]}
    if [ "$failed_count" -eq 0 ]; then
        echo "SUMMARY: PASS ${PASSED_COUNT}/${TOTAL_COUNT} checks succeeded."
        exit 0
    else
        echo "SUMMARY: FAIL (${failed_count} check(s) failed out of ${TOTAL_COUNT}):"
        for failure in "${FAILED_CHECKS[@]}"; do
            echo "  - ${failure}"
        done
        local exit_code=$failed_count
        if [ "$exit_code" -gt 99 ]; then
            exit_code=99
        fi
        exit "$exit_code"
    fi
}

main "$@"
# END_BLOCK: SMOKE_REPORT
