# Astro Mini App — монорепо

Telegram Mini App: персональный астрологический ассистент.
Главный экран — **Today** (`/day/:date`), главный endpoint — `GET /api/day/:date`.

> Полный продуктовый и архитектурный контекст — в [`docs/`](./docs/).
> Перед любыми изменениями читать: `docs/09_Project_transfer_context.md`,
> `docs/00_Обзор_продукта.md`, `docs/10_GRACE_Project_Agent_Guide.md`,
> и релевантный документ по зоне задачи.

---

## Структура репозитория

```text
astro/
├── apps/
│   ├── web/              # Next.js 16, Telegram Mini App UI (фронт v0)
│   ├── api/              # FastAPI backend (оркестратор: profile + access + cache + LLM)
│   └── solarsage/        # Sidecar для астрорасчётов (Swiss Ephemeris + REST)
├── packages/
│   └── contracts/        # Единые JSON-контракты + zod/pydantic схемы
│       ├── today.ts
│       ├── calendar.ts
│       ├── natal.ts
│       └── access.ts
├── infra/
│   ├── systemd/          # unit-файлы для api / solarsage / worker / web / backup
│   └── docker-compose.yml  # Postgres + Redis для локальной разработки
├── scripts/
│   ├── bootstrap-vds.sh  # первичная настройка VDS (пакеты, юзер, swap, ufw)
│   ├── deploy.sh         # `git pull && build && restart` на VDS
│   └── backup.sh         # дамп Postgres + Redis snapshot в /var/backups/astro
├── docs/                 # вся продуктовая и архитектурная документация
├── .env.example          # единый шаблон переменных окружения
├── Makefile              # short-cuts: make dev / make deploy / make migrate
└── README.md             # этот файл
```

Принцип: **один репозиторий = один деплой**. Любая часть (web, api,
solarsage) переносится на другой VDS просто `git clone` + копированием
`.env` + `make deploy`.

---

## Стек

- **Frontend** — Next.js 16 (App Router) + Tailwind + shadcn/ui, TMA SDK.
- **Backend** — Python 3.12, FastAPI, SQLAlchemy 2 + Alembic, Pydantic v2.
- **DB** — PostgreSQL 16, Redis 7.
- **Worker** — `arq` (Redis-based async queue) для фоновой генерации дня.
- **SolarSage** — отдельный Python REST-сервис со Swiss Ephemeris (sidecar
  на `127.0.0.1:18091`, наружу не торчит).
- **LLM** — через Vercel AI Gateway либо прямой провайдер (выбирается в `.env`).
- **Reverse proxy** — nginx на VDS (уже установлен и настроен админом сервера;
  репозиторий его не конфигурирует).
- **Process manager** — systemd (web, api, worker, solarsage).

---

## ТЗ на развёртывание с нуля (VDS, Ubuntu 22.04/24.04)

Полный пошаговый план — в [`docs/DEPLOY.md`](./docs/DEPLOY.md). Ниже —
короткий чек-лист.

### 0. Что нужно заранее
- VDS ≥ 2 vCPU / 4 GB RAM / 40 GB SSD, Ubuntu 22.04 LTS или 24.04 LTS.
- Домен, направленный A-записью на IP VDS (например `astro.example.com`).
- **nginx уже установлен и настроен** на VDS — этот репозиторий его не
  трогает. Проксирование `/` → `127.0.0.1:3000` и `/api/` → `127.0.0.1:8000`
  настраивает админ сервера (пример блока есть в `docs/DEPLOY.md`).
- Telegram Bot Token + настроенный Mini App в @BotFather.
- LLM API key (OpenAI / Anthropic / AI Gateway).
- (Опц.) GitHub-репозиторий с этим монорепо и deploy-key.

**Папка проекта на VDS: `/opt/solarsage-astro`** (владелец — пользователь `astro`).

### 1. Bootstrap VDS (3 минуты)
```bash
ssh root@VDS_IP
bash /tmp/bootstrap-vds.sh        # ставит python/node/postgres/redis, создаёт юзера astro и /opt/solarsage-astro
```
Скрипт **не трогает nginx** — раз он у тебя уже стоит и настроен. Делает:
создаёт пользователя `astro`, ставит swap 2G, пакеты (git, build-essential,
python3.12, nodejs 20, pnpm, postgresql-16, redis-server), включает ufw
(22/80/443), отключает root-login, создаёт `/opt/solarsage-astro`.

### 2. Клонирование и настройка
```bash
sudo -iu astro
git clone git@github.com:<you>/astro.git /opt/solarsage-astro
cd /opt/solarsage-astro
cp .env.example .env
$EDITOR .env       # заполнить все секреты (см. таблицу ниже)
```

### 3. База и миграции
```bash
make db-create     # создаёт роль + БД astro в Postgres
make migrate       # alembic upgrade head
```

### 4. SolarSage sidecar
```bash
cd /opt/solarsage-astro/apps/solarsage
make install
sudo cp /opt/solarsage-astro/infra/systemd/solarsage.service /etc/systemd/system/
sudo systemctl daemon-reload && sudo systemctl enable --now solarsage
```

### 5. Backend (FastAPI + worker)
```bash
cd /opt/solarsage-astro/apps/api
make install
sudo cp /opt/solarsage-astro/infra/systemd/astro-api.service    /etc/systemd/system/
sudo cp /opt/solarsage-astro/infra/systemd/astro-worker.service /etc/systemd/system/
sudo systemctl daemon-reload && sudo systemctl enable --now astro-api astro-worker
```

### 6. Frontend (Next.js)
```bash
cd /opt/solarsage-astro/apps/web
pnpm install && pnpm build
sudo cp /opt/solarsage-astro/infra/systemd/astro-web.service /etc/systemd/system/
sudo systemctl daemon-reload && sudo systemctl enable --now astro-web
```

### 7. Reverse proxy (nginx уже стоит на VDS)

Этот репозиторий **не управляет nginx**. Админ сервера сам добавляет
site-конфиг. Минимальный пример апстримов, к которым нужно проксировать:

- `/api/` → `http://127.0.0.1:8000` (FastAPI);
- `/`     → `http://127.0.0.1:3000` (Next.js, с поддержкой WebSocket-апгрейда).

См. `docs/DEPLOY.md` шаг 7 — там приведён готовый server-block, который
можно положить в `/etc/nginx/sites-available/astro` и сделать
`nginx -t && systemctl reload nginx`. SSL — через уже стоящий certbot
или собственный issuer.

### 8. Привязка к Telegram
В @BotFather → Bot Settings → Mini App → URL: `https://astro.example.com/`.
Webhook (если используется): `https://astro.example.com/api/telegram/webhook`.

### 9. Smoke-тест
```bash
curl https://astro.example.com/api/health      # → {"ok": true}
curl https://astro.example.com/api/day/2026-05-24 -H "X-Tg-Init-Data: <test>"
```
Открыть Mini App в Telegram → должен загрузиться Today screen.

### 10. Бэкапы
```bash
sudo cp /opt/solarsage-astro/infra/systemd/astro-backup.* /etc/systemd/system/
sudo systemctl enable --now astro-backup.timer   # ежедневно в 03:00 UTC
```

---

## Переменные окружения

Полный список — в `.env.example`. Минимум для запуска:

| Переменная | Описание |
|---|---|
| `DATABASE_URL` | `postgresql+asyncpg://astro:***@127.0.0.1:5432/astro` |
| `REDIS_URL` | `redis://127.0.0.1:6379/0` |
| `TELEGRAM_BOT_TOKEN` | токен бота, для валидации `initData` |
| `SOLARSAGE_BASE_URL` | `http://127.0.0.1:18091` |
| `SOLARSAGE_API_KEY` | shared-secret между api и sidecar |
| `LLM_PROVIDER` | `openai` / `anthropic` / `ai-gateway` |
| `LLM_API_KEY` | ключ выбранного провайдера |
| `LLM_MODEL` | например `openai/gpt-5-mini` |
| `NEXT_PUBLIC_API_BASE` | `https://astro.example.com/api` |
| `APP_ENV` | `dev` / `staging` / `production` |
| `APP_SECRET` | random 32 bytes, hex — для подписи сессий |

---

## Локальная разработка

```bash
make dev                # поднимает Postgres+Redis в docker-compose,
                        # api на :8000, web на :3000, solarsage на :18091
```

или по частям:

```bash
docker compose -f infra/docker-compose.yml up -d postgres redis
cd apps/solarsage && make run
cd apps/api       && make run
cd apps/web       && pnpm dev
```

---

## Принципы (не нарушать)

См. `docs/10_GRACE_Project_Agent_Guide.md`. Кратко:
- Today = экран выбранного дня, route `/day/:date`.
- Backend отдаёт стабильный `TodayPayload` (см. `packages/contracts/today.ts`),
  фронт не интерпретирует астрологию.
- LLM пишет только по curated `SemanticLayer`, не по raw SolarSage.
- Расчёты можно менять, контракты — нет (через `contract_version`).
- Versioning обязателен везде: `calculation_version`, `normalization_version`,
  `scoring_version`, `prompt_version`, `contract_version`.
