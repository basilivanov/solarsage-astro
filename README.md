# Astro

Astro Mini App — backend (FastAPI) + frontend (Next.js) + SolarSage sidecar (расчётный движок, контейнер в app stack).

> **Status: production path подготовлен.** Запуск — **только ручной**, через
> canonical Compose orchestrator: `docs/DEPLOYMENT.md` и
> `docs/PRODUCTION_RUNBOOK.md`. Исторический `docs/DEPLOY.md` заменён этими
> документами и сохранён как история. Ниже — **dev-loop**.

---

## Quickstart (dev)

Проверка гейтов (lint + types + миграции + контракты + тесты):

```bash
bash bootstrap.sh
```

Полный dev-loop с БД:

```bash
cp .env.example .env                       # один раз
docker compose -f infra/docker-compose.yml up -d   # postgres + redis
make -C apps/api install                   # venv + deps
make -C apps/api migrate                   # alembic upgrade head
make -C apps/api run                       # FastAPI :8000
pnpm install && pnpm dev                   # Next.js :3000
```

SolarSage sidecar — контейнер `solarsage-sidecar` в canonical app stack
(production). В dev-loop допустим и внешний sidecar (**dev-only**): просто
укажи `SOLARSAGE_BASE_URL` в `.env`.

---

## Структура

| Путь | Что |
|---|---|
| `app/`, `components/`, `package.json` | Next.js App Router (frontend) |
| `apps/api/` | FastAPI + alembic (backend) |
| `apps/solarsage/` | SolarSage sidecar runtime (расчётный движок; production — контейнер `solarsage-sidecar` в app stack) |
| `packages/contracts/` | сгенерированные OpenAPI + TS (drift-gated) |
| `grace/` | план развития, инварианты, маркеры волн (история) |
| `infra/` | `infra/docker-compose.yml` dev-only (postgres + redis); production — `infra/production/` |
| `scripts/` | `scripts/deploy/` (canonical production), `scripts/dev/` (dev helpers, напр. `db-create.sh`), контракт-генератор, grace-линтер |
| `docs/` | canonical docs: `DEPLOYMENT.md`, `PRODUCTION_RUNBOOK.md`; `DEPLOY.md` — история (replaced) |

---

## Testing

### Backend Tests
```bash
cd apps/api
pytest tests/ -v
```

### Frontend Unit Tests
```bash
npm run test        # watch mode
npm run test:run    # single run
```

### E2E Tests
```bash
npm run test:e2e       # headless
npm run test:e2e:ui    # interactive UI
```

### CI
All tests run automatically on push/PR via GitHub Actions (`.github/workflows/ci.yml`).

---

## Что точно не работает прямо сейчас
- `make deploy` / `make backup` / `make logs` / `make solarsage` — disabled, exit 1 (production идёт через canonical Compose orchestrator: app/sidecar/frontend контейнеры стека `solarsage-app`, см. `docs/DEPLOYMENT.md` и `docs/PRODUCTION_RUNBOOK.md`).

См. также `MANIFEST.md` — оперативное состояние волн.
