---
name: sandbox-prototype
description: Прототипирование UI SolarSage через dev-only sandbox /sandbox (живые React-компоненты + JSON-фикстуры, без API/auth). Использовать для любых задач «покажи как будет выглядеть», вариантов дизайна на апрув владельцу, визуальных итераций до реализации.
---

# Sandbox-прототипирование

Канон: UI-прототип пишется СРАЗУ в боевых компонентах (Tailwind/шрифты/токены прода) и смотрится через песочницу. HTML-макеты и отдельные мок-приложения НЕ делать — они не переносятся 1:1 (решение владельца 2026-08-03, docs/work/2026-08-03_today-ux-round2/00_MASTER_TZ.md §63).

## Инфраструктура

- Маршруты: `app/sandbox/` — индекс `/sandbox`, экран дня `/sandbox/today?fixture=<name>`.
- Guard: `app/sandbox/layout.tsx` — `notFound()` вне `NODE_ENV=development` (в prod-сборке 404).
- Фикстуры: `__tests__/fixtures/today_convergence_v2/*.json` (полные wire-envelope'ы, переиспользуются тестами). Новое состояние = новый JSON туда же.
- Frame: `app/sandbox/today/sandbox-today-client.tsx` — phone-канва + `lg:` wide, TabBar, бейдж имени фикстуры.

## Цикл итерации

1. Поднять dev-сервер: `npx next dev --webpack -p 3000` — ТОЛЬКО `--webpack` (Turbopack падает на inferred root из-за вложенных lockfile'ов в /opt). Если :3000 уже занят работающим `next dev` — использовать его (fast refresh подхватит правки), не убивать чужой процесс.
2. **Всегда публиковать владельцу через CF quick tunnel** (см. ниже) — localhost-ссылки и скриншоты в чат не считаются сдачей прототипа. Скриншоты Playwright'ом — дополнительно, для фиксации состояния в репо/отчёте.
3. Правка компонента → fast refresh ~1 сек → владелец видит по тому же tunnel URL. Никаких build/restart/deploy.
4. По окончании — убить dev-сервер и туннель, если их поднимали мы (проверка `ss -tlnp | grep :3000`).

## Публикация владельцу: CF quick tunnel (обязательно)

Прототип считается показанным только когда владельцу дан живой tunnel URL. Порядок:

```bash
# dev-сервер уже слушает :3000 (п.1 цикла итерации)
nohup /tmp/cloudflared tunnel --url http://127.0.0.1:3000 --no-autoupdate > /tmp/sandbox-tunnel.log 2>&1 &
# URL: grep -oE "https://[a-z0-9-]+\.trycloudflare\.com" /tmp/sandbox-tunnel.log | head -1
```

- Бинарь: `/tmp/cloudflared` (linux-amd64 из официальных GitHub releases; если отсутствует — скачать заново тем же способом).
- **КРИТИЧНО: dev-сервер должен быть запущен с tunnel-хостом в allowed origins**, иначе Next 16 блокирует cross-origin HMR-websocket, страница через туннель рендерится, но гидратация дохнет и клики не работают. Запуск: `SANDBOX_ALLOWED_DEV_ORIGIN=<host>.trycloudflare.com npx next dev --webpack -p 3000` (host без схемы; переменную читает `next.config.mjs`). Порядок: сначала поднять туннель и узнать URL, потом перезапустить dev-сервер с этой переменной.
- Отдавать владельцу полный URL вида `<tunnel>/sandbox/today?fixture=<name>`.
- Quick tunnel временный: живёт, пока живы dev-сервер и процесс cloudflared. Перед тем как сообщить URL, проверить его `curl -s -o /dev/null -w "%{http_code}"` — должно быть 200 (не 502/503 прогрева) — **и обязательно прокликать интерактив Playwright'ом через tunnel URL** (клик по сигналу/тайлу открывает sheet), локальная проверка этого не покрывает.
- Общая политика безопасности артефактов — в AGENTS.md «Публикация отчётов и скриншотов»: только публично безопасный контент, никаких логов/данных пользователей.

## Правила

- Прототип = правки боевого компонента. Если состояние нужно «подсветить» (редкое/недостижимое живьём) — добавить/подправить JSON-фикстуру, не код под фикстуру.
- Sandbox-страницы не импортируют auth/API/`lib/mocks/*`; данные только из фикстур.
- DOM test contract (data-testid, data-state) не ломать и в прототипе.
- После апрува владельца: убрать ничего не нужно — код уже production; дальше стандартный накат (тесты, бейзлайны, деплой).

## Добавление нового экрана в песочницу

1. `app/sandbox/<screen>/page.tsx` — server component: безопасная загрузка фикстуры с диска (whitelist regex имени), picker при невалидном имени.
2. `app/sandbox/<screen>/sandbox-<screen>-client.tsx` — client frame с боевым компонентом.
3. Ссылка в индексе `app/sandbox/page.tsx`.
4. GRACE-разметка файлов обязательна (AI_HEADER/MODULE_CONTRACT/MODULE_MAP, owned_tests: none допустимо).

## Проверка

- `npx tsc --noEmit`, `python3 scripts/grace_front_lint.py`, `bash scripts/grace/check-markers.sh`.
- Ручная: `/sandbox` 200, страница фикстуры рендерит реальный экран (скриншот).
- В prod-сборке (`next build`) маршрут существует, но отдаёт 404 — это by design, не баг.
