# 41 — P4-D3A CALENDAR + DAY-HISTORY SNAPSHOT INDEX TZ — Today Convergence Rewrite

Controller packet по coder-loop §10.7. Архитектор: main agent. Кодер: codex CLI
(второй), cwd `/tmp/solarsage-convergence-b`, ветка `work/today-convergence-2b`.

ВАЖНО: ты и есть coder. Skill coder-loop использовать НЕЛЬЗЯ — задачу
выполняешь сам и отчитываешься здесь ревьюеру. Параллельно в другом worktree
идёт работа над Day endpoint и narrative — их файлы НЕ трогать (см. §7).

## 1. Packet title

P4-D3A — Calendar month и новый Readings day-history переводятся на published
snapshot index: wire-state `hero | ordinary | not-computed`, без cold
calculations и без legacy dayStatus.

## 2. Phase / Wave

W-TODAY-CONVERGENCE-REWRITE / P4 (W5-S1 API consumers), срез D3A.

## 3. Modules

- `M-API-CALENDAR` — apps/api/app/api/calendar.py
- `M-CALENDAR-SERVICE` — apps/api/app/services/calendar_service.py
- `M-SCHEMAS-CALENDAR` — apps/api/app/schemas/calendar.py
- Новый: `M-API-READINGS` — apps/api/app/api/readings.py (router для
  day-history) + регистрация в app/main.py
- Новый: `M-TODAY-DAY-HISTORY` — apps/api/app/services/today_day_history_service.py
- Новый: `M-SCHEMAS-TODAY-HISTORY` — apps/api/app/schemas/today_day_history.py
- Tests: apps/api/tests/test_calendar_endpoints.py (переписать), новый
  apps/api/tests/test_today_day_history_api.py
- Generated contracts: packages/contracts/* (регенерация)

## 4. Goal

1. `GET /api/calendar?month=YYYY-MM` возвращает дни с
   `dayState = hero | ordinary | not-computed`, вычисленным ТОЛЬКО из
   опубликованных `today_snapshots` rows (без sidecar/LLM/legacy scoring).
2. Новый `GET /api/readings/day-history?limit=N` возвращает
   `DayHistoryPayload`: только published rows, без запуска расчётов.

## 5. Норматив (прочитать перед кодированием)

- `docs/work/2026-07-29_today-convergence-rewrite/04_W2_W3_RUNTIME_CONTRACT_TZ.md`
  §6 (строки 331-343): calendar wire-state и DayHistoryPayload.
- `docs/work/2026-07-29_today-convergence-rewrite/05_W5_W8_OPERATIONS_AND_RELEASE_TZ.md`
  §5.1 (строки 192-205): consumer wiring invariants.
- Текущие интерфейсы:
  - `CalendarService.get_calendar(user_id, month, today)` —
    apps/api/app/services/calendar_service.py:88; legacy day_status слои
    :203/:272.
  - `CalendarDay` — apps/api/app/schemas/calendar.py:56.
  - `TodaySnapshot` model — apps/api/app/db/models.py:637
    (поля user_id, target_date, published_at, deterministic_result_json).
  - deterministic_result_json: `state` = convergence_today|quiet_day,
    `day_tone`, `selected.selected_spheres`, `selected.impulses[]`.
  - access: `AccessService(db).can_access_day(user.id, date)` — НЕ вызывать
    на каждый день месяца без нужды; для calendar access projection
    использовать существующий bulk/periodic подход, если есть, иначе одним
    запросом access window на месяц (смотри как сейчас :88+).
  - local date: `resolve_user_local_date` (apps/api/app/services/user_local_date.py).

## 6. Exact write scope

- apps/api/app/api/calendar.py
- apps/api/app/services/calendar_service.py
- apps/api/app/schemas/calendar.py
- apps/api/app/api/readings.py (новый)
- apps/api/app/services/today_day_history_service.py (новый)
- apps/api/app/schemas/today_day_history.py (новый)
- apps/api/app/main.py — только include_router нового readings router
- apps/api/app/schemas/contract_registry.py — зарегистрировать новый
  DayHistoryPayload root (calendar root уже там)
- apps/api/tests/test_calendar_endpoints.py (переписать)
- apps/api/tests/test_today_day_history_api.py (новый)
- apps/api/tests/test_calendar_service.py — если существует и фиксирует
  legacy day_status — переписать затронутые кейсы под snapshot index
- packages/contracts/* — `pnpm contracts:generate`

## 7. Frozen / Out of scope (занято параллельным кодером — НЕ трогать)

- apps/api/app/api/day.py, api/today_convergence.py, api/checkin.py,
  api/profile.py
- apps/api/app/services/today_service.py, today_convergence_*.py,
  today_snapshot_service.py, today_narrative_*.py, user_local_date.py
- apps/api/app/core/config.py, core/logging_events.py
- Миграции, frontend, canon YAML, W9-удаление legacy TodayService.
- Static sphere page и sphere drilldown — отдельный packet (не этот).

## 8. Функциональные требования

### 8.1 Calendar dayState

- Один SQL запрос: published snapshots пользователя за месяц
  (`published_at IS NOT NULL`, head supersedes-цепочки — если реализован
  helper в snapshot service, НЕ использовать: сделать локальный запрос с
  `NOT EXISTS child` условием в calendar service; параллельный кодер меняет
  snapshot service).
- `dayState` по дню: snapshot с `deterministic_result_json.state ==
  "convergence_today"` → `hero`; `"quiet_day"` → `ordinary`; отсутствует →
  `not-computed`.
- `CalendarDay`: заменить `day_status: DayStatus|None` на
  `day_state: Literal["hero","ordinary","not-computed"]` (wire
  `dayState`). `lunar`, `access`, `disabled`, `is_today` — сохранить как
  есть. Никакой заливки valence/tones.
- Month endpoint НИКОГДА не запускает расчёты отсутствующих дат: удалить
  `_compute_and_cache_day_status` вызов из hot path (сам legacy метод не
  удалять — W9; hot path его больше не вызывает).
- `not-computed` — отдельный честный state, не подменять ordinary.

### 8.2 Day-history

- `GET /api/readings/day-history?limit=N` (default 14, max 60, валидация
  1..60 → 422 вне диапазона).
- Только published head-snapshots пользователя, `target_date` desc, limit.
- `DayHistoryPayload` (camelCase wire): `items: [{date, snapshotId, state,
  dayTone, sphereKeys: string[] (≤3 из selected_spheres), impulseCount:
  int}]`. Legacy `reading.paragraphs`/`dayStatus` отсутствуют.
- Access: endpoint требует session (401 без неё); locked пользователю
  возвращает `items: []` + его access state (решение: включить в payload
  поле `access` как в calendar; история не раскрывает события — только
  state/tone/sphere keys, это допустимо для preview; locked → пусто).
- Никаких N cold calculations: один indexed SELECT.

### 8.3 Тесты

- test_calendar_endpoints.py переписать: 401/422 грани сохранить; dayState
  матрица (hero/ordinary/not-computed смесь в одном месяце); assert: ноль
  вызовов sidecar/scoring (mock spy); lunar/access сохранены.
- test_today_day_history_api.py: published-only, desc order, limit
  cap/422, locked → пусто, поля соответствуют wire, отсутствие
  legacy-полей.
- Оба suite используют in-memory/async DB фикстуры проекта (смотри как
  устроен test_calendar_endpoints.py сейчас).

### 8.4 GRACE / logging

- Новые модули — полная разметка; изменённые — обновить contract/map
  (emitted_logs: использовать существующее `calendar.viewed`; для history —
  если подходящего события нет, НЕ добавлять новое в этом packet —
  зафиксировать `emitted_logs: none` и отметить в отчёте).
- `grace/frontend.paths` и knowledge-graph не трогать (нет новых frontend
  paths/модулей вне apps/api).

## 9. Must-preserve invariants

- Существующие зелёные тесты вне §6 не ломаются.
- `pnpm contracts:check` зелёный после регенерации.
- PG integration не затрагивается.
- Никаких вызовов sidecar/LLM/TodayService из calendar/history hot path
  (assert в тестах).

## 10. Verification

```bash
cd /tmp/solarsage-convergence-b/apps/api
/opt/solarsage-astro/apps/api/.venv/bin/python -m pytest \
  tests/test_calendar_endpoints.py tests/test_today_day_history_api.py \
  tests/test_calendar_service.py -q -p no:cacheprovider 2>&1 | tail -3
/opt/solarsage-astro/apps/api/.venv/bin/python -m pytest tests/ -q \
  -m "not integration and not benchmark" -p no:cacheprovider 2>&1 | tail -3
/opt/solarsage-astro/apps/api/.venv/bin/python -m ruff check app
cd /tmp/solarsage-convergence-b && python3 scripts/grace_lint.py apps/api/app && \
  python3 scripts/check_logging_guardrails.py && pnpm contracts:check
```

## 11. Expected evidence

- Список изменённых/созданных файлов, вывод команд §10.
- Описание wire-формы DayHistoryPayload и CalendarDay diff.
- Подтверждение: zero sidecar/LLM calls в month/history (какой тест
  доказывает).

## 12. Escalation rule

Нужно менять файлы из §7 или потребовался helper из snapshot service →
СТОП, доложить (локальный SQL в своём сервисе допустим). Сомнение — в отчёт.

## 13. No-commit rule

Ничего не коммить и не пушить — коммит делает ревьюер.
