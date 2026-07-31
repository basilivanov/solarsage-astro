# 38 — P4-D1 WIRE PROJECTION TZ — Today Convergence Rewrite

Controller packet по coder-loop §10.7. Архитектор: main agent. Кодер: opencode
в tmux astro2 (cwd `/tmp/solarsage-convergence-impl`).

## 1. Packet title

P4-D1 — deterministic projection `TodaySnapshot` (+ narrative row, access)
→ `TodayConvergencePayload` (wire root).

## 2. Phase / Wave

W-TODAY-CONVERGENCE-REWRITE / P4 (W5-S1 API consumers), срез D1 (без HTTP).

## 3. Modules

- Новый: `M-TODAY-CONVERGENCE-PROJECTION` (apps/api/app/services/today_convergence_projection.py)
- Тесты: `apps/api/tests/test_today_convergence_projection.py`

## 4. Goal

Один наблюдаемый результат: чистый сервисный модуль, который из уже
опубликованного `TodaySnapshot` row (+ опциональной `TodaySnapshotNarrative`
row + `ContentAccessState`) строит `TodayConvergencePayload`
(`apps/api/app/schemas/today_convergence.py`), проходящий ВСЕ root-инварианты
схемы, включая 5 canonical contract fixtures
`apps/api/tests/fixtures/contracts/today-convergence-*.json` как оракул формы.

Никаких HTTP/DB/sidecar/LLM вызовов в модуле — это pure projection слой.
К нему позже подключатся Day endpoint (P4-D2) и narrative (P6).

## 5. Контекст (что уже существует — читать, не переписывать)

- Wire root + вложенные модели: `apps/api/app/schemas/today_convergence.py`
  (`TodayConvergencePayload` :358, жёсткие root-инварианты :401-531,
  camelCase wire через `CamelModel`).
- Snapshot row: `app/db/models.py` `TodaySnapshot` (:637) — поля
  `deterministic_result_json`, `canonical_input_json`, `birth_time_mode`,
  `birth_time_range`, `target_date`, `timezone`, `published_at`,
  `formula_version`, `calculation_version`.
- Narrative row: `app/db/models.py` `TodaySnapshotNarrative` (:709) — `status`
  (`pending|ready|unavailable`), `content_json`.
- Форма snapshot JSON: `apps/api/app/services/today_convergence_snapshot.py`:
  - `deterministic_result_json` = `_result_pack` (:356): `state`, `day_tone`,
    `selected{convergences[{group_id, anchor_event_id, member_event_ids,
    evidence_event_ids, primary_sphere, secondary_sphere, polarity,
    evidence_level}], main_event{event_id, sphere, polarity, evidence_level},
    impulses[...], selected_unit_ids, selected_spheres}`, `audit{...}`.
  - `canonical_input_json.factor_units[]` = полные сериализованные
    `CanonicalUnit` (`_unit_payload` :199): содержат `canonical_event_id`,
    `event_class`, `source_key`, `semantic_key`, `driver_key`,
    `product_spheres`, `polarity`, `exact_at`, `active_from`, `active_until`
    (WindowValue сериализован как ISO date/datetime), `technique_horizon`.
- Контрактные fixtures-оракулы (5 шт):
  `apps/api/tests/fixtures/contracts/today-convergence-{full-hero-ready,
  full-quiet-not-needed,preview,locked,unavailable}.json`; их round-trip
  уже зафиксирован в `apps/api/tests/test_today_convergence_contract.py`.
- Норматив: `docs/work/2026-07-29_today-convergence-rewrite/04_W2_W3_RUNTIME_CONTRACT_TZ.md`
  §3 (строки 51-229) — envelope, матрица состояний, caps, EventTime,
  narrative claim shape. Читать целиком перед кодированием.
- Canon day parts: `grace/canon/today_convergence.v1.yml` :183-186 —
  night [0,6), morning [6,12), day [12,18), evening [18,24).

## 6. Exact write scope

Разрешено создать/изменить ТОЛЬКО:

- `apps/api/app/services/today_convergence_projection.py` (новый)
- `apps/api/tests/test_today_convergence_projection.py` (новый)

## 7. Frozen / Out of scope

- НЕ менять: `schemas/today_convergence.py`, `today_convergence_snapshot.py`,
  `today_snapshot_service.py`, `today_narrative_lease_service.py`,
  `app/db/models.py`, любые API endpoints, frontend, миграции, canon YAML.
- НЕ реализовывать: HTTP endpoints, LLM-генерацию, lease orchestration,
  `periodContext`/`lookahead` продюсеров (их нет — см. §9).
- НЕ добавлять legacy-поля (`dayStatus`, `relativeStatus`, `v2`, `focus`).

## 8. Функциональные требования

### 8.1 Публичные entrypoints (рекомендуемые сигнатуры)

```python
def project_snapshot_payload(
    snapshot: TodaySnapshot,
    narrative: TodaySnapshotNarrative | None,
    access_state: ContentAccessState,  # "full" | "preview" | ...
) -> TodayConvergencePayload

def project_empty_payload(
    *,
    target_date: date,
    timezone_name: str,
    birth_time: TodayConvergenceBirthTime,
    access_state: ContentAccessState,
    unavailable: bool,  # True → state=unavailable проекция; False → locked
) -> TodayConvergencePayload
```

Допустимо объединить в один фасад, но обе проекции (со snapshot и без) обязаны
быть покрыты. Все ошибки проекции — fail-closed typed error
(`TodayConvergenceProjectionError(ValueError)` с reason token
`today_convergence_projection:<reason>`); невалидный snapshot JSON НЕ должен
выдавать частичный payload.

### 8.2 Матрица проекции (из 04 §3.2, обязательна)

- `full` + snapshot: `state`, `dayTone` из `deterministic_result_json`;
  `snapshotId`=str(snapshot.id), `publishedAt`, `personal=True`,
  `previewTeaser=None`.
- `contentState` маппинг из narrative row: отсутствует → `pending`;
  `pending` → `pending`; `ready` → `ready` + LLM claims из `content_json`;
  `unavailable` → `unavailable`, LLM-поля null. LLM claims проецируются
  ТОЛЬКО при `ready`; каждый claim `{text, sourceEventIds}` обязан пройти
  wire-валидацию (summary ≤220 chars, sourceEventIds ⊆ selected events блока);
  любая невалидность → весь LLM-слой атомарно отбрасывается
  (`contentState=unavailable`, LLM-поля null), deterministic часть неизменна.
- `preview` + snapshot: `state`/`dayTone`/`personal` сохраняются;
  `previewTeaser.spheres` ≤3 из `selected.selected_spheres` (порядок
  deterministic: как в selected); `convergences`/`mainEvent`/`impulses`/
  `events` пусты; `periodContext`/`lookahead` null; `contentState=not_needed`.
- `locked` (без snapshot): `state=null`, все контентные поля null/пусты,
  `contentState=not_needed`, `previewTeaser=null`, `snapshotId=null`.
- `state=unavailable` (без snapshot): `snapshotId=null`, `publishedAt=null`,
  `dayTone=null`, `personal=null`, `contentState=unavailable`, все блоки пусты.
- `birthTime` заполняется во всех состояниях из snapshot
  (`birth_time_mode`+`birth_time_range` + capabilities из
  `canonical_input_json.birth_time.capabilities`) или из аргумента для
  empty-проекций.

### 8.3 Convergences / mainEvent / impulses / events

- `convergences[]`: из `selected.convergences` (0..3, порядок как в selected —
  hero первым). Wire-форма по fixture: `id=group_id`,
  `primarySphere`/`secondarySphere`, `polarity`, `evidenceLevel`,
  `eventIds` = `evidence_event_ids` (решение архитектора: публичная
  evidence-пара; fixture full-hero-ready согласуется — там ровно 2 ID).
  `summary`/`meaning`/`action` — null до narrative ready.
- `mainEvent` / `impulses[]`: из `selected.main_event` / `selected.impulses`;
  `time` строится из соответствующего factor_unit (см. 8.4). Поле `id`
  mainEvent — детерминированный производный ID (например `mev_v1_<event_id>`
  — зафиксировать выбранную схему в тесте; должен быть стабилен между вызовами).
- `events[]`: ровно union всех ID, на которые ссылаются блоки
  (`convergences[].eventIds`, `mainEvent.eventId`, `impulses[].eventId`),
  каждый — из `canonical_input_json.factor_units` по `canonical_event_id`.
  Root-инвариант `event_ledger_mismatch` обязан проходить.
  Форма события: `id`, `kind` (из `event_class`, fallback — `technique_horizon`),
  `sphere` (product sphere из selected-записи), `polarity`, `evidenceLevel`,
  `time` (см. 8.4), `sourceIds` — непустой массив стабильных источников
  (`source_key`, иначе `semantic_key`/`driver_key`).
- Ссылка на отсутствующий в factor_units ID → fail-closed error
  (не пропускать молча).

### 8.4 EventTime маппинг (04 §3.3, строки 216-229)

Источник — factor_unit поля `exact_at`/`active_from`/`active_until`
(ISO date или datetime) + `birth_time_mode` snapshot + `timezone` snapshot:

- `exact` mode: `time.mode="exact"`, `peak`/`start`/`end` — `HH:MM` в локальной
  tz snapshot'а (datetime → local), `partOfDay=null`. Если у unit нет точного
  окна — эскалация на уровне reason token, не выдумывать.
- `bucket` mode: `time.mode="partofday"`, `partOfDay` из canon day-parts
  (night [0,6), morning [6,12), day [12,18), evening [18,24)) по локальному
  часу peak (или середины окна), часовые поля null.
- `unknown` mode: `partofday` или `date` (date — когда известна только дата).
- Точные часы вне `exact` запрещены — wire-валидатор это проверяет, проекция
  не должна их эмиттить.

### 8.5 GRACE

- Полная разметка нового модуля: `AI_HEADER`, `START_MODULE_CONTRACT`
  (включая `emitted_logs: none` — чистая проекция), `START_MODULE_MAP` с
  `owned_tests`, `START_FUNCTION_CONTRACT` для публичных функций,
  `START_BLOCK` для semantic blocks (MATRIX, LEDGER, EVENT_TIME, NARRATIVE).
- Новых log events НЕ вводить.

## 9. Must-preserve invariants

- `schemas/today_convergence.py` НЕ меняется: если проекция не проходит
  root-валидатор — чинится проекция, не схема. Любая кажущаяся дыра в схеме —
  эскалация (см. §11).
- Immutability: проекция не мутирует входные row/JSON (deepcopy не требуется,
  если не мутируешь).
- Детерминизм: одинаковый вход → byte-identical wire JSON (проверить тестом
  двойного вызова).
- Quiet day без mainEvent/impulses и без periodContext — недопустимый вход по
  контракту selection; если встретится — fail-closed error + доклад
  (это дыра selection, не маскировать).

## 10. Verification

```bash
cd /tmp/solarsage-convergence-impl/apps/api
/opt/solarsage-astro/apps/api/.venv/bin/python -m pytest \
  tests/test_today_convergence_projection.py \
  tests/test_today_convergence_contract.py -q -p no:cacheprovider
/opt/solarsage-astro/apps/api/.venv/bin/python -m ruff check app/services/today_convergence_projection.py
cd /tmp/solarsage-convergence-impl && python3 scripts/grace_lint.py apps/api/app/services/today_convergence_projection.py
```

Плюс полный не-регресс:
```bash
cd /tmp/solarsage-convergence-impl/apps/api && \
  /opt/solarsage-astro/apps/api/.venv/bin/python -m pytest tests/ -q \
  -m "not integration and not benchmark" -p no:cacheprovider 2>&1 | tail -3
```

## 11. Expected evidence

- Список созданных файлов; вывод всех команд §10 (tail).
- Матрица тестов в отчёте: full-hero (snapshot+narrative ready/pending/
  unavailable/отсутствует), preview, locked, state=unavailable,
  quiet с mainEvent+impulses, bucket и unknown EventTime, невалидный narrative
  content_json → атомарный unavailable, детерминизм (double-call byte parity),
  foreign event reference → typed error.

## 12. Escalation rule

Нужно изменить что-либо из §7 (wire schema, snapshot document, models,
endpoints) или обнаружена дыра в selection/snapshot формате → СТОП, доложить
в отчёте с конкретикой, новый packet выпишет архитектор. Не поглощать в scope.

## 13. No-commit rule

Ничего не коммить и не пушить — коммит делает ревьюер. `git status` в конце
должен показывать только 2 новых файла из §6.
