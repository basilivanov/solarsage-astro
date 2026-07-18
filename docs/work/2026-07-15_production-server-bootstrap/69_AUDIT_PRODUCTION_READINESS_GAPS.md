# Production readiness audit — remaining launch gaps

Дата аудита: 2026-07-15. Режим: read-only архитектурный аудит текущей ветки `infra/production-bootstrap`. Production apply/deploy, SSH, сеть, GitHub API, commit и push не выполнялись. Secret values и `.env.production` не читались/не выводились.

## Executive status

Текущая автоматизация ещё не готова к безопасному production launch. R11/R12 закрыли значительную часть OS/TLS/backup mechanics, но остаются реальные runtime/security gaps. До ручной команды запуска требуется закрыть P0, затем критичные P1 и выполнить fresh-host rehearsal на тестовом сервере.

## P0 — launch blockers

### P0.1 Fresh-host GitHub/SSH sequence циклический

Runbook ставит `prod-github-access.sh --apply` раньше host-prepare (`docs/PRODUCTION_RUNBOOK.md:103-110`), но access apply уже требует:

- checkout private/public keys (`scripts/prod-github-access.sh:214-222`);
- Actions public key (`:244-257`);
- установленный forced wrapper (`:260-264`).

Wrapper устанавливается только host-prepare (`scripts/prod-host-prepare.sh:893-896`). OS bootstrap создаёт user/home, но не полный key material (`scripts/prod-os-bootstrap.sh:379-407`). Нет canonical команды безопасного создания server checkout key и `/etc/solarsage/keys`.

Нужно: отдельный non-cyclic bootstrap flow с actor/owner/mode:

1. OS bootstrap и operator SSH proof;
2. host directories + forced wrapper;
3. server checkout key generation без вывода private material;
4. operator регистрирует checkout public key read-only в GitHub;
5. operator передаёт Actions public key;
6. GitHub access apply/preflight;
7. repository private transition;
8. source-readiness workflow;
9. только затем deploy.

### P0.2 Backup, Alembic и API могут работать с разными БД

Env loader проверяет `DATABASE_URL` только как non-empty/non-SQLite (`scripts/lib/prod-env-loader.sh:174-176`). Backup/pg_isready жёстко используют `127.0.0.1:5433` и `POSTGRES_*` (`scripts/prod-deploy.sh:391-400`, `scripts/prod-backup.sh:269-272`), тогда Alembic/API используют `DATABASE_URL` (`apps/api/alembic/env.py:12-21`, `apps/api/app/db/session.py:65-75`).

Нужно: единый canonical DB identity validator до backup/migration:

- PostgreSQL asyncpg DSN;
- exact host `127.0.0.1`, port `5433`;
- username/database равны `POSTGRES_USER`/`POSTGRES_DB`;
- password consistency проверяется без логирования;
- SQLite, alternate host/port/db/user и credential URL leakage fail-closed.

Предпочтительно собирать runtime DSN из одной validated структуры, а не поддерживать независимые значения.

### P0.3 Deploy in-place и не имеет реального rollback

`prod-deploy.sh` checkout-ит target и затем пересоздаёт live `.venv`, sidecar venv и frontend build на месте (`scripts/prod-deploy.sh:252-348`). Failure trap только печатает SHA (`:82-96`). Миграция выполняется при работающем старом API, затем сервисы переключаются последовательно (`:399-461`). Частичный build или incompatible schema может оставить недетерминированный runtime.

Нужно:

- immutable release directory по commit SHA;
- dependency/build/preflight до переключения live symlink;
- explicit migration compatibility policy (expand/contract либо maintenance/drain);
- previous-release pointer;
- атомарное переключение runtime paths;
- проверенный rollback, учитывающий schema compatibility;
- signal-safe remote deploy execution, не зависящий от живого SSH job.

### P0.4 Нет общего destructive-operation lock/state machine

Deploy, backup, restore и offsite maintenance используют разные locks либо не используют общий lock (`scripts/prod-deploy.sh:193-199`, `scripts/prod-backup.sh:141-213`, `scripts/prod-db-restore.sh:246-323`). Restore не учитывает maintenance timer/service.

Нужно: общий `/run/solarsage-maintenance.lock` и состояния для deploy/backup/restore/restic maintenance; взаимное исключение, stale-state recovery, проверка всех timers/services и единая recovery procedure.

### P0.5 `.env.production` допускает process-control injection

`prod-env-loader.sh` принимает любое имя по общему regex и экспортирует все пары (`scripts/lib/prod-env-loader.sh:103-147,200-235`). Значения `PATH`, `BASH_ENV`, `ENV`, `LD_*`, `NODE_OPTIONS`, `PYTHONPATH`, `GIT_*`, `SSH_ASKPASS` способны влиять на последующие `pnpm`, Python, Bash, Git и systemd services. Harness использует безопасный stub и этого не доказывает.

Нужно:

- exact allowlist production env keys;
- deny process-control names/prefixes;
- rejection unknown keys до любого build/restart;
- sanitized fixed environment для build/install;
- runtime secrets передавать только минимальным migration/backup/preflight subprocesses;
- tests с canaries `BASH_ENV`, `PATH`, `NODE_OPTIONS`, `LD_PRELOAD`, `PYTHONPATH`, `GIT_DIR`, `GIT_CONFIG_*`.

## P1 — high priority before launch

### P1.1 Offsite bootstrap/retention order

Runbook требует offsite enabled, но repository init описан после host-prepare. Host-prepare preflight уже делает `restic snapshots`, поэтому fresh uninitialized repo блокирует flow. `--local-only` backup при enabled offsite всё равно может запустить retention; restore вызывает такой backup перед destructive operation.

Нужно:

- separate `offsite init` и `offsite check`;
- credentials/repository init до host readiness gate;
- production launch требует `OFFSITE_BACKUP_ENABLED=true` и verified snapshot roundtrip;
- local-only никогда не удаляет retention candidates при enabled offsite без explicit operator flag.

### P1.2 Backup provenance и restore recovery

Backup сохраняет dump+checksum, но не commit SHA, Alembic state, DB identity, infra fingerprint или cache identities. Restore просит вручную угадать matching commit и при partial failure только сообщает safety dump path.

Нужно: hashed manifest рядом с dump, exact offsite proof, disposable restore drill и автоматизированная recovery-from-prebackup команда.

### P1.3 Production alerting отсутствует

Backup/maintenance пишут локальные события, но нет подключённого production `OnFailure`, heartbeat, disk/cert/backup-age/offsite alarms. Legacy alert scripts не каноничны и содержат dev assumptions.

Нужно: отдельный production alert unit с отдельным credential/chat, fail-closed HTTP delivery tests и controlled failure injection.

### P1.4 Ephemeris readiness недостаточна

Host prepare создаёт directory, deploy проверяет только readable/traversable path. Нет versioned artifact, required-file inventory/checksum и engine proof. Часть расчётов использует hardcoded `/opt/sweph/ephe`, обходя settings.

Нужно: versioned ephemeris bundle, SHA256 manifest, единый path, oracle probes и health response с доказанным engine/data identity.

### P1.5 SSH hardening не завершён

Bootstrap открывает SSH, но не канонизирует `PermitRootLogin`, `PasswordAuthentication`, operator key proof и lockout-safe rollback.

Нужно: сначала установить/проверить operator key во второй сессии, затем managed sshd drop-in, `sshd -t`, reload с rollback timer, отключение password/root login.

### P1.6 Deploy не требует зелёный release gate

CI не запускается на каждый push main, deploy workflow не связан с exact green check; Next build игнорирует TypeScript errors. Нужен дешёвый targeted reusable release gate/required check по exact SHA с учётом лимита Actions minutes.

### P1.7 GitHub Actions timeout меньше worst-case deploy

Workflow timeout 45 минут, backup/offsite способен идти до 2–3 часов. Обрыв SSH может оставить partial in-place deploy. Предпочтительно запускать remote systemd deploy job и получать status/result, а Actions использовать только как дешёвый trigger/poll.

### P1.8 Telegram production identity не доказана

Проверяется только non-empty token и строка `BOT_USERNAME`; token другого bot может пройти. Нет автоматизированного `getMe` identity proof, menu/WebApp URL/domain/commands checklist и real HMAC auth smoke.

Нужно: secret-safe bot id/username verification, BotFather checklist evidence и реальный Telegram WebApp auth e2e перед launch.

### P1.9 Sidecar identity/health расходятся

Sidecar health может вернуть default `git_sha=dev` и устаревшую calculation version; unit не привязывает их к immutable release. Deploy health проверяет только HTTP success.

Нужно: shared calculation version + release SHA в health JSON и exact assertions после restart.

### P1.10 Host-prepare rollback не восстанавливает runtime state

File transaction rollback не возвращает enabled/active state units/timers/container. Нужен snapshot/restore runtime states либо честная автоматизированная recovery checklist с post-failure audit.

### P1.11 Production secrets доступны build/install lifecycle

После loader весь env передаётся `pnpm install`, pip install и Next build. Dependency lifecycle получает DB/bot/LLM/restic credentials.

Нужно: build под `env -i` с минимальным allowlist до загрузки secrets; secrets только для узких preflight/backup/migration процессов.

## P2 — reproducibility and operational debt

- Python deploy каждый раз upgrades pip/wheel и разрешает broad dependency ranges; production image `postgres:15` mutable. Нужны pinned lock/hash artifacts и image digest/minor upgrade process.
- Cache keys versioned, поэтому blanket invalidation не нужен, но нет CI gate, требующего bump identity при cache-affecting diff.
- Runbook содержит duplicate/out-of-order GitHub steps, не везде указывает actor (`root`/`astro`), expected rc/output и evidence path.
- Payment endpoint намеренно отвечает 503. Перед launch зафиксировать scope как free launch либо реализовать provider fulfillment отдельным ТЗ.

## Recommended implementation order

1. Завершить R13 isolated harnesses без false-green.
2. Fresh-host/key/bootstrap ordering + lockout-safe SSH hardening.
3. Exact env allowlist/process-control protection + canonical DB identity.
4. Immutable release deploy, migration policy, global maintenance lock and rollback.
5. Backup/offsite/restore state machine, provenance manifest, retention correction, alerts and restore drill.
6. Ephemeris artifact/readiness and exact sidecar identity.
7. Cheap exact-SHA release gate and sanitized reproducible builds.
8. Telegram/BotFather/auth launch proof.
9. Consolidated numbered runbook and full fresh-host rehearsal on test server.

Production launch остаётся отдельной ручной командой пользователя после закрытия и независимой приёмки всех launch gates.
