#!/bin/bash
# run-all-tests.sh — параллельный запуск всех тестов
# Vitest + Pytest + Playwright одновременно, результаты собираются в конце
set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m'

ROOT="$(cd "$(dirname "$0")" && pwd)"
RESULTS=/tmp/test-results-$$
mkdir -p "$RESULTS"

echo "=== Запуск всех тестов параллельно ==="
START=$(date +%s)

# 1. Vitest (unit) — уже параллельный внутри (threads)
cd "$ROOT" && npx vitest run --reporter=verbose > "$RESULTS/vitest.log" 2>&1 &
VITEST_PID=$!

# 2. Pytest (backend) — параллельный через xdist (-n auto)
cd "$ROOT/apps/api" && source .venv/bin/activate && python -m pytest tests/ -q -n auto > "$RESULTS/pytest.log" 2>&1 &
PYTEST_PID=$!

# 3. Playwright (E2E) — параллельный внутри (fullyParallel + workers)
cd "$ROOT" && E2E_BASE_URL=http://localhost:3002 npx playwright test --reporter=line > "$RESULTS/e2e.log" 2>&1 &
E2E_PID=$!

# Ждём всех
wait $VITEST_PID; VITEST_EXIT=$?
wait $PYTEST_PID; PYTEST_EXIT=$?
wait $E2E_PID; E2E_EXIT=$?

END=$(date +%s)
DURATION=$((END - START))

echo ""
echo "=== Результаты (${DURATION}s) ==="

for suite in vitest pytest e2e; do
    if [ "$suite" = "vitest" ]; then
        RESULT=$(grep -E "Test Files|Tests " "$RESULTS/vitest.log" | tail -2 | tr '\n' ' ')
        EXIT=$VITEST_EXIT
    elif [ "$suite" = "pytest" ]; then
        RESULT=$(tail -1 "$RESULTS/pytest.log")
        EXIT=$PYTEST_EXIT
    else
        RESULT=$(grep -E "passed|failed" "$RESULTS/e2e.log" | tail -1)
        EXIT=$E2E_EXIT
    fi

    if [ $EXIT -eq 0 ]; then
        echo -e "  ${GREEN}✓${NC} $suite: $RESULT"
    else
        echo -e "  ${RED}✗${NC} $suite: $RESULT"
    fi
done

echo ""
echo "Логи: $RESULTS/"
