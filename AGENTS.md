# AGENTS.md — SolarSage Astro

AGENTS.md вместе с документами `docs/agents/*` — operative canon репозитория;
`docs/GRACE_CANON.md` — policy baseline. При расхождении действует operative canon.
Этот файл держит критичные правила и ежедневные команды inline, а справочные
детали выносит в `docs/agents/` — у каждой ссылки указано, что там лежит.

## Канонические порты

| Порт | Сервис | Где запущен | Комментарий |
|------|--------|-------------|-------------|
| **5433** | PostgreSQL | `solarsage-db` (Docker) | База данных. .env: `DATABASE_URL` → `localhost:5433` |
| **8000** | API (FastAPI) | контейнер `solarsage-api` (Compose `solarsage-app`) | **Единственный API**. Nginx: `/api/` → 8000 |
| **3002** | Frontend (Next.js) | контейнер `solarsage-frontend` (Compose `solarsage-app`) | Production build. Nginx: `/` → 3002 |
| **80/443** | Nginx | `nginx.service` | Единая точка входа: `/api/*` → 8000, всё остальное → 3002 |

Канонический production path — минимальный Compose path: immutable per-SHA OCI images + `infra/production/docker-compose.app.yml` + orchestrator `/usr/local/libexec/solarsage/prod-orchestrator`.

### Вспомогательные порты (не продакшен)

| Порт | Сервис | Комментарий |
|------|--------|-------------|
| **5434** | PostgreSQL (dev) | Дублирует 5433 для локальной разработки |
| **3000** | Frontend (dev) | `pnpm dev` вручную, только для локальной разработки |
| **55432** | Magia DB | Другой проект, НЕ наш |
| **55173-55181** | Magia (dev/prod) | Другой проект, НЕ наш |
| **18080** | Adminer | DB-менеджер, другой проект |

### Production sidecar

| Порт | Сервис | Где запущен | Комментарий |
|------|--------|-------------|-------------|
| **18091** | SolarSage sidecar | контейнер `solarsage-sidecar` (Compose `solarsage-app`) | Расчётный движок, внутренний (API → sidecar по compose-сети) |
| **18095** | Bugsink | контейнер `solarsage-bugsink` (Compose `solarsage-bugsink`) | Error tracking UI, внутренний (`127.0.0.1:18095`, доступен по SSH-туннелю) |

Docker Compose проекты, systemd units (активные и parked) — см.
[`docs/agents/runtime-environments.md`](docs/agents/runtime-environments.md).

### НЕ ИСПОЛЬЗОВАТЬ

- ❌ **Ручной uvicorn** — `nohup uvicorn ... &` создаёт фантомный бэкенд без env-переменных
- ❌ **Порт 8001 как API** — это SolarSage sidecar, не API
- ❌ **USE_FIXTURES** — удалён, только реальный API через Telegram auth
- ❌ **Prefect** — удалён, контейнеры и systemd-юниты очищены

## Production host (astro.vasiliy-ivanov.ru)

Прод живёт на **отдельной машине** (`2.26.20.80`, xorek.cloud, EU; SSH
`root@2.26.20.80 -i ~/.ssh/solarsage_prod_server_ed25519`). Рантайм — Compose
`solarsage-app` (api/sidecar/frontend) + `solarsage-prod` (DB) + `solarsage-bugsink`.
Деплой — только через skill `prod-deploy`.

Полная топология (что где лежит, app.env ключи, backup/restic, egress и relay,
ProtectHome-caveat, список контейнеров и таймеров) —
[`docs/agents/runtime-environments.md`](docs/agents/runtime-environments.md).

## Dev host (dev.astro.vasiliy-ivanov.ru)

Дев — эта машина: рантайм **systemd units + локальный checkout** `/opt/solarsage-astro`
(не Compose). Таблица units, env-ключи convergence RC, legacy-флаги —
[`docs/agents/runtime-environments.md`](docs/agents/runtime-environments.md).

### Деплой на дев

```bash
cd /opt/solarsage-astro && git pull   # рабочее дерево = то, что крутится
NODE_ENV=production npm run build     # собирает в .next-prod (см. lib/env/next-dist-dir.mjs); build = `next build --webpack`, Turbopack падает на inferred root
systemctl restart solarsage-api solarsage-frontend solarsage-sidecar
```

Проверка: `curl https://dev.astro.vasiliy-ivanov.ru/api/health` — `git_sha` должен совпасть с HEAD.

⚠️ Не поднимать API/фронт вручную через `nohup uvicorn` / `nohup npm run start` на тех же портах: ручной процесс занимает порт, а systemd unit уходит в crash-loop (`activating (auto-restart)`). Если unit crash-loop'ится — сначала искать чужой процесс на порту (`ss -tlnp | grep :8000`).

Примечание: `next-env.d.ts` переписывается под последний использованный distDir (`.next` ↔ `.next-prod`) при каждой сборке — этот diff в коммиты не включать.

## Аутентификация

Единственный канонический путь: **Telegram WebApp → HMAC → `/api/auth/telegram`**.

- Dev-режим (`NODE_ENV=development`): `/api/auth/dev` для локальной разработки
- Production: только через Telegram HMAC-верификацию с реальным `TELEGRAM_BOT_TOKEN`

## UI Semantic/Test Contract

Фронтенд пишется так, чтобы пользователь, accessibility tree и headless-тест видели один публичный UI-контракт. Суть правил:

- Стабильные `data-testid` у экранов и крупных блоков; состояния отражаются в DOM
  (`data-state`, `data-screen-state`, `aria-*`); icon-only buttons имеют `aria-label`;
  loading — `role="status"`, error — `role="alert"`, modal — `role="dialog"` + `aria-modal`.
- Тесты опираются только на публичный DOM-контракт, не на CSS-классы/React internals/тексты LLM.
- `data-testid` — публичный контракт: не переименовывать без обновления тестов.
- Production runtime не импортирует `lib/mocks/*` и demo/mock API; mock e2e — только test-only слой.

Полные enums состояний (включая новый Today), правила для форм/табов/accordion,
тестовая стратегия и примеры кода —
[`docs/agents/ui-test-contract.md`](docs/agents/ui-test-contract.md).

## GRACE Canon и структурные логи

- Новые кодовые файлы и существенные изменения: `AI_HEADER`, `START_MODULE_CONTRACT`,
  `START_MODULE_MAP` (с обязательным `owned_tests`); для нетривиальных публичных
  функций/классов — `START_FUNCTION_CONTRACT` и `START_BLOCK`. Старые файлы ради
  формата не переписывать. Шаблоны — в [`docs/agents/grace-canon.md`](docs/agents/grace-canon.md).
- Логирование: frontend/browser — `logEvent`/`logStart`/`logSuccess`/`logFailure` из
  `lib/log/index.ts`; frontend server — `lib/grace/log.ts`; backend — `log_event` из
  `apps/api/app/core/logging.py`. Допустимые события — `lib/log/events.gen.ts` и
  `apps/api/app/core/logging_events.py`; новое событие сначала в registry. `grace_control` не существует — не импортировать.
- Навигация по коду — через GRACE-маркеры: модуль ищем по `rg "purpose:"` / имени
  `M-*`, читаем сначала CONTRACT/MAP, реализацию — по `START_BLOCK`, события — по
  точным именам из `emitted_logs`. Подробный workflow — там же, в grace-canon.md.

## Sandbox-прототипирование (канон)

Любой UI-прототип делается СРАЗУ в боевых React-компонентах и смотрится через dev-only песочницу — отдельные HTML-макеты и мок-приложения запрещены (перенос «1 в 1» достигается по построению). Полный workflow — скилл `sandbox-prototype`.

- Маршрут: `app/sandbox/` (`/sandbox` — индекс, `/sandbox/today?fixture=<name>` — экран дня). Guard `NODE_ENV=development`: в prod-сборке 404.
- Фикстуры: `__tests__/fixtures/today_convergence_v2/*.json` — те же, что в unit/e2e тестах; новые состояния = новый JSON туда же.
- Запуск: `npx next dev --webpack -p 3000` (ТОЛЬКО `--webpack`, Turbopack падает на inferred root). Порт 3000, вручную, по окончании процесс убить — не оставлять nohup-сирот.
- Итерация: правка компонента → fast refresh ~1 сек → скрин/CF-туннель владельцу на апрув.
- Sandbox-страницы не импортируют `lib/mocks/*`, auth и API; контент — только фикстуры.

## Тестирование

### Vitest (unit)
```bash
npx vitest run          # 29 тестов
```

### Pytest (backend)
```bash
cd apps/api && source .venv/bin/activate && python -m pytest tests/ -q
```

### Playwright (E2E)
```bash
E2E_BASE_URL=http://localhost:3000 npx playwright test
```
Использует реальный Telegram initData через `scripts/generate-telegram-test-initdata.py`.

### Генератор initData для тестов
```bash
python3 scripts/generate-telegram-test-initdata.py
```
Создаёт HMAC-подписанный initData с реальным bot token из `.env.production`.

## Расположение файлов

| Что | Где |
|-----|-----|
| Nginx конфиг | `/etc/nginx/sites-enabled/astro.conf` |
| Canonical env | `/etc/solarsage/app.env` (root:astro `0640`, operator-created) |
| Installed orchestrator | `/usr/local/libexec/solarsage/prod-orchestrator` |
| Installed app compose | `/etc/solarsage/compose/docker-compose.app.yml` |
| App compose (source) | `infra/production/docker-compose.app.yml` |
| DB compose (source) | `infra/production/docker-compose.yml` |
| InitData генератор | `scripts/generate-telegram-test-initdata.py` |
| Prod error loop (triage/fix runner) | `scripts/prod-errors/` (`.env` gitignored, см. `.env.example`) |

## Публикация отчётов и скриншотов (CF tunnel)

Артефакты владельцу (visual baselines, e2e-скриншоты, HTML-отчёты) выкладываем через
**Cloudflare quick tunnel** (static server на loopback + `cloudflared`), а не
скриншотами в чат. Только публично безопасный контент — никаких логов с user ids,
env, дампов. Пошаговые команды и активная витрина —
[`docs/agents/artifact-publishing.md`](docs/agents/artifact-publishing.md).

## Форматирование вывода в чат (OpenCode / TUI)

- ❌ **Запрещено использовать LaTeX/KaTeX синтаксис** в ответах (`$...$`, `$$...$$`, `\ge`, `\le`, `\rightarrow`, `\approx`, `\frac` и т.д.) — терминальный UI OpenCode не имеет KaTeX-рендера и отображает сырой сломанный текст.
- ✅ **Использовать чистый Unicode**:
  - Сравнения и стрелки: `≥`, `≤`, `→`, `←`, `↔`, `≈`, `≠`, `±`, `×`, `÷`, `·`
  - Степени и градусы: `°`, `′`, `″`, `²`, `³`, `½`, `¼`, `¾`
  - Астрологические символы: `☌`, `☍`, `△`, `□`, `⚹`, `⚼`, `⚺`, `☀️`, `🌙`, `♀`, `♂`, `♃`, `♄`, `♅`, `♆`, `♇`
  - Формулы писать простым текстовым видом: `P(X ≥ 9) = 13.3%`, `360° / 64 = 5°37′30″`.

## Известные баги / технический долг

Активен баг #2: SolarSage не отдаёт `planet.house` (маппинг на стороне API в
`normalization_service.py`). Полная таблица багов и закрытых фиксов —
[`docs/agents/known-issues.md`](docs/agents/known-issues.md).
