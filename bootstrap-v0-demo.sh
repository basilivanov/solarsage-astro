#!/bin/bash
# bootstrap-v0-demo.sh — запуск демо-режима для v0.app
# Использование:
#   1. Распакуй ZIP в папку
#   2. Запусти: ./bootstrap-v0-demo.sh
#   3. Открой http://localhost:3000/day/today

set -e
cd "$(dirname "$0")"

echo "==> Устанавливаю зависимости (pnpm install)..."
pnpm install --frozen-lockfile 2>/dev/null || pnpm install

echo "==> Включаю демо-режим..."
cat > .env.local << 'ENVEOF'
NEXT_PUBLIC_DEMO_MODE=true
NEXT_PUBLIC_API_URL=
ENVEOF

echo "==> Запускаю dev-сервер на порту 3000..."
echo ""
echo "  День:       http://localhost:3000/day/today"
echo "  Календарь:  http://localhost:3000/calendar"
echo "  Чат:        http://localhost:3000/chat"
echo "  Профиль:    http://localhost:3000/profile"
echo "  Натал:      http://localhost:3000/readings/natal"
echo ""
pnpm dev --port 3000
