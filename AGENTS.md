# AGENTS.md — SolarSage Astro

## Канонические порты

| Порт | Сервис | Где запущен | Комментарий |
|------|--------|-------------|-------------|
| **8000** | API (FastAPI) | `solarsage-api.service` (systemd) | **Единственный API**. Nginx: `/api/` → 8000 |
| **8001** | API (чужая) | `astro-project-backend-1` (Docker) | `backend.app.main:app` — другой проект, НЕ наш |
| **3002** | Frontend (Next.js) | `solarsage-frontend.service` (systemd) | Production build. Nginx: `/` → 3002 |
| **3000** | Frontend (dev) | `pnpm dev` вручную | Только для локальной разработки |
| **80/443** | Nginx | `nginx.service` | Единая точка входа: `/api/*` → 8000, всё остальное → 3002 |
| **18091** | SolarSage sidecar | Docker, внутренний | Расчётный движок, только для API (не снаружи) |

### Docker Compose

- `docker-compose.yml` — **канонический** (API=8000, SolarSage=8001, Frontend=3000)
- `docker-compose.prod.yml` — **неймспейснутый** (API=8002, SolarSage=8003) для запуска рядом с другими проектами
- Если меняешь compose-файл — обнови nginx и next.config.mjs соответственно

### Systemd

- `solarsage-frontend.service` — Next.js production build, порт 3002
- `ductor-astro.service` — Telegram бот @vi_astro_bot
- `prefect-worker-solarsage-astro.service` — фоновая обработка (Prefect)

### НЕ ИСПОЛЬЗОВАТЬ

- ❌ **Ручной uvicorn** — `nohup uvicorn ... &` создаёт фантомный бэкенд без env-переменных
- ❌ **Порт 8001 как API** — это SolarSage sidecar, не API
- ❌ **USE_FIXTURES** — удалён, только реальный API через Telegram auth

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
