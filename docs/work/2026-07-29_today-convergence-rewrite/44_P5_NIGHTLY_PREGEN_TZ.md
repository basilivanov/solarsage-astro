# 44 — P5 NIGHTLY PREGEN TZ — Today Convergence Rewrite

Controller packet по coder-loop §10.7. Архитектор: main agent. Кодер: codex CLI
(первый), cwd `/tmp/solarsage-convergence-impl`, ветка `work/today-convergence-2`.

ВАЖНО: ты и есть coder. Skill coder-loop использовать НЕЛЬЗЯ — задачу
выполняешь сам и отчитываешься здесь ревьюеру. Параллельный кодер работает
только с `__tests__/fixtures/` — backend трогает он в этой ветке НЕ (ты —
единственный backend writer здесь).

## 1. Packet title

P5 (W5-S2) — nightly pregen на новом контракте: двухступенчатый one-shot job
(deterministic snapshot → selective LLM warm-up) для bounded cohort,
idempotent, с typed outcomes и structured summary.

## 2. Phase / Wave

W-TODAY-CONVERGENCE-REWRITE / P5. Зависит от принятых: P2 runtime, P3
snapshots/lease, P6 narrative, P4-D2 endpoint (всё в HEAD ветки).

## 3. Modules

- Переписываемый: `M-JOBS-DAY-PREGEN` — apps/api/app/jobs/day_pregen.py
- Новый (рекомендуется): `M-TODAY-PREGEN-SERVICE` —
  apps/api/app/services/today_pregen_service.py (cohort + двухстадийная
  логика; job остаётся тонким CLI)
- Изменяемый: `M-CONFIG` — apps/api/app/core/config.py (6 новых settings)
- Tests: apps/api/tests/test_day_pregen_job.py (переписать) + новый
  apps/api/tests/test_today_pregen_service.py

## 4. Goal

`python -m app.jobs.day_pregen` (тот же entry point, что у dev timer) за один
one-shot run: выбирает bounded cohort активных пользователей, для каждого
публикует deterministic snapshot на локальное ЗАВТРА пользователя, и для
подмножества (full access + свежая активность ≤7д) прогревает narrative через
существующие lease + generate_today_narrative. Никакого legacy
TodayService/valence. Impression НЕ создаётся.

## 5. Норматив (прочитать перед кодированием)

- `docs/work/2026-07-29_today-convergence-rewrite/05_W5_W8_OPERATIONS_AND_RELEASE_TZ.md`
  §2.1-2.4 (строки 42-122) — cohort, две стадии, idempotency, retry.
- `docs/work/2026-07-29_today-convergence-rewrite/06_DEV_RELEASE_EXECUTION_PLAN_TZ.md`
  P5 (строки 220-242).
- Существующее:
  - legacy job: apps/api/app/jobs/day_pregen.py — посмотреть ТОЛЬКО источник
    активности cohort (какой запрос/таблица даёт «active за N дней») и CLI
    conventions; вся TodayService-логика заменяется.
  - `calculate_today_convergence(profile, target_date)` —
    services/today_convergence_runtime.py
  - `build_today_convergence_snapshot_document` —
    services/today_convergence_snapshot.py
  - `TodaySnapshotService.publish_or_load` —
    services/today_snapshot_service.py
  - `TodayNarrativeLeaseService.acquire/complete_*` —
    services/today_narrative_lease_service.py
  - `generate_today_narrative` — services/today_narrative_service.py
  - `AccessService.can_access_day` — services/access_service.py
  - `resolve_user_local_date` — services/user_local_date.py
  - Существующие registry события: `day.pregen_started`,
    `day.pregen_user_finished`, `day.pregen_completed` (уже в
    logging_events.py — использовать их, новые НЕ добавлять).

## 6. Exact write scope

- apps/api/app/jobs/day_pregen.py (переписать)
- apps/api/app/services/today_pregen_service.py (новый)
- apps/api/app/core/config.py — добавить (typed, с валидацией >0):
  `day_pregen_active_days=14` (DAY_PREGEN_ACTIVE_DAYS),
  `day_pregen_llm_active_days=7` (DAY_PREGEN_LLM_ACTIVE_DAYS),
  `day_pregen_concurrency=3` (DAY_PREGEN_CONCURRENCY),
  `day_pregen_max_users=500` (DAY_PREGEN_MAX_USERS),
  `day_pregen_deterministic_deadline_seconds=10`
  (DAY_PREGEN_DETERMINISTIC_DEADLINE_SECONDS),
  `day_pregen_llm_deadline_seconds=45` (DAY_PREGEN_LLM_DEADLINE_SECONDS)
- apps/api/tests/test_day_pregen_job.py (переписать — тонкий CLI shell)
- apps/api/tests/test_today_pregen_service.py (новый)

## 7. Frozen / Out of scope

- НЕ менять: api/*, today_convergence_*.py (кроме использования),
  today_snapshot_service.py, today_narrative_*.py, access_service.py,
  user_local_date.py, logging_events.py, миграции, systemd-файлы
  (обновление timer unit — P8-A, не этот packet), frontend.
- НЕ читать флаги TODAY_VALENCE_V1_*/SOLARSAGE_V2_* — новый job от них не
  зависит.
- НЕ создавать impression rows и не трогать TodayPayloadCache.

## 8. Функциональные требования

### 8.1 Cohort (05 §2.1)

- Активность: тот же источник, что использует legacy job (найти в старом
  day_pregen.py — users с session/active use за последние
  `day_pregen_active_days`).
- Профиль полный: дата/место/timezone рождения заполнены; `exact`, `bucket`,
  `unknown` режимы допускаются одинаково (resolve_profile_birth_time
  валиден).
- Доступ к Дню: `can_access_day` != locked (preview допустим для
  deterministic stage; LLM warm-up только full — см. 8.2).
- Детерминированный порядок: самые недавно активные первыми; cap
  `day_pregen_max_users` — при превышении job завершает обработку cap'ом и
  помечает итог typed outcome `cohort_capped` (не пытается обработать всю
  базу).
- Невалидные/неположительные settings → fail-closed ДО выбора cohort
  (exit 1 с typed log).

### 8.2 Две стадии per user (05 §2.2)

targetDate = завтра в timezone пользователя (`resolve_user_local_date(user,
now + 1 day)` — аккуратно: resolver принимает now; передай now+24h).

1. Deterministic: cache-проверка (load_current по (user, targetDate) +
   profile_hash) → hit: skip; miss: `calculate_today_convergence` → Built:
   `build_..._document` → `publish_or_load` (или superseding при смене
   profile_hash — как в day endpoint); Unavailable → typed per-user outcome
   `deterministic_unavailable`, к стадии 2 не переходить.
   Per-user deterministic deadline: `day_pregen_deterministic_deadline_seconds`.
2. Selective LLM warm-up: только если access == full И последняя активность
   ≤ `day_pregen_llm_active_days`. `lease.acquire(...)` → claim:
   `generate_today_narrative` (deadline `day_pregen_llm_deadline_seconds`)
   → `complete_ready` / `complete_unavailable(error_code, next_retry_at)`.
   Skip (ready/in_flight/cooldown) — typed outcome, не ошибка.
   Максимум 3 bounded попытки в одном run: сразу, затем по due-time +5 и
   +20 минут (интервалы инжектируемы для тестов; в реальном run — ждать,
   provider slot между попытками не удерживается). Исчерпание →
   `unavailable` с next_retry_at — НЕ считается успешным pregen.
3. Неуспех стадии 2 НЕ удаляет deterministic данные.

### 8.3 Idempotency и concurrency

- Повторный запуск job — безопасен: publish on-conflict reuse, lease skip;
  тест: второй run делает ноль новых snapshots и ноль provider calls.
- Per-user concurrency через asyncio.Semaphore(`day_pregen_concurrency`);
  per-user исключение логируется (type-only) и не рушит batch.
- Job дожидается всех своих bounded LLM-задач перед итоговым summary
  (05 §2.4).

### 8.4 Logging / summary

- `day.pregen_started` (cohort params, cap), per-user
  `day.pregen_user_finished` (typed outcome: snapshot_hit / published /
  deterministic_unavailable / llm_ready / llm_unavailable / llm_skipped_*),
  `day.pregen_completed` (summary counters: cohort_size, deterministic
  published/hit/failed, llm ready/unavailable/skipped, duration).
- PII/raw data запрещены; correlation_id на run.
- Ошибка логгера не ломает job.

### 8.5 Тесты (минимум, fake sidecar/LLM)

- cohort selection: exact/bucket/unknown допущены; incomplete profile
  excluded; inactive excluded; locked excluded из LLM stage (но допустим в
  deterministic? — НЕТ: locked не имеет access к Дню → исключён из cohort);
  cap → typed `cohort_capped`.
- deterministic stage: miss → publish; second run → hit, zero sidecar calls.
- LLM stage: full+свежий → generate вызван; preview или stale>7d → нет;
  failure → deterministic snapshot остаётся; 3 попытки bound (fake clock),
  потом unavailable + next_retry_at.
- invalid settings → fail-closed до cohort (exit 1, typed log).
- per-user exception не рушит batch (один пользователь падает, остальные
  завершаются, summary фиксирует).
- summary counters соответствуют per-user outcomes.
- impression поля snapshots остаются NULL после run.

## 9. Must-preserve invariants

- Существующие зелёные тесты не ломаются; legacy TodayService не меняется.
- `python3 scripts/grace_lint.py apps/api/app` PASS, ruff PASS,
  guardrails PASS.
- Job не импортирует TodayService после переписывания (grep gate в тесте
  или проверка ревьюером).

## 10. Verification

```bash
cd /tmp/solarsage-convergence-impl/apps/api
/opt/solarsage-astro/apps/api/.venv/bin/python -m pytest \
  tests/test_today_pregen_service.py tests/test_day_pregen_job.py -q -p no:cacheprovider
/opt/solarsage-astro/apps/api/.venv/bin/python -m pytest tests/ -q \
  -m "not integration and not benchmark" -p no:cacheprovider 2>&1 | tail -3
/opt/solarsage-astro/apps/api/.venv/bin/python -m ruff check app
cd /tmp/solarsage-convergence-impl && python3 scripts/grace_lint.py apps/api/app && \
  python3 scripts/check_logging_guardrails.py
```

## 11. Expected evidence

- Список файлов; вывод §10; per-user outcome enum; пример summary log
  payload; подтверждение отсутствия TodayService импорта в job.

## 12. Escalation rule

Нужно менять runtime/snapshot/narrative/lease internals, источник
активности не находится или требует новой таблицы → СТОП, доложить.

## 13. No-commit rule

Ничего не коммить и не пушить — коммит делает ревьюер.
