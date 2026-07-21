#!/bin/bash
# run-all-tests.sh — быстрый локальный test loop (host: 4 CPU / 8 GiB)
#
# Режимы:
#   quick (default) — Vitest + backend pytest ПАРАЛЛЕЛЬНО, по TEST_WORKERS
#                     (default 2) workers каждый; без E2E.
#   full            — та же unit-фаза, затем Playwright E2E СТРОГО
#                     последовательно в 1 worker (real/release E2E никогда не
#                     параллелится с unit/backend: один backend/DB и shared
#                     state; release contract не меняется).
#
# Агрегация: оба процесса всегда дожидаемся (без set -e на wait), summary по
# каждому suite отдельно, non-zero exit при любом failure.
set -uo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m'

ROOT="$(cd "$(dirname "$0")" && pwd)"
MODE="${1:-quick}"
WORKERS="${TEST_WORKERS:-2}"

usage() {
    echo "Usage: $0 [quick|full]" >&2
    echo "       TEST_WORKERS=<positive int> (default 2) $0 [quick|full]" >&2
    exit 78
}

[ "$MODE" = "quick" ] || [ "$MODE" = "full" ] || usage
[[ "$WORKERS" =~ ^[0-9]+$ ]] && [ "$WORKERS" -ge 1 ] || usage

RESULTS=/tmp/test-results-$$
mkdir -p "$RESULTS"

VITEST_EXIT=0
PYTEST_EXIT=0
E2E_EXIT=0

echo "=== Unit-фаза: Vitest + pytest параллельно (workers=$WORKERS каждый) ==="
START=$(date +%s)

# Vitest и pytest идут одновременно; каждый ограничен своими workers.
cd "$ROOT" && npx vitest run --minWorkers=1 --maxWorkers="$WORKERS" > "$RESULTS/vitest.log" 2>&1 &
VITEST_PID=$!

cd "$ROOT" && "$ROOT/apps/api/.venv/bin/python" -m pytest apps/api/tests -q -n "$WORKERS" --dist=loadfile > "$RESULTS/pytest.log" 2>&1 &
PYTEST_PID=$!

# Дожидаемся ОБОИХ даже при падении одного (никакого set -e на wait).
wait "$VITEST_PID" || VITEST_EXIT=$?
wait "$PYTEST_PID" || PYTEST_EXIT=$?

UNIT_END=$(date +%s)

if [ "$MODE" = "full" ]; then
    echo ""
    echo "=== E2E-фаза: Playwright последовательно (workers=1) ==="
    # Только ПОСЛЕ unit-фазы: E2E ходит в тот же backend/DB и никогда не
    # параллелится с ней. 1 worker — честная serial нагрузка на 4 CPU host.
    cd "$ROOT" && E2E_BASE_URL=http://localhost:3002 npx playwright test --reporter=line --workers=1 > "$RESULTS/e2e.log" 2>&1 || E2E_EXIT=$?
fi

END=$(date +%s)
DURATION=$((END - START))
UNIT_DURATION=$((UNIT_END - START))

echo ""
echo "=== Результаты (unit ${UNIT_DURATION}s, всего ${DURATION}s) ==="

print_suite() {
    local name="$1" exit_code="$2" result="$3" log="$4"
    if [ "$exit_code" -eq 0 ]; then
        echo -e "  ${GREEN}✓${NC} $name: $result"
    else
        echo -e "  ${RED}✗${NC} $name: $result"
        echo "  --- tail $log ---"
        tail -n 30 "$log" | sed 's/^/  /'
        echo "  --- end tail ---"
    fi
}

print_suite vitest "$VITEST_EXIT" "$(grep -E "Test Files|Tests " "$RESULTS/vitest.log" | tail -2 | tr '\n' ' ')" "$RESULTS/vitest.log"
print_suite pytest "$PYTEST_EXIT" "$(tail -1 "$RESULTS/pytest.log")" "$RESULTS/pytest.log"
if [ "$MODE" = "full" ]; then
    print_suite e2e "$E2E_EXIT" "$(grep -E "passed|failed" "$RESULTS/e2e.log" | tail -1)" "$RESULTS/e2e.log"
fi

echo ""
echo "Логи: $RESULTS/"

if [ "$VITEST_EXIT" -ne 0 ] || [ "$PYTEST_EXIT" -ne 0 ] || [ "$E2E_EXIT" -ne 0 ]; then
    exit 1
fi
exit 0
