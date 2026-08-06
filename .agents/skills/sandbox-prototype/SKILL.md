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

1. Поднять dev-сервер: `npx next dev --webpack -p 3000` — ТОЛЬКО `--webpack` (Turbopack падает на inferred root из-за вложенных lockfile'ов в /opt).
2. Открыть `http://127.0.0.1:3000/sandbox/today?fixture=<name>` — или скриншот Playwright'ом, или CF quick tunnel для владельца (процедура туннеля — в AGENTS.md «Публикация отчётов и скриншотов»).
3. Правка компонента → fast refresh ~1 сек → следующий скрин. Никаких build/restart/deploy.
4. По окончании — убить dev-сервер (не оставлять nohup-сирот на :3000; проверка `ss -tlnp | grep :3000`).

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
