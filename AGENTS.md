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
