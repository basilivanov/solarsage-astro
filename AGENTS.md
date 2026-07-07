# AGENTS.md — SolarSage Astro

## Канонические порты

| Порт | Сервис | Где запущен | Комментарий |
|------|--------|-------------|-------------|
| **5433** | PostgreSQL | `solarsage-db` (Docker) | База данных. .env: `DATABASE_URL` → `localhost:5433` |
| **8000** | API (FastAPI) | `solarsage-api.service` (systemd) | **Единственный API**. Nginx: `/api/` → 8000 |
| **3002** | Frontend (Next.js) | `solarsage-frontend.service` (systemd) | Production build. Nginx: `/` → 3002 |
| **80/443** | Nginx | `nginx.service` | Единая точка входа: `/api/*` → 8000, всё остальное → 3002 |

### Вспомогательные порты (не продакшен)

| Порт | Сервис | Комментарий |
|------|--------|-------------|
| **5434** | PostgreSQL (dev) | Дублирует 5433 для локальной разработки |
| **3000** | Frontend (dev) | `pnpm dev` вручную, только для локальной разработки |
| **55432** | Magia DB | Другой проект, НЕ наш |
| **55173-55181** | Magia (dev/prod) | Другой проект, НЕ наш |
| **18080** | Adminer | DB-менеджер, другой проект |
| **18091** | SolarSage sidecar | Расчётный движок (systemd, внутренний) |

### Docker

- `solarsage-db` — PostgreSQL 15 на портах 5433+5434, `POSTGRES_DB=astro`, user/password из `.env`
- Docker Compose (`docker-compose.yml`) — канонический файл, API=8000, SolarSage=8001, Frontend=3000
- Docker Compose (`docker-compose.prod.yml`) — неймспейснутый для запуска рядом с другими проектами

### Systemd

- `solarsage-sidecar.service` — SolarSage (pyswissePH), порт 18091, PYTHONPATH=/opt/solarsage-astro/apps/solarsage
- `solarsage-api.service` — FastAPI, порт 8000, EnvironmentFile=`/opt/solarsage-astro/.env`
- `solarsage-frontend.service` — Next.js production build, порт 3002
- `ductor-astro.service` — Telegram бот @vi_astro_bot

### НЕ ИСПОЛЬЗОВАТЬ

- ❌ **Ручной uvicorn** — `nohup uvicorn ... &` создаёт фантомный бэкенд без env-переменных
- ❌ **Порт 8001 как API** — это SolarSage sidecar, не API
- ❌ **USE_FIXTURES** — удалён, только реальный API через Telegram auth
- ❌ **Prefect** — удалён, контейнеры и systemd-юниты очищены

## Аутентификация

Единственный канонический путь: **Telegram WebApp → HMAC → `/api/auth/telegram`**.

- Dev-режим (`NODE_ENV=development`): `/api/auth/dev` для локальной разработки
- Production: только через Telegram HMAC-верификацию с реальным `TELEGRAM_BOT_TOKEN`

## UI Semantic/Test Contract

Фронтенд должен быть написан так, чтобы пользователь, accessibility tree и headless-тест видели один и тот же публичный UI-контракт. Тесты не должны зависеть от CSS-классов, React internals или случайного текста LLM.

### Обязательные правила для экранов и интерактивных блоков

- Каждый крупный экран имеет стабильный root selector: `data-testid="today-screen"`, `calendar-screen`, `profile-screen`, `readings-screen`, `horary-screen`, `natal-screen`.
- Крупные повторяемые блоки имеют стабильные `data-testid`: карточки, строки календаря, CTA, paywall, loading/error/empty states.
- Состояния, важные для UI и тестов, отражаются в DOM:
  - `data-state="loading|ready|empty|error|locked|disabled"`
  - `data-status="calm|tense|favorable|neutral"` или другой контрактный enum
  - `disabled`, `aria-disabled`, `aria-busy`, `aria-pressed`, `aria-expanded`, `aria-current`, `aria-selected`
- Icon-only buttons обязательно имеют `aria-label`.
- Табы и основная навигация используют `nav`, `aria-label`, `aria-current="page"` или `aria-selected`.
- Формы используют реальные `label`, `aria-invalid`, `aria-describedby`; placeholder не считается label.
- Loading state использует `role="status"` и/или `aria-busy`; error state использует `role="alert"`; modal/sheet использует `role="dialog"` и `aria-modal`.
- Для accordion/disclosure обязательно отражать состояние через `aria-expanded` и связанный `aria-controls`, если есть раскрываемая область.
- Динамические тексты от API/LLM не должны быть единственной опорой теста; рядом нужен стабильный structural selector или state attribute.
- `data-testid` — это публичный test contract. Не переименовывать без обновления e2e/unit тестов и миграционной причины.

### Тестовая стратегия для UI

- Mock/fixture e2e через Playwright `page.route('/api/**', ...)` допустим только как test-only слой. Он проверяет visual/structural contract фронта на стабильных payload'ах.
- Real e2e всегда идёт без route interception: Telegram HMAC → реальный API → реальные данные.
- Visual regression baseline использовать дозировано: ключевые экраны и состояния (`day`, `calendar`, `profile`, `readings`, `horary`, `natal`, `locked`, `empty`, `error`, `generating`). Динамические текстовые зоны маскировать или проверять структурно.
- Production runtime не должен импортировать `lib/mocks/*`, `lib/demo-data.ts` или demo/mock API. Моки живут в test harness, fixtures и старом visual reference, но не в product path.

Пример контракта:

```tsx
<section data-testid="today-summary" data-status={dayStatus}>
  <button
    type="button"
    aria-expanded={open}
    aria-controls="today-summary-details"
  >
    Подробнее
  </button>
</section>
```

Тест должен обращаться к публичному DOM-контракту:

```ts
await expect(page.getByTestId("today-summary")).toHaveAttribute("data-status", "calm")
await expect(page.getByRole("button", { name: "Подробнее" })).toHaveAttribute("aria-expanded", "false")
```

## GRACE Canon и структурные логи

Новые кодовые файлы и существенные изменения в существующих файлах должны сохранять GRACE-разметку: `AI_HEADER`, `START_MODULE_CONTRACT`, `START_MODULE_MAP`, а для нетривиальных публичных функций/классов — `START_FUNCTION_CONTRACT` и `START_BLOCK`. Старые файлы не переписывать ради формата отдельно от задачи.

### Шаблон файла

Использовать синтаксис комментариев языка файла (`#` для Python, `//` для TypeScript/TSX):

```ts
// ############################################################################
// AI_HEADER: MODULE_NAME — one-line description of what this module does
// ROLE: Detailed role. Who calls it, what it provides.
// ############################################################################

// START_MODULE_CONTRACT: M-MODULE-NAME
// purpose: What this module does. Who calls it, what it returns/provides.
// owns:
//   - path/to/file.ts
// inputs: List of inputs, parameters, or dependencies.
// outputs: What this module returns or provides.
// dependencies: Local modules, services, external APIs.
// side_effects: File writes, DB inserts, network calls, subprocess spawns.
// emitted_logs: Exact event names emitted by this module, or "none".
// invariants: Conditions this module must preserve.
// failure_policy: What errors are raised, returned, logged, or swallowed.
// END_MODULE_CONTRACT: M-MODULE-NAME

// START_MODULE_MAP: M-MODULE-NAME
// public_entrypoints:
//   - exportedFunction
//   - ClassName.methodName
// semantic_blocks:
//   - BLOCK_NAME: what this block owns
// owned_tests:
//   - __tests__/...
// END_MODULE_MAP: M-MODULE-NAME
```

Для функций:

```ts
// START_BLOCK: BLOCK_NAME
export async function runThing(input: string): Promise<Result> {
  // START_FUNCTION_CONTRACT: F-M-MODULE-NAME.runThing
  // purpose: What this function does.
  // inputs: input — description.
  // returns: Result — meaning.
  // side_effects: Network calls, DB writes, log events.
  // emitted_logs: ui.fetch_started, ui.fetch_succeeded, ui.fetch_failed.
  // error_behavior: Throws/returns on specific failures.
  // END_FUNCTION_CONTRACT: F-M-MODULE-NAME.runThing
}
// END_BLOCK: BLOCK_NAME
```

### Адаптация логов под этот репозиторий

Не импортировать `grace_control.core.structured_logger.GraceLogger`: такого runtime в SolarSage Astro нет. Использовать существующие механизмы:

- Frontend/browser: `logEvent`, `logStart`, `logSuccess`, `logFailure` из `lib/log/index.ts`. Для старого кода допустим существующий `logger.*`, но новые важные бизнес-события лучше писать через typed `logEvent`.
- Frontend server/RSC/route handlers: если файл уже использует GRACE stdout envelope, использовать `lib/grace/log.ts`; не смешивать два логгера в одном модуле без причины.
- Backend FastAPI: `log_event`, `bind_log_context`, `log_block` из `apps/api/app/core/logging.py`.
- Список допустимых событий берётся из `lib/log/events.gen.ts` и `apps/api/app/core/logging_events.py`. Новое событие сначала добавить в registry/contract, затем использовать в коде.
- В `emitted_logs` в contract указывать реальные event names (`ui.fetch_started`, `day.viewed`, `system.error`), а не произвольные фразы.
- Каждый структурный log должен иметь `slice`, `module`, `block`, `event`, `correlation_id`; frontend logger заполняет defaults, но для нового feature-кода передавать точные `slice/module/block` в `meta`.
- В логах запрещены raw Telegram initData, bot token, session cookies, email/phone и точные персональные данные без редакции. Использовать существующий redactor.
- Логгер не должен ломать пользовательский flow: ошибки логирования swallowing/handled, бизнес-ошибки логируются и возвращаются по контракту.

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
| Systemd unit'ы | `/etc/systemd/system/solarsage-*.service` |
| Production .env | `/opt/solarsage-astro/.env.production` |
| Backend env | `/opt/astro-project/.env` |
| Docker compose | `/opt/solarsage-astro/docker-compose.yml` |
| InitData генератор | `scripts/generate-telegram-test-initdata.py` |

## Известные баги / технический долг

| # | Баг | Где | Суть |
|---|-----|-----|------|
| 1 | `Transit_` / `Natal_` в UI | `today_service.py:209` — построение `TopFlag` | Имена сигналов приходят из нормализации с префиксом `Transit_Planet`. При построении `topFlags` используется сырое `signal.planet` без стриппинга. В результате в JSON-ответе: `"title": "Transit_Moon square Saturn"`. LLM-промпт просит не использовать Transit_, но сигналы попадают в UI независимо от LLM. **Fix:** стриппить префикс в `today_service.py` при построении `TopFlag`, либо в `NormalizationService` на этапе создания сигналов. |
| 2 | SolarSage не отдаёт `planet.house` | `normalization_service.py:60` — `_planets_in_houses()` | SolarSage возвращает `houses: [{number, cusp}]` отдельно от планет. `NormalizationService` вынужден вручную маппить `planet.longitude → house` через `_find_house()`. Это лишняя работа на стороне API. **Fix:** добавить в SolarSage выдачу `planet.house` сразу при расчёте транзитов и натала. |
