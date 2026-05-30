#!/usr/bin/env bash
# bootstrap.sh — one-shot local verification for the wave-1.1 / wave-1.1B repo.
#
# Назначение: после распаковки zip в корень проекта запустить ОДНУ команду,
# которая поднимает venv, ставит deps, прогоняет все 6 гейтов W-1.1 и
# drift-gate W-1.1B (Option B). Если скрипт завершается с exit 0 — всё
# зелёное, можно подписывать пакеты.
#
# Usage:
#   bash bootstrap.sh                 # full run
#   bash bootstrap.sh --skip-install  # reuse existing apps/api/.venv
#
# Side effects:
#   - создаёт apps/api/.venv (или переиспользует)
#   - создаёт apps/api/ci.db (sqlite) и удаляет в конце
#   - регенерирует packages/contracts/openapi.json и _generated.ts
#   - инициализирует .git если его нет (нужно для drift-gate)

set -euo pipefail

cd "$(dirname "$0")"
ROOT="$(pwd)"

SKIP_INSTALL=0
for arg in "$@"; do
  case "$arg" in
    --skip-install) SKIP_INSTALL=1 ;;
    *) echo "unknown arg: $arg" >&2; exit 2 ;;
  esac
done

step() { printf '\n=== %s ===\n' "$*"; }

# ---------------------------------------------------------------------------
# 0. Python venv + deps
# ---------------------------------------------------------------------------
if [[ "$SKIP_INSTALL" -eq 0 || ! -d apps/api/.venv ]]; then
  step "venv + pip install"
  python3 -m venv apps/api/.venv
  # shellcheck disable=SC1091
  source apps/api/.venv/bin/activate
  pip install -q --upgrade pip
  pip install -q -e "apps/api[dev]"
else
  # shellcheck disable=SC1091
  source apps/api/.venv/bin/activate
fi

# ---------------------------------------------------------------------------
# W-1.1 Verification (6 gates)
# ---------------------------------------------------------------------------
pushd apps/api >/dev/null

step "Gate 1: ruff"
ruff check .

step "Gate 2: mypy"
mypy app

step "Gate 3: alembic upgrade head"
rm -f ci.db
DATABASE_URL="sqlite+aiosqlite:///./ci.db" alembic upgrade head

step "Gate 4: uvicorn + GET /api/health"
uvicorn app.main:app --port 8766 >/tmp/uvicorn.log 2>&1 &
UVPID=$!
trap 'kill $UVPID 2>/dev/null || true' EXIT
sleep 2
BODY="$(curl -s localhost:8766/api/health)"
CODE="$(curl -s -o /dev/null -w '%{http_code}' localhost:8766/api/health)"
echo "body: $BODY"
echo "code: $CODE"
[[ "$CODE" == "200" ]] || { echo "health not 200"; exit 1; }
echo "$BODY" | grep -q '"status":"ok"' || { echo "bad shape"; exit 1; }
kill $UVPID 2>/dev/null || true
trap - EXIT

step "Gate 5: pytest"
pytest -q

step "Gate 6: drift cleanup grep"
if grep -rnE "from app\.api\.(day|calendar|profile|readings|auth)" app 2>/dev/null; then
  echo "forbidden router import found"; exit 1
fi
echo "drift cleanup ok"

rm -f ci.db
popd >/dev/null

# ---------------------------------------------------------------------------
# W-1.1B Verification (Option B drift gate)
# ---------------------------------------------------------------------------
step "contracts:generate (cold)"
bash scripts/contracts/generate.sh

if [[ ! -d .git ]]; then
  step "git init (drift gate needs git)"
  git init -q
  git -c user.email=ci@x -c user.name=ci add -A
  git -c user.email=ci@x -c user.name=ci commit -qm "bootstrap baseline"
fi

step "contracts:generate (warm) — must be idempotent"
bash scripts/contracts/generate.sh

step "drift gate: git diff --exit-code"
git diff --exit-code -- packages/contracts/openapi.json packages/contracts/_generated.ts
echo "OK: openapi.json + _generated.ts are byte-identical to committed version"

# ---------------------------------------------------------------------------
# W-2.0 Verification (frontend GRACE conformance, variant C: lint + bash gate)
# ---------------------------------------------------------------------------
step "Gate 7: pnpm install (frozen)"
if ! command -v pnpm >/dev/null 2>&1; then
  echo "pnpm not found — using npx pnpm"
  PNPM="npx -y pnpm@10.32.1"
else
  PNPM="pnpm"
fi
$PNPM install --prefer-frozen-lockfile --silent

step "Gate 8: eslint (grace plugin: contracts-only-import + no-redeclare-contract-types)"
$PNPM exec eslint .

step "Gate 9: GRACE marker gate"
bash scripts/grace/check-markers.sh

step "Gate 10: GRACE negative tests"
bash scripts/grace/check-negative.sh

step "Gate 11: vitest (grace tests)"
$PNPM exec vitest run

# ---------------------------------------------------------------------------
step "ALL GREEN"
echo "W-1.1:  ruff/mypy/alembic/health/pytest/drift — ok"
echo "W-1.1B: contracts:generate idempotent, drift gate clean"
echo "W-2.0:  eslint(grace) + marker gate + negative tests + vitest — ok"
