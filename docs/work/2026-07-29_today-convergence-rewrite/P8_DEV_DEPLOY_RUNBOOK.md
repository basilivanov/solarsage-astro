# P8 DEV DEPLOY RUNBOOK — Today Convergence RC

Рабочий чеклист ревьюера для P8-B/P8-C (06 ТЗ §P8). RC SHA = HEAD
`work/today-convergence-2` после принятия всех пакетов.

## P8-A preflight (состояние)

- [x] `solarsage-day-pregen.timer` остановлен и disabled; процесса day_pregen нет.
- [x] `solarsage_contracts` в обоих venv = `ss-calc-1.3.0` (api + sidecar).
- [x] Egress с dev-хоста: api.telegram.org 302, openrouter.ai 200, sidecar 200.
- [ ] Тестовая БД `today_integration_test` создана на 5433 (для PG integration).
- [ ] Unit source `infra/systemd/solarsage-day-pregen.service` без valence
  (закоммичено 831ea471) — установить на хост при deploy.
- [ ] При deploy убрать: `/etc/systemd/system/solarsage-api.service.d/valence.conf`;
  из `/opt/solarsage-astro/.env`: `TODAY_VALENCE_V1_DUAL_RUN`,
  `SOLARSAGE_V2_ENABLED`, `SOLARSAGE_V2_FRONTEND_ENABLED`.
- [ ] При deploy добавить в `.env`: `DAY_PREGEN_ACTIVE_DAYS=14`,
  `DAY_PREGEN_LLM_ACTIVE_DAYS=7`, `DAY_PREGEN_CONCURRENCY=3`,
  `DAY_PREGEN_MAX_USERS=500`, `DAY_PREGEN_DETERMINISTIC_DEADLINE_SECONDS=10`,
  `DAY_PREGEN_LLM_DEADLINE_SECONDS=45`, `TODAY_NARRATIVE_MAX_OUTPUT_TOKENS=700`,
  `TODAY_NARRATIVE_TIMEOUT_SECONDS=45`,
  `TODAY_NARRATIVE_PROMPT_VERSION=today-narrative-v2`,
  `TODAY_LLM_ON_DEMAND_CONCURRENCY=3`, `RELEASE_SHA=<RC SHA>`.

## P8-B deploy (на dev-хосте, /opt/solarsage-astro)

1. `pg_dump` backup: `docker exec solarsage-db pg_dump -U <user> astro >
   /var/backups/solarsage/pre-convergence-$(date +%Y%m%d-%H%M).sql` (через
   sudo, креды из .env).
2. `git fetch && git checkout <RC SHA>` (ветка work/today-convergence-2 →
   main merge решается отдельно; deploy из RC SHA напрямую допустим —
   зафиксировать решение владельца о ветке).
3. Migration rehearsal: `alembic upgrade head` → `alembic current`;
   downgrade/upgrade на today_integration_test (0027-0030) уже покрыт
   PG integration тестами.
4. Frontend build: `NODE_ENV=production npm run build` (distDir
   `.next-prod`).
5. Обновить `.env` и unit (см. P8-A), `systemctl daemon-reload`.
6. Restart: `systemctl restart solarsage-api solarsage-sidecar
   solarsage-frontend`.
7. Health gates (HARD FAIL при любом несовпадении):
   - `curl 127.0.0.1:8000/api/health` → `git_sha == RC SHA`, `release_sha
     == RC SHA`.
   - `curl 127.0.0.1:18091/v1/health` → `calculation_version ==
     ss-calc-1.3.0`, `release_sha == RC SHA`, ephemeris identity
     `se-stellium-1800-2399-20260721`.
   - Frontend 3002 → 200.
   - `ss -tlnp | grep -E ':8000|:3002|:18091'` — ровно один
     systemd-owned listener на порт, без ручного uvicorn/next.

## P8-C acceptance

1. Acceptance cohort (test fixture setup, НЕ production-only route):
   - exact / bucket / unknown профили; full / preview / locked access;
   - фиксированные даты. Seeder через существующий Telegram HMAC +
     profile API (`scripts/generate-telegram-test-initdata.py` для
     initData). IDs учесть в E2E cleanup.
2. Targeted smoke + real E2E без page.route: 8 сценариев 06 §P8-C.
3. Bounded pregen one-shot ТОЛЬКО на acceptance cohort:
   `systemctl start solarsage-day-pregen.service` (или ручной run с
   `--limit`), проверить snapshots/narratives для cohort.
4. Cache hit: повторный GET того же дня → нет второго provider call
   (journalctl без narrative_generation_started повтора; `meta` быстрый).
5. Counters: latency (cache hit p95 <1s, cold <5s), snapshot/lease/LLM
   counters из логов.
6. `journalctl -u solarsage-api -u solarsage-sidecar -u
   solarsage-frontend --since deploy`: нет crash-loop,
   system.error, failed leases подряд, PII/secrets.
7. Владелец принимает UI + visual baseline.
8. Только после 1-7: `systemctl enable --now solarsage-day-pregen.timer`.
