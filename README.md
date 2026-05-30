# Astro

Astro Mini App — backend (FastAPI) + frontend (Next.js) + внешний SolarSage сервис.

> **Status: Phase 1, pre-W-DEPLOY.** Проект пока **не разворачивается в прод**
> одной командой. Production-runbook будет переписан в волне `W-DEPLOY`
> (см. `grace/development-plan.xml` → `<future-waves>`). Текущий
> `docs/DEPLOY.md` помечен `stale (pre-W-1.0)` и руководством к деплою
> не является. Ниже — только **dev-loop**.

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

SolarSage запускается **отдельно** (внешний docker-сервис), мы только
ходим в него по `SOLARSAGE_BASE_URL` из `.env`.

---

## Структура

| Путь | Что |
|---|---|
| `app/`, `components/`, `package.json` | Next.js 16 App Router (frontend) |
| `apps/api/` | FastAPI + alembic (backend) |
| `apps/solarsage/` | вспомогательные `collect_*.py` скрипты (рантайм SolarSage — внешний) |
| `packages/contracts/` | сгенерированные OpenAPI + TS (drift-gated) |
| `grace/` | план развития, инварианты, маркеры волн |
| `infra/` | dev-only `docker-compose.yml` (postgres + redis) |
| `scripts/` | bootstrap-vds, db-create, контракт-генератор, grace-линтер |
| `docs/` | продуктовая история; `DEPLOY.md` — **stale** до `W-DEPLOY` |

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
- `make deploy` / `scripts/deploy.sh` — guarded, exit 1 (см. `W-DEPLOY`).
- `make logs` — нет systemd unit-файлов до `W-DEPLOY`.
- Полноценный SolarSage runtime — поднимается отдельно вне этого репо.

См. также `MANIFEST.md` — оперативное состояние волн.
