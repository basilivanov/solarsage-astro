#!/usr/bin/env bash

// ############################################################################
// AI_HEADER: MODULE_SCRIPTS_GUARDRAILS
// ROLE: Tooling script
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-GUARDRAILS-TOOLING
// ############################################################################

// START_MODULE_CONTRACT
// purpose: Tooling script — scripts/guardrails.sh
// owns:
//   - scripts/guardrails.sh
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

# ############################################################################
# Portable guardrails entrypoint.
#
# This script is the source-of-truth runner for local checks, Vercel build
# checks, Prefect/GRACE verifier runs, and any future CI provider. GitHub
# Actions workflows are intentionally not required while v0 sync rejects
# repositories that contain .github/workflows/*.
# ############################################################################
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
API_ROOT="$ROOT/apps/api"

section() {
  printf '\n=== %s ===\n' "$*"
}

die() {
  printf 'ERROR: %s\n' "$*" >&2
  exit 2
}

usage() {
  cat <<'EOF'
Usage:
  bash scripts/guardrails.sh <command>

Commands:
  fast       Run cheap mechanical checks only (frontend/backend GRACE lint).
  normal     Run frontend and backend checks suitable for normal acceptance.
  strict     Run full merge gate (full + backend-grace + logging guardrails).
  docs       Validate docs/ front-matter and docs/MANIFEST.md sync.
  secrets    Run a lightweight accidental-secret scan on tracked files.
  orchestrator
             Validate GRACE orchestrator adapter, profiles, roles, schema.
  contracts  Regenerate OpenAPI/TS contracts and fail on drift.
  backend    Run GRACE lint, ruff, mypy, alembic round-trip, pytest.
  backend-grace
             Run strict backend GRACE marker lint for canon-sync waves.
  frontend   Run eslint, TypeScript check, GRACE marker gate, negative tests.
  domain     Run domain-specific quality checks (horary quality).
  vercel     Run the checks suitable for Vercel build: docs + secrets + frontend.
  full       Run docs + secrets + orchestrator + contracts + backend + frontend + domain + prod.

Dependency setup:
  pnpm install
  cd apps/api && make install
EOF
}

require_cmd() {
  local command_name="$1"
  local install_hint="$2"
  if ! command -v "$command_name" >/dev/null 2>&1; then
    die "$command_name is not available. $install_hint"
  fi
}

run_pnpm() {
  if command -v pnpm >/dev/null 2>&1; then
    pnpm "$@"
    return 0
  fi

  if command -v corepack >/dev/null 2>&1; then
    corepack pnpm "$@"
    return 0
  fi

  die "pnpm is not available. Install pnpm or enable corepack."
}

api_python() {
  if [[ -x "$API_ROOT/.venv/bin/python" ]]; then
    printf '%s\n' "$API_ROOT/.venv/bin/python"
    return 0
  fi

  if python3 - <<'PY' >/dev/null 2>&1
import fastapi
import pytest
import sqlalchemy
import alembic
PY
  then
    printf '%s\n' "python3"
    return 0
  fi

  die "API dependencies are missing. Run: cd apps/api && make install"
}

api_bin_path() {
  if [[ -d "$API_ROOT/.venv/bin" ]]; then
    printf '%s:%s\n' "$API_ROOT/.venv/bin" "$PATH"
  else
    printf '%s\n' "$PATH"
  fi
}

run_docs() {
  section "docs: front-matter"
  python3 "$ROOT/scripts/check_frontmatter.py"

  section "docs: manifest"
  python3 "$ROOT/scripts/check_docs_manifest.py"
}

run_secrets() {
  section "security: accidental secret scan"

  if ! git -C "$ROOT" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    echo "git repository not found; skipping tracked-file secret scan"
    return 0
  fi

  local secret_output
  secret_output="$(
    git -C "$ROOT" grep -n -I -E \
      '(sk-[A-Za-z0-9_-]{20,}|gh[pousr]_[A-Za-z0-9_]{20,}|AKIA[0-9A-Z]{16})' \
      -- . \
      ':(exclude)pnpm-lock.yaml' \
      ':(exclude)package-lock.json' \
      ':(exclude)*.example' \
      ':(exclude)docs/**' \
      ':(exclude)grace/**' \
      2>/dev/null || true
  )"

  local env_output
  env_output="$(
    git -C "$ROOT" grep -n -I -E \
      '(OPENAI_API_KEY|ANTHROPIC_API_KEY|TELEGRAM_BOT_TOKEN|BOT_TOKEN|SECRET_KEY|DATABASE_URL|POSTGRES_PASSWORD|JWT_SECRET|SESSION_SECRET)=[^[:space:]#'\'\"']+' \
      -- . \
      ':(exclude)*.example' \
      ':(exclude)docs/**' \
      ':(exclude)grace/**' \
      2>/dev/null || true
  )"

  if [[ -n "$secret_output" || -n "$env_output" ]]; then
    echo "Potential secrets found in tracked files:"
    [[ -z "$secret_output" ]] || echo "$secret_output"
    [[ -z "$env_output" ]] || echo "$env_output"
    exit 1
  fi

  echo "secret scan: OK"
}

run_orchestrator() {
  section "orchestrator: validator self-tests"
  python3 -m unittest "$ROOT/scripts/test_orchestrator_contracts.py" -v

  section "orchestrator: project adapter"
  python3 "$ROOT/scripts/check_orchestrator_contracts.py"
}

run_contracts() {
  section "contracts: regenerate"
  bash "$ROOT/scripts/contracts/generate.sh"

  section "contracts: drift gate"
  git -C "$ROOT" diff --exit-code -- \
    packages/contracts/openapi.json \
    packages/contracts/_generated.ts
}

run_backend() {
  local python_bin
  python_bin="$(api_python)"

  section "backend: grace_lint self-tests"
  "$python_bin" -m unittest "$ROOT/scripts/test_grace_lint.py" -v

  section "backend: ruff"
  (
    cd "$API_ROOT"
    PATH="$(api_bin_path)" ruff check .
  )

  section "backend: mypy"
  (
    cd "$API_ROOT"
    PATH="$(api_bin_path)" mypy app
  )

  section "backend: alembic sqlite round-trip"
  local scratch_db
  scratch_db="$(mktemp "$API_ROOT/.guardrails.XXXXXX.db")"
  rm -f "$scratch_db"
  (
    cd "$API_ROOT"
    PATH="$(api_bin_path)" DATABASE_URL="sqlite+aiosqlite:///$scratch_db" alembic upgrade head
    PATH="$(api_bin_path)" DATABASE_URL="sqlite+aiosqlite:///$scratch_db" alembic downgrade base
    PATH="$(api_bin_path)" DATABASE_URL="sqlite+aiosqlite:///$scratch_db" alembic upgrade head
  )
  rm -f "$scratch_db"

  section "backend: pytest"
  (
    cd "$API_ROOT"
    PATH="$(api_bin_path)" pytest -q
  )
}

run_backend_grace() {
  local python_bin
  python_bin="$(api_python)"

  section "backend-grace: grace_lint self-tests"
  "$python_bin" -m unittest "$ROOT/scripts/test_grace_lint.py" -v

  section "backend-grace: app marker lint"
  "$python_bin" "$ROOT/scripts/grace_lint.py" "$API_ROOT/app"
}

run_frontend() {
  section "frontend: eslint"
  (
    cd "$ROOT"
    run_pnpm exec eslint .
  )

  section "frontend: typecheck"
  (
    cd "$ROOT"
    run_pnpm exec tsc --noEmit
  )

  section "frontend: GRACE marker gate"
  bash "$ROOT/scripts/grace/check-markers.sh"

  section "frontend: GRACE negative tests"
  bash "$ROOT/scripts/grace/check-negative.sh"
}

run_domain() {
  section "domain: check horary quality"
  bash "$ROOT/scripts/check_horary_quality.sh"
}

run_fast() {
  section "fast: cheap mechanical checks"
  python3 "$ROOT/scripts/test_grace_lint.py"
  python3 "$ROOT/scripts/test_grace_front_lint.py"
  python3 "$ROOT/scripts/grace_lint.py" "$API_ROOT/app"
  python3 "$ROOT/scripts/grace_front_lint.py"
}

run_normal() {
  run_frontend
  run_backend
}

run_prod_guard() {
  section "guardrails:prod"
  bash "$ROOT/scripts/check_prod_guard.sh"
}

run_vercel() {
  run_docs
  run_secrets
  run_frontend
  run_prod_guard
}

run_full() {
  run_docs
  run_secrets
  run_orchestrator
  run_contracts
  run_backend
  run_frontend
  run_domain
  run_prod_guard
}

run_logging_guardrails() {
  section "logging: structured logging guardrails"
  python3 "$ROOT/scripts/check_logging_guardrails.py"
}

run_strict() {
  run_full
  run_backend_grace
  run_logging_guardrails
}

if [[ $# -ne 1 ]]; then
  usage
  exit 2
fi

case "$1" in
  fast) run_fast ;;
  normal) run_normal ;;
  docs) run_docs ;;
  secrets) run_secrets ;;
  orchestrator) run_orchestrator ;;
  contracts) run_contracts ;;
  backend) run_backend ;;
  backend-grace) run_backend_grace ;;
  frontend) run_frontend ;;
  domain) run_domain ;;
  prod|guardrails:prod) run_prod_guard ;;
  vercel) run_vercel ;;
  full|all) run_full ;;
  strict) run_strict ;;
  -h|--help|help) usage ;;
  *) usage; exit 2 ;;
esac
