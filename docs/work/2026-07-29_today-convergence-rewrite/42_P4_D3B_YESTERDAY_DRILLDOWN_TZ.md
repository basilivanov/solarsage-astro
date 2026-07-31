# 42 — P4-D3B YESTERDAY RECAP + SPHERE DRILLDOWN TZ — Today Convergence Rewrite

Controller packet по coder-loop §10.7. Архитектор: main agent. Кодер: codex CLI
(второй), cwd `/tmp/solarsage-convergence-b`, ветка `work/today-convergence-2b`.

ВАЖНО: ты и есть coder. Skill coder-loop использовать НЕЛЬЗЯ — задачу
выполняешь сам и отчитываешься здесь ревьюеру. Параллельно в другом worktree
идёт работа над Day endpoint — его файлы НЕ трогать (см. §7).

## 1. Packet title

P4-D3B — Yesterday/check-in forecast recap по snapshot lineage + deterministic
sphere drilldown endpoint `GET /api/day/snapshots/{id}/spheres/{key}`.

## 2. Phase / Wave

W-TODAY-CONVERGENCE-REWRITE / P4 (W5-S1 API consumers), срез D3B.

## 3. Modules

- `M-API-CHECKIN` — apps/api/app/api/checkin.py (расширение yesterday)
- `M-CHECKIN-SERVICE` — apps/api/app/services/checkin_service.py (recap projection)
- `M-CONTRACTS-CHECKIN` — apps/api/app/schemas/checkin.py (wire добавки)
- Новый: `M-API-TODAY-SPHERE-DRILLDOWN` — apps/api/app/api/today_sphere_drilldown.py
- Новый: `M-TODAY-SPHERE-DRILLDOWN` — apps/api/app/services/today_sphere_drilldown_service.py
- Tests: переписанные/новые (§6)
- Generated contracts: packages/contracts/*

## 4. Goal

1. `GET /api/checkin/yesterday` возвращает новую generated форму:
   `targetDate, hadCheckin, checkin, forecastAvailable, forecastRecap`
   (04 §6, строки 345-357). Pre-submit recap скрыт; post-submit recap только
   при валидной snapshot/impression lineage. Streak и `(user_id, target_date)`
   uniqueness не меняются.
2. `GET /api/day/snapshots/{snapshot_id}/spheres/{sphere_key}` — deterministic
   evidence chain сферы из published snapshot. Только owner + full access;
   preview не получает evidence; cross-user → 404.

## 5. Норматив (прочитать перед кодированием)

- `docs/work/2026-07-29_today-convergence-rewrite/04_W2_W3_RUNTIME_CONTRACT_TZ.md`
  §6 (HTTP-поверхность: строки 305-357; YesterdayCheckinResponse :345-357;
  drilldown :315).
- `docs/work/2026-07-29_today-convergence-rewrite/05_W5_W8_OPERATIONS_AND_RELEASE_TZ.md`
  §5.1 (:192-205): Yesterday recap и Sphere drilldown invariants.
- `docs/work/2026-07-29_today-convergence-rewrite/03_W7_FRONTEND_DESIGN_TZ.md`
  §7 (drilldown содержимое, :186-190) и §8.2 (yesterday поведение, :206-231).
- Существующее:
  - `checkin_service._load_snapshot_lineage` (P3-E): выбирает показанный
    snapshot и пишет `forecast_snapshot_id/prediction_seen_at/
    prediction_seen_surface` при первом submit. Читать перед изменениями.
  - `TodaySnapshotService.load_owned(user_id, snapshot_id)` — owner lookup.
  - Wire event модели: `apps/api/app/schemas/today_convergence.py`
    (`TodayConvergenceEvent`, `TodayConvergenceEventTime`, ...).
  - Snapshot JSON формы: deterministic_result_json + canonical_input_json
    (см. `today_convergence_snapshot.py` `_result_pack`/`_factor_pack`).
  - Projection helpers для EventTime/ledger:
    `apps/api/app/services/today_convergence_projection.py` (можно
    импортировать приватное нельзя — если нужен общий helper, выделить
    публичный в ЭТОМ ЖЕ файле аккуратно, не меняя поведения).

## 6. Exact write scope

- apps/api/app/api/checkin.py
- apps/api/app/services/checkin_service.py
- apps/api/app/schemas/checkin.py
- apps/api/app/api/today_sphere_drilldown.py (новый)
- apps/api/app/services/today_sphere_drilldown_service.py (новый)
- apps/api/app/schemas/today_sphere_drilldown.py (новый)
- apps/api/app/main.py — только include_router
- apps/api/app/schemas/contract_registry.py — регистрация нового root
- apps/api/app/services/today_convergence_projection.py — ТОЛЬКО если нужен
  публичный helper (превратить приватный в публичный без смены поведения)
- apps/api/tests/test_checkin_endpoints.py — расширить/переписать yesterday кейсы
- apps/api/tests/test_today_sphere_drilldown_api.py (новый)
- apps/api/tests/test_contract_registry.py — EXPECTED_ROOT_NAMES + новый root
- packages/contracts/* — `pnpm contracts:generate`

## 7. Frozen / Out of scope (занято параллельным кодером — НЕ трогать)

- apps/api/app/api/day.py, api/calendar.py, api/readings.py, api/profile.py,
  api/today_convergence.py
- apps/api/app/services/today_service.py, today_snapshot_service.py,
  today_narrative_*.py, calendar_service.py, today_day_history_service.py
- apps/api/app/core/config.py, core/logging_events.py
- Миграции, frontend, canon YAML.
- Static sphere page (`GET /api/spheres/{key}`) — следующий packet, не этот.

## 8. Функциональные требования

### 8.1 Yesterday recap

`YesterdayCheckinResponse` новая форма (camelCase wire):

```text
targetDate: date
hadCheckin: bool
checkin: CheckinResponse | null
forecastAvailable: bool
forecastRecap: null | { snapshotId: string, state, dayTone, sphereKeys: string[] (≤3) }
```

- `targetDate` — локальное вчера через существующий `service.local_yesterday`.
- `forecastAvailable=true` ⟺ за targetDate есть published snapshot с
  impression (day или lookahead) у этого пользователя (проверка по
  first_day_seen_at/first_lookahead_seen_at — без раскрытия контента).
- До первого submit: `forecastRecap=null` ВСЕГДА (даже при forecastAvailable).
- После submit: recap строится из `EveningCheckin.forecast_snapshot_id`
  (lineage, написанная P3-E); если snapshot не найден/чужой/не опубликован —
  recap=null. `sphereKeys` — из deterministic_result_json
  selected.selected_spheres (≤3). Никакого legacy dayStatus.
- Редактирование check-in НЕ перепривязывает lineage (уже обеспечено P3-E —
  не сломать).
- Additive wire change (новые поля) — compat gate обязан остаться additive;
  если выходит breaking по YesterdayCheckinResponse — СТОП, эскалация.

### 8.2 Sphere drilldown

`GET /api/day/snapshots/{snapshot_id}/spheres/{sphere_key}`:

- auth session обязателен; snapshot = `load_owned(user.id, snapshot_id)`;
  чужой/отсутствующий → uniform 404.
- access: `AccessService.can_access_day(user.id, snapshot.target_date)`;
  не-full (preview/locked) → 403 `ACCESS_REQUIRED` без evidence.
- `sphere_key` вне canonical 12 сфер → 422.
- Сфера отсутствует в selected snapshot'а → 404 `SPHERE_NOT_IN_SNAPSHOT`.
- Ответ `TodaySphereDrilldownPayload` (новый root, camelCase):
  - `snapshotId`, `sphere`, `state`, `dayTone`, `birthTimeMode`;
  - `events`: все selected events этой сферы (из convergences evidence,
    mainEvent, impulses), каждый — wire-форма `TodayConvergenceEvent`
    (id, kind, sphere, polarity, evidenceLevel, time, sourceIds);
  - `convergence`: если сфера — primary/secondary в выбранной группе:
    `{id, primarySphere, secondarySphere, polarity, evidenceLevel, eventIds}`,
    иначе null;
  - порядок events deterministic (как в payload-проекции);
  - LLM-полей НЕТ вовсе (drilldown полностью deterministic).
- Построение — из deterministic_result_json + canonical_input_json тем же
  маппингом, что и payload projection (переиспользовать публичный helper,
  если выделен; не дублировать логику копипастой).
- Лог: существующее событие не подходит → в этом packet логи не добавлять,
  `emitted_logs: none` (запись в отчёт).

### 8.3 Тесты (минимум)

- yesterday: pre-submit forecastAvailable=true + recap=null; post-submit
  recap со snapshotId/state/dayTone/sphereKeys; submit без показанного
  snapshot → forecastAvailable=false + recap=null; edit не перепривязывает;
  streak untouched.
- drilldown: owner full happy (events + convergence форма, порядок);
  cross-user 404; preview 403; locked 403; invalid sphere 422; сфера вне
  snapshot 404; deterministic — без LLM полей; события совпадают с payload
  projection для того же snapshot (consistency check).
- registry тест обновлён (+1 root).

## 9. Must-preserve invariants

- Существующие зелёные тесты вне §6 не ломаются (checkin create/update
  контракт не меняется — только yesterday response).
- `PYTHON=/opt/solarsage-astro/apps/api/.venv/bin/python pnpm contracts:check`
  зелёный.
- Ни один путь не вызывает sidecar/LLM.

## 10. Verification

```bash
cd /tmp/solarsage-convergence-b/apps/api
/opt/solarsage-astro/apps/api/.venv/bin/python -m pytest \
  tests/test_checkin_endpoints.py tests/test_today_sphere_drilldown_api.py \
  tests/test_contract_registry.py -q -p no:cacheprovider 2>&1 | tail -3
/opt/solarsage-astro/apps/api/.venv/bin/python -m pytest tests/ -q \
  -m "not integration and not benchmark" -p no:cacheprovider 2>&1 | tail -3
/opt/solarsage-astro/apps/api/.venv/bin/python -m ruff check app
cd /tmp/solarsage-convergence-b && python3 scripts/grace_lint.py apps/api/app && \
  python3 scripts/check_logging_guardrails.py && \
  PYTHON=/opt/solarsage-astro/apps/api/.venv/bin/python pnpm contracts:check
```

## 11. Expected evidence

- Список файлов, вывод команд §10, wire-форма drilldown payload (пример JSON),
  отметка по каждому тест-кейсу §8.3.

## 12. Escalation rule

Нужно менять файлы §7, миграции, или additive невозможен для
YesterdayCheckinResponse → СТОП, доложить. Сомнения — в отчёт.

## 13. No-commit rule

Ничего не коммить и не пушить — коммит делает ревьюер.
