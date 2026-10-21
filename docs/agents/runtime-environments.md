# Runtime-окружения: production и dev хосты

> Часть operative canon репозитория (вместе с AGENTS.md и `docs/agents/*`).
> Извлечено из AGENTS.md 2026-10-22; AGENTS.md содержит резюме и ссылку на этот файл.
> Обращаться сюда за: топологией prod/dev хостов, расположением файлов на проде,
> systemd units и таймерами, env-ключами окружений, egress/relay-контекстом,
> Docker Compose проектами.

## Канонический production path

Канонический production path — минимальный Compose path: immutable per-SHA OCI images + `infra/production/docker-compose.app.yml` + единственный orchestrator `/usr/local/libexec/solarsage/prod-orchestrator` (исходник `scripts/deploy/prod-orchestrator.sh`). До one-time manual cutover старые app systemd units (`solarsage-api.service`, `solarsage-sidecar.service`, `solarsage-frontend.service`) могут ещё существовать на хосте; они disabled-by-name, их templates удалены из репозитория (181 cleanup).

## Docker

- `infra/production/docker-compose.app.yml` — **canonical production app stack** (api/sidecar/frontend, loopback-only, digest-pinned images; проект `solarsage-app`)
- `infra/production/docker-compose.yml` — **canonical production DB** (PostgreSQL 15, проект `solarsage-prod`, port 5433)
- Root `docker-compose.yml` / `docker-compose.prod.yml` — **dev/compatibility only** (не production source of truth)
- `solarsage-db` — PostgreSQL 15 контейнер DB-проекта на портах 5433+5434, `POSTGRES_DB=astro`, user/password из `.env`

## Systemd (общее)

- `solarsage-db.service` — PostgreSQL compose project (canonical DB, port 5433)
- `solarsage-backup.timer` / `solarsage-backup.service` — canonical daily backup через установленный orchestrator
- `ductor-astro.service` — Telegram бот @vi_astro_bot

App-сервисы (api/sidecar/frontend) работают в контейнерах Compose `solarsage-app`, а не как systemd units. Старые app units (`solarsage-api.service`, `solarsage-sidecar.service`, `solarsage-frontend.service`), `solarsage.service`, `solarsage-frontend-preview-3001.service` и `solarsage-backup-maintenance.*` — parked: host-prepare только disable-by-name (без `--now`, без stop), фактический stop — отдельная ручная one-time cutover команда владельца непосредственно перед первым Compose deploy.

## Production host (astro.vasiliy-ivanov.ru)

Прод живёт на **отдельной машине** (с 2026-07-23 — новый хост, миграция с RU-хостера):

```text
domain: astro.vasiliy-ivanov.ru
IPv4:   2.26.20.80 (xorek.cloud, EU — прямой egress к Telegram/OpenRouter/ЮKassa)
OS:     Ubuntu 22.04 LTS, hostname 1871962.xorek.cloud
SSH:    root@2.26.20.80 -i ~/.ssh/solarsage_prod_server_ed25519
Старый хост 157.22.192.242 — standby (app-контейнеры остановлены, БД запущена,
backup.timer выключен). Не удалять до явного решения владельца.
```

### Что где лежит на проде

| Что | Где |
|-----|-----|
| App env (секреты) | `/etc/solarsage/app.env` (root:astro 0640) |
| Installed app compose | `/etc/solarsage/compose/docker-compose.app.yml` |
| Repo checkout (infra) | `/opt/solarsage-astro` (нужен для `solarsage-db.service` и tmpfiles.d) |
| Orchestrator | `/usr/local/libexec/solarsage/prod-orchestrator` |
| Orchestrator state / release record | `/var/lib/solarsage/orchestrator/release-record` |
| Локальные DB-дампы | `/var/backups/solarsage` |
| Restic-репозиторий (временно на этой же машине) | `/srv/restic/solarsage` |
| Nginx vhost | `/etc/nginx/sites-enabled/astro.vasiliy-ivanov.ru.conf` |
| TLS cert | certbot, `/etc/letsencrypt/live/astro.vasiliy-ivanov.ru/` |
| Error tracking (Bugsink) | `infra/production/docker-compose.bugsink.yml`, `solarsage-bugsink.service` |
| Контейнеры | `solarsage-api`, `solarsage-sidecar`, `solarsage-frontend` (Compose `solarsage-app`), `solarsage-db` (Compose `solarsage-prod`), `solarsage-bugsink` (Compose `solarsage-bugsink`) |

Systemd на проде: активны `solarsage-db.service`, `solarsage-backup.timer`, `solarsage-day-pregen.timer` (+ `.service`, с 2026-08-09 — pregen завтрашнего дня в 04:07 MSK через `docker exec solarsage-api python -m app.jobs.day_pregen`; prod-вариант юнита — `infra/systemd/solarsage-day-pregen-prod.{service,timer}`, dev-вариант на venv — `solarsage-day-pregen.{service,timer}`), `solarsage-feedback-broadcast.timer`, `fail2ban`, UFW (22/80/443). Бэкап = orchestrator `backup`: локальный pg_dump в `/var/backups/solarsage` + restic в `sftp:restic-backup@2.26.20.80:/solarsage` — **это та же машина (backup-to-self, ВРЕМЕННО)**; при появлении отдельного offsite-хоста поменять `RESTIC_REPOSITORY` в app.env и ssh-дропин.

Prod app.env (convergence, 2026-08-09): narrative/pregen ключи зеркалят dev-канон (`TODAY_NARRATIVE_MODEL_PREGEN=deepseek/deepseek-v4-flash`, `TODAY_NARRATIVE_MODEL_ONDEMAND=openai/gpt-4.1-nano`, `TODAY_NARRATIVE_FALLBACK_MODELS`/`LLM_FALLBACK_MODEL=google/gemma-4-31b-it`, `TODAY_NARRATIVE_PROMPT_VERSION=today-narrative-v6`, `DAY_PREGEN_LLM_DEADLINE_SECONDS=180` и остальные `DAY_PREGEN_*`); legacy `SOLARSAGE_V2_ENABLED`/`SOLARSAGE_V2_FRONTEND_ENABLED` удалены (код работает с default False, как на dev).

⚠️ `solarsage-backup.service` работает с `ProtectHome=true` — ssh внутри юнита **не читает** `/root/.ssh/config`. SSH-конфиг для restic-хоста обязан жить в `/etc/ssh/ssh_config.d/solarsage-restic.conf` (IdentityFile `/etc/solarsage/keys/restic-sftp-ed25519`, pinned UserKnownHostsFile `/etc/solarsage/keys/restic-backup-known_hosts`).

### Egress и relay (состояние после миграции)

С нового хоста всё доступно напрямую: `api.telegram.org`, `openrouter.ai`, `api.deepseek.com`, `api.yookassa.ru`, `github.com`. TCP egress-relay (`infra/relay/`, контейнер `egress-relay` на dev-хосте `45.88.172.246:8443`) продом **больше не используется** и оставлен в standby. В prod app.env НЕ должно быть `OPENROUTER_BASE_URL` (дефолт — прямой `https://openrouter.ai/api/v1`), в installed compose НЕ должно быть `extra_hosts`.

Исторический контекст (RU-хостер, до 2026-07-23): OpenRouter — geo-block 403, api.telegram.org — SNI-DPI drop (проверено: режется TLS ClientHello по SNI на любой IP), Telegram webhook inbound — timeout. Если прод когда-либо переедет обратно в RU-юрисдикцию — поднимать relay и возвращать `extra_hosts` + `OPENROUTER_BASE_URL` (см. `infra/relay/README.md`).

Корневой дизайн-вывод: любой внешний сервис, от которого зависит продукт, обязан быть проверен на достижимость **с прод-хоста** (см. post-deploy smoke); «зелёные тесты в CI/dev» ничего не говорят о прод-egress.

## Dev host (dev.astro.vasiliy-ivanov.ru)

Дев живёт на отдельной машине (`bivanov.fvds.ru`, 45.88.172.246 — та же, где egress-relay в standby). В отличие от прода, рантайм здесь — **systemd units + локальный checkout** `/opt/solarsage-astro`, а не Compose-контейнеры.

Nginx (`/etc/nginx/sites-enabled/astro.conf`): `dev.astro.vasiliy-ivanov.ru` и `test.astro.vasiliy-ivanov.ru` → `/api/*` на `127.0.0.1:8000`, всё остальное на `127.0.0.1:3002`.

| Unit | Что запускает | Порт |
|------|---------------|------|
| `solarsage-api.service` | uvicorn `app.main:app` из `apps/api/.venv`, env из `/opt/solarsage-astro/.env` | 8000 |
| `solarsage-frontend.service` | `npm run start` (`next start`), `NODE_ENV=production`, `PORT=3002` — отдаёт prod build из `.next-prod` | 3002 |
| `solarsage-sidecar.service` | uvicorn `solarsage.app:app` из `apps/solarsage/venv`, `PYTHONPATH=apps/solarsage` | 18091 |
| `solarsage-frontend-dev-3000.service` | `pnpm next dev` (обычно inactive; 3000 поднимают вручную, nginx его не обслуживает) | 3000 |
| `solarsage-frontend-mock-dev-3001.service` | mock preview из worktree `/opt/solarsage-astro-mock-preview` (`archive/demo-origin-main`) | 3001 |
| `solarsage-synastry-reconcile.timer` (+ `.service`) | oneshot `python -m app.jobs.synastry_reconcile` каждые 5 мин — доводит зависшие synastry-репорты до ready/failed+refund | — |
| `solarsage-day-pregen.timer` (+ `.service`) | oneshot `python -m app.jobs.day_pregen` ежедневно в 04:07 — предгенерация завтрашнего дня активным пользователям на новом convergence-контракте (deterministic snapshot → selective LLM warm-up; cache hit вместо ~75 сек LLM). Юнит без valence-флагов; источники в `infra/systemd/` | — |

Девовский API-юнит больше НЕ несёт valence drop-in (`/etc/systemd/system/solarsage-api.service.d/valence.conf` удалён при convergence cutover). `TODAY_VALENCE_V1_ENABLED`, `TODAY_VALENCE_V1_DUAL_RUN`, `SOLARSAGE_V2_ENABLED`, `SOLARSAGE_V2_FRONTEND_ENABLED` — legacy routing flags, удалены из всех runtime-окружений; новый Today от них не зависит.

Новые env в `.env` (convergence RC): `DAY_PREGEN_ACTIVE_DAYS` (14), `DAY_PREGEN_LLM_ACTIVE_DAYS` (7), `DAY_PREGEN_CONCURRENCY` (3), `DAY_PREGEN_MAX_USERS` (500), `DAY_PREGEN_DETERMINISTIC_DEADLINE_SECONDS` (10), `DAY_PREGEN_LLM_DEADLINE_SECONDS` (180 — flash p95 ~124с по eval, 45с давал TimeoutError), `TODAY_NARRATIVE_MODEL_PREGEN` (`deepseek/deepseek-v4-flash`), `TODAY_NARRATIVE_MODEL_ONDEMAND` (`openai/gpt-4.1-nano`), `TODAY_NARRATIVE_FALLBACK_MODELS` (`google/gemma-4-31b-it`), `TODAY_NARRATIVE_PREGEN_MAX_OUTPUT_TOKENS` (3000), `TODAY_NARRATIVE_MAX_OUTPUT_TOKENS` (2000), `TODAY_NARRATIVE_TIMEOUT_SECONDS` (45), `TODAY_NARRATIVE_PROMPT_VERSION` (`today-narrative-v6`), `TODAY_LLM_ON_DEMAND_CONCURRENCY` (3), `LLM_FALLBACK_MODEL` (`google/gemma-4-31b-it`), `RELEASE_SHA`. Today narrative использует flash на pregen, nano on-demand и Gemma как OpenRouter fallback; фронт- и storage-контракты не меняются. Sidecar получает release identity через drop-in `/etc/systemd/system/solarsage-sidecar.service.d/release.conf` (`SOLARSAGE_RELEASE_SHA`).

Девовский `.env`: `APP_ENV=staging`, `DEV_MODE=false`, `APP_DOMAIN=dev.astro.vasiliy-ivanov.ru` → auth только через Telegram HMAC, `/api/auth/dev` на деве недоступен.

Процедура деплоя на дев — в AGENTS.md, раздел «Dev host → Деплой на дев».
