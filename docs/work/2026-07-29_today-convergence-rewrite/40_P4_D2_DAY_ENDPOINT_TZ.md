# 40 — P4-D2 DAY ENDPOINT ORCHESTRATION TZ — Today Convergence Rewrite

Controller packet по coder-loop §10.7. Архитектор: main agent. Кодер: codex CLI
в tmux astro2:0.0 (cwd `/tmp/solarsage-convergence-impl`).

## 1. Packet title

P4-D2 — `GET /api/day/{date}` и `POST /api/day/{date}/retry` на новом
`TodayConvergencePayload` envelope: snapshot publish/load, narrative lease +
BackgroundTasks LLM, access projections. Атомарное переключение с legacy
TodayService path на этом endpoint.

## 2. Phase / Wave

W-TODAY-CONVERGENCE-REWRITE / P4 (W5-S1), срез D2. Зависит от принятых:
P4-D1 projection (397a1278), P6 narrative (packet 39), P3 snapshots/lease.

## 3. Modules

- Изменяемый: `M-API-DAY` — apps/api/app/api/day.py
- Изменяемый: `M-TODAY-SNAPSHOT-SERVICE` — apps/api/app/services/today_snapshot_service.py
  (только добавить current-snapshot lookup)
- Изменяемый: `M-TODAY-CONVERGENCE-SNAPSHOT` — apps/api/app/services/today_convergence_snapshot.py
  (только экспортировать profile-hash helper)
- Изменяемый: `M-CONFIG` — apps/api/app/core/config.py (1 новая настройка)
- Тесты: apps/api/tests/test_day_endpoints.py (переписать), новый
  apps/api/tests/test_day_convergence_api.py, triage legacy HTTP-тестов (§10).
- Generated contracts: packages/contracts/* (регенерация после смены
  response_model).

## 4. Goal

`GET /api/day/{date}` возвращает `TodayConvergencePayload` по 04 §3/§6:
cache hit не запускает LLM и sidecar; cold GET публикует deterministic
snapshot, создаёт narrative lease, отвечает `contentState=pending` и запускает
LLM через BackgroundTasks; preview получает server-side teaser; locked — без
snapshot и расчёта; технический сбой расчёта — HTTP 200 `state=unavailable`.

## 5. Норматив (прочитать перед кодированием)

- 04 §3.1-3.3 (envelope, матрица), §5 (local date), §6 (HTTP-поверхность,
  строки 305-343) — `docs/work/2026-07-29_today-convergence-rewrite/04_W2_W3_RUNTIME_CONTRACT_TZ.md`
- 05 §2.4 (on-demand orchestration без очереди, строки 106-122) и §4
  (concurrency invariants) — тот же каталог, `05_W5_W8_OPERATIONS_AND_RELEASE_TZ.md`
- Существующие интерфейсы:
  - projection: `app/services/today_convergence_projection.py`
    (`project_snapshot_payload`, `project_empty_payload`)
  - runtime: `calculate_today_convergence(profile, target_date, *, client=None)`
    в `app/services/today_convergence_runtime.py`
  - document builder: `build_today_convergence_snapshot_document(profile,
    calculation)` в `app/services/today_convergence_snapshot.py`
  - snapshot service: `TodaySnapshotService.publish_or_load /
    publish_superseding / load_owned` в `app/services/today_snapshot_service.py`
  - lease: `TodayNarrativeLeaseService.acquire/complete_ready/
    complete_unavailable/load` в `app/services/today_narrative_lease_service.py`
  - narrative: `generate_today_narrative` из packet 39 (фактическую сигнатуру
    взять из `app/services/today_narrative_service.py`)
  - access: `AccessService(db).can_access_day(user.id, target_date)` →
    `ContentAccessState` (см. текущий day.py :171)
  - local date: `resolve_user_local_date(user, datetime.now(UTC))`

## 6. Exact write scope

- `apps/api/app/api/day.py` — переключить `get_day`; добавить `retry_day`;
  legacy focus-drilldown endpoint в этом файле НЕ трогать (P4-D3 отдельно).
- `apps/api/app/services/today_snapshot_service.py` — добавить
  `load_current(user_id, target_date) -> TodaySnapshot | None`: head
  supersedes-цепочки (published, без child rows). Больше ничего в файле не
  менять.
- `apps/api/app/services/today_convergence_snapshot.py` — сделать публичный
  `compute_today_profile_hash(profile, resolution) -> str` (тонкая обёртка
  над существующим `_profile_hash`; сам `_profile_hash` не трогать).
- `apps/api/app/core/config.py` — добавить
  `today_llm_on_demand_concurrency: int = 3` (alias
  `TODAY_LLM_ON_DEMAND_CONCURRENCY`).
- `apps/api/app/services/today_narrative_service.py` — НЕ менять; только
  использовать.
- `apps/api/tests/test_day_endpoints.py` — переписать под новый контракт.
- `apps/api/tests/test_day_convergence_api.py` — новый HTTP contract suite.
- Triage legacy тестов по §10 (удаления только из allowlist-правила).
- `packages/contracts/*` — регенерировать через `pnpm contracts:generate`.
- `apps/api/app/core/logging_events.py` — НЕ менять (события уже есть из
  P3/P6); использовать существующие `day.snapshot_lookup_hit/miss`,
  `day.snapshot_published`, `day.snapshot_conflict_reused`,
  `day.snapshot_superseded`, `day.viewed`, `day.narrative_generation_*`.

## 7. Frozen / Out of scope

- НЕ менять: TodayService и его unit-тесты (W9 позже), calendar_service,
  checkin, today_convergence runtime/pipeline/projection/narrative/lease
  логику, schemas/today_convergence.py, миграции, frontend.
- НЕ удалять legacy `TodayPayload` из `PUBLIC_CONTRACT_ROOTS` (это W8).
- НЕ реализовывать: sphere drilldown endpoint (P4-D3), calendar changes
  (P4-D3), pregen (P5), impression endpoint (уже есть).
- Никакого parallel compatibility envelope (запрещено 06 §5).

## 8. Функциональные требования

### 8.1 GET /api/day/{date} (`date=YYYY-MM-DD` или `today`)

Поток (по шагам, все шаги существующими сервисами):

1. `require_session` (как сейчас). Невалидная session → 401 (middleware).
2. `today` → `resolve_user_local_date`; ISO parse; невалидная дата или
   невалидная tz профиля → **422** (04 §6; legacy 400 больше не возвращается
   на этом endpoint).
3. Onboarding check (существующая логика :158-167 day.py) → 422.
4. `access = AccessService(db).can_access_day(user.id, target_date)`.
5. `locked` → `project_empty_payload(unavailable=False, access)`; sidecar и
   snapshot НЕ вызываются (assert в тесте).
6. `full`/`preview`:
   a. `resolution = resolve_profile_birth_time(profile)`;
      `profile_hash = compute_today_profile_hash(profile, resolution)`.
   b. `snapshot = TodaySnapshotService(db).load_current(user.id, target_date)`.
   c. Cache hit: snapshot есть и `snapshot.profile_hash == profile_hash` →
      `narrative = TodayNarrativeLeaseService(db).load(snapshot.id,
      settings.today_narrative_prompt_version)` →
      `project_snapshot_payload(snapshot, narrative, access)` → 200.
      Sidecar и LLM НЕ вызываются. Лог `day.snapshot_lookup_hit`.
   d. Cold: `day.snapshot_lookup_miss` → `calculate_today_convergence`:
      - `Unavailable` → `project_empty_payload(unavailable=True, ...)`,
        HTTP 200, snapshot не публикуется.
      - `Built` → `build_today_convergence_snapshot_document` →
        если старый snapshot существовал (другой profile_hash) —
        `publish_superseding`, иначе `publish_or_load` → логи publish/
        conflict/superseded по факту.
   e. Только для `full` (НЕ preview): narrative orchestration по 05 §2.4 —
      `narrative = lease.load(...)`; если `ready` → payload ready;
      иначе `lease.acquire(...)`:
      - claim получен → ответ `contentState=pending` + BackgroundTasks:
        process limiter (asyncio.Semaphore
        `settings.today_llm_on_demand_concurrency`, один на приложение) →
        внутри `generate_today_narrative(snapshot, prompt_version=...)` →
        `complete_ready(content_json)` / `complete_unavailable(error_code,
        next_retry_at=now+5min первый retry)`. Background обязан всегда
        завершаться ready|unavailable (no eternal pending); исключение в
        background → complete_unavailable("internal_error", next_retry_at).
      - skip (in_flight/cooldown/ready/exhausted) → payload с contentState
        из фактического narrative row (pending/unavailable/ready).
   f. `preview` → `project_snapshot_payload(snapshot, None, access)`
      (contentState=not_needed через проекцию); LLM не запускается.
7. Ответ — `TodayConvergencePayload` (response_model на роуте).
8. Логи: `day.viewed` (существующий, если уместен) и snapshot-события;
   correlation_id из request; PII/raw data запрещены. Ошибка логгера не
   ломает flow.

### 8.2 POST /api/day/{date}/retry

- Тот же date/onboarding/access поток. Idempotent:
  - нет snapshot → тот же cold path, что GET;
  - narrative `unavailable` и `next_retry_at <= now` → повторный acquire +
    background (тот же код, что GET); ответ 200 envelope;
  - narrative `pending` с живым lease → **202 + Retry-After** (секунды до
    lease_until/next_retry_at), без второго generation call;
  - `ready` → 200 envelope (no-op).
- Cooldown/second concurrent retry не создаёт второй provider call (lease
  single-flight; тест с двумя параллельными retry).

### 8.3 Удаляемое из get_day

`authorize_today_preview`, `resolve_today_selection_context`,
`resolve_today_access_for_selection`, `TodayService.get_today_payload` и
весь preview-transport guard из `get_day` — удаляются из этого handler
(сами модули не трогаем: W9). Новый код не читает `TODAY_VALENCE_V1_*`,
`SOLARSAGE_V2_*` флаги.

### 8.4 GRACE / logging

- Обновить MODULE_CONTRACT/MODULE_MAP M-API-DAY (emitted_logs — реальные).
- Новые публичные функции — FUNCTION_CONTRACT.
- Структурные логи на границах: lookup hit/miss, publish outcome, narrative
  acquire/skip, background complete/fail. Не логировать в циклах.

## 9. Must-preserve invariants

- Legacy TodayService unit-тесты (test_today_v2_payload, test_today_service_v2_*,
  scoring/valence/semantic suites) остаются зелёными — сервис не меняется.
- Impression endpoint (`POST /api/day/snapshots/{id}/impression`) не меняется
  и остаётся зелёным.
- `pnpm contracts:check` зелёный после регенерации.
- Все PG integration-тесты (TODAY_TEST_POSTGRES_URL) зелёные.
- Ни один GET не создаёт snapshot для locked; ни один cache hit не вызывает
  sidecar/LLM (assert по mocks).

## 10. Legacy HTTP-test triage (правило)

После переключения endpoint часть legacy тестов упадёт. Правило (W9
manifest, «переписываются/расширяются под новый путь» + staged removal):

- `test_day_endpoints.py` — переписать: 401/422-грани + happy path на новом
  envelope (mock `calculate_today_convergence` и narrative).
- HTTP-тесты, фиксирующие УДАЛЁННЫЙ legacy wire-контракт GET /api/day
  (topFlags, dayStatus, v2-block, preview header transport,
  frozen v2 contract через HTTP) — удалить В ТОМ ЖЕ changeset, каждый файл с
  однострочным обоснованием в отчёте (равноценное покрытие добавляется в
  test_day_convergence_api.py). Кандидаты (проверить по факту падений):
  test_today_preview_transport.py, test_today_preview_access.py,
  test_frozen_day_contract.py, test_today_focus_contract.py (HTTP часть),
  test_llm_fallback.py, test_llm_why_sections_schema.py,
  test_today_concrete_advice_retry.py, test_today_llm_gather_overlap.py,
  test_pipeline_integration.py, test_critical_gaps.py (day-часть),
  test_day_no_birthday_fallback.py, integration/test_cache.py,
  integration/test_locked_day.py, integration/test_user_flow.py.
- Тесты, фиксирующие поведение, живущее и после переключения (auth 401,
  onboarding 422, invalid date) — сохранить через переписанный
  test_day_endpoints.py / новый suite.
- Unit-тесты TodayService internals (без HTTP) — НЕ трогать.
- Запрещено: удалять тест «чтобы CI стал зелёным» без равноценного покрытия
  грани в новом suite; xfails/skip как способ уйти от triage.

## 11. Новые HTTP-тесты (test_day_convergence_api.py), минимум

- full cold hero: publish + pending + background вызван один раз; повторный
  GET → ready после complete (без второго sidecar/provider call).
- full warm hit: snapshot существует → ни sidecar, ни LLM (assert mocks).
- preview: snapshot публикуется, teaser ≤3 сфер, events скрыты, LLM не
  запускается.
- locked: пустой envelope, snapshot/sidecar не вызываются.
- state=unavailable: calculate → Unavailable → HTTP 200, snapshotId=null.
- invalid date / мусорная tz → 422; not onboarded → 422; no session → 401.
- retry: pending+lease alive → 202 + Retry-After; unavailable с due retry →
  новый acquire; ready → no-op 200; два параллельных retry → один acquire.
- background exception → narrative unavailable с next_retry_at (не вечный
  pending).
- cross-user: чужой snapshot недостижим через этот endpoint (load_current по
  user_id) — smoke на уровне сервиса уже есть в P3-тестах.

## 12. Verification

```bash
cd /tmp/solarsage-convergence-impl/apps/api
/opt/solarsage-astro/apps/api/.venv/bin/python -m pytest \
  tests/test_day_convergence_api.py tests/test_day_endpoints.py \
  tests/test_today_snapshot_impression_api.py -q -p no:cacheprovider
/opt/solarsage-astro/apps/api/.venv/bin/python -m pytest tests/ -q \
  -m "not integration and not benchmark" -p no:cacheprovider 2>&1 | tail -3
/opt/solarsage-astro/apps/api/.venv/bin/python -m ruff check app
cd /tmp/solarsage-convergence-impl && python3 scripts/grace_lint.py apps/api/app && \
  python3 scripts/check_logging_guardrails.py && pnpm contracts:check
# PG integration (URL выдать из .env как раньше):
cd apps/api && TODAY_TEST_POSTGRES_URL=... /opt/solarsage-astro/apps/api/.venv/bin/python -m pytest \
  tests/test_today_snapshot_postgres.py tests/test_today_snapshot_lineage_postgres.py \
  tests/test_today_narrative_lease_postgres.py -q -p no:cacheprovider
```

## 13. Expected evidence

- Список изменённых/удалённых файлов; для каждого удалённого теста — строка
  обоснования по §10.
- Вывод всех команд §12.
- Матрица §11 с отметкой о тесте на каждый кейс.
- contracts:check PASS + diff stat packages/contracts.

## 14. Escalation rule

Нужно менять projection/narrative/lease/snapshot internals, schemas,
миграции, TodayService → СТОП, доложить. Сомнение в triage конкретного
файла → оставить файл, доложить в отчёте.

## 15. No-commit rule

Ничего не коммить и не пушить — коммит делает ревьюер.
