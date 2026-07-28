# 01 TZ E1 — Focus Event Drilldown API (backend)

1. **Packet title**: E1-FOCUS-EVENT-DRILLDOWN-API
2. **Phase / Wave**: W5-FOCUS-EVENT-DRILLDOWN, срез E1 (backend)
3. **Modules**: M-API-DAY (endpoint), новый M-API-FOCUS-EVENT-DRILLDOWN (builder), M-SCHEMAS-TODAY-FOCUS (схема)
4. **Goal**: работающий `GET /api/day/{date_str}/focus-event/{event_id}`, который по кешированному payload дня возвращает детерминированный дрилдаун события (см. master `00_TZ.md`). Ответ мгновенный, без LLM и без пересчёта астрологии.

## 5. Exact write scope (разрешённые файлы)

- `apps/api/app/services/focus_event_drilldown_builder.py` — НОВЫЙ чистый builder
- `apps/api/app/schemas/today_focus.py` — добавить схемы дрилдауна
- `apps/api/app/api/day.py` — добавить роут
- `apps/api/tests/test_focus_event_drilldown.py` — НОВЫЙ тест builder'а + endpoint'а
- `packages/contracts/openapi.json`, `packages/contracts/_generated.ts`, `packages/contracts/_generated.zod.ts` — регенерация (`npm run contracts:generate`)
- `grace/knowledge-graph.xml` — добавить модуль M-API-FOCUS-EVENT-DRILLDOWN (node + edge к M-API-DAY)

## 6. Frozen / Out of scope

- НЕ менять `today_service.py`, `today_focus_builder.py`, `day_factor_ledger.py`, `focus_title_builder.py`.
- НЕ менять существующие схемы/поля `TodayFocus`/`TodayConvergence`/`TodayFocusEvent`.
- НЕ трогать фронтенд (components/, lib/, e2e/) — это срез E2.
- НЕ добавлять LLM-вызовы, НЕ пересчитывать факторы/активации.
- `packages/contracts/index.ts` (barrel) — НЕ трогать, это срез E2.

## 7. Must-preserve invariants

- `cd apps/api && source .venv/bin/activate && python -m pytest tests/ -q -k "not postgres and not election_quota_persists"` — зелёный.
- `ruff check app/` и `mypy app/services/` — чисто.
- `python3 scripts/grace_lint.py app` (из apps/api) — PASS.
- GET /api/day/{date} — контракт без изменений.

## Дизайн (обязателен к исполнению)

### Endpoint (`apps/api/app/api/day.py`)

`GET /{date_str}/focus-event/{event_id}` рядом с существующим `/{date_str}`.
event_id содержит двоеточия (`ev:act:t2n__MOON__SQUARE__PLUTO`) — это валидный path segment, экранирование на фронте через encodeURIComponent.

Логика:
1. Та же auth-сессия, что у day endpoint'а (смотри, как устроен `/{date_str}`).
2. Прочитать кеш payload: таблица `today_payloads_cache` (модель
   `TodayPayloadCache` в `app/db/models.py`), ключ user_id + target_date
   (точные колонки/сериализацию смотри в `today_service.py` — там пишется кеш).
3. Cache miss → 404 `{"detail": "day_payload_not_cached"}`.
4. В JSON payload: `focus.events[]` — найти по `id == event_id`; нет → 404
   `{"detail": "event_not_found"}`.
5. `v2.activationEvidence[]` — найти записи по `event.sourceActivationIds`
   (первая = primary). Может отсутствовать — builder обязан деградировать gracefully.
6. Вернуть `FocusEventDrilldown` (camelCase через CamelModel).

### Схемы (`apps/api/app/schemas/today_focus.py`)

```python
class FocusEventPlanetSide(CamelModel):
    planet_key: str          # "MOON" (или ключ жребия "NECESSITY")
    label: str               # "Луна" / "Жребий"
    frame_label: str         # "транзитная" / "твой натальный" / "твой жребий"
    function_text: str       # "эмоции и привычки"

class FocusEventNumber(CamelModel):
    label: str               # "Орб"
    value: str               # "0°19′"

class FocusEventDrilldown(CamelModel):
    event_id: str
    human_title: str
    technical_title: str | None
    kind: str                # exact/starts/peak/building/separating
    kind_label: str          # "точный пик" | "начинается" | "нарастает" | "ослабевает"
    occurs_at: datetime | None
    local_time: str | None   # "13:31" в tz пользователя
    timezone: str
    meaning: str | None      # LLM-текст из payload как есть
    technique_label: str     # "Транзит к твоей натальной карте"
    source: FocusEventPlanetSide | None
    target: FocusEventPlanetSide | None
    aspect_label: str | None   # "Квадратура"
    aspect_symbol: str | None  # "□"
    aspect_tone: str | None    # polarity: supportive/tense/mixed/neutral
    aspect_mechanics: str | None
    numbers: list[FocusEventNumber]
    source_activation_ids: list[str]
```

### Builder (`apps/api/app/services/focus_event_drilldown_builder.py`)

Чистая функция `build_focus_event_drilldown(event: dict, evidence: list[dict]) -> FocusEventDrilldown`.
GRACE-разметка обязательна (AI_HEADER/MODULE_CONTRACT/MODULE_MAP/FUNCTION_CONTRACT).

Правила:
- Функции планет — `PLANET_FUNCTIONS` из `app.services.sphere_why_builder`
  (ключи TitleCase: "Moon", "Pluto"; evidence.sourcePlanet уже TitleCase,
  targetPlanet — UPPER → `.title()` при маппинге).
- Не-планетная цель (targetType "lot", напр. NECESSITY): label "Жребий",
  frame_label "твой жребий", function_text "особая расчётная точка карты".
- frame_label: sourceFrame=="transit" → "транзитная"; targetFrame=="natal" → "твой натальный".
- kind_label: exact/peak → "точный пик", starts → "начинается",
  building → "нарастает", separating → "ослабевает".
- aspect_label/symbol: conjunction Соединение ☌, opposition Оппозиция ☍,
  trine Тригон △, square Квадрат □, sextile Секстиль ⚹, quincunx Квиконс ⚻,
  semi_square Полуквадрат ∠, sesqui_quadrate/sesquisquare Полутораквадрат ⚼,
  semi_sextile Полусекстиль ⚺. Аспект берётся из evidence `aspect` (fallback `kind`).
- aspect_mechanics — `ASPECT_MEANINGS[aspect]["explanation"]` из
  `app.services.synastry_service` (проверь структуру словаря); ключа нет → None.
- technique_label: transit_to_natal → "Транзит к твоей натальной карте",
  transit_to_lot → "Транзит к жребию", lunar_return → "Лунар (карта месяца)",
  solar_return → "Соляр (карта года)", прочее → "Астрологический цикл".
- numbers (только строки с данными, порядок фиксирован):
  1. "Орб" — из evidence.orb в градусах/минутах: `0°19′` (форматтер как
     `_format_orb_label` в synastry_service — скопировать 5 строк в builder).
  2. "Точное время" — exactAt → локальное "HH:MM" + " · Europe/Moscow".
  3. "Фаза" — phase: exact → "точный", applying → "сходящийся",
     separating → "расходящийся", period/background → "долгий период".
  4. "Окно действия" — activeFrom — activeUntil в локальной tz: "27.07 04:12 — 29.07 22:40".
  5. "Сила влияния" — strength 0..1 → "72%".
  6. "Полюс" — polarity: supportive → "поддерживающий", tense → "напряжённый",
     mixed → "смешанный", neutral → "нейтральный".
- Все datetime из evidence (ISO-строки с Z) парсить и конвертировать в event.timezone.

### Тесты (`apps/api/tests/test_focus_event_drilldown.py`)

- Builder: (а) аспектное событие Луна→Плутон с полным evidence — все поля,
  формат орба/времени/окна, kind_label; (б) событие к жребию (t2l, targetType lot)
  — «Жребий» без машинных ключей; (в) пустой evidence → source/target/numbers None/[] graceful.
- Endpoint (по образцу `test_today_focus_contract.py`: async_client, make_initdata,
  db_session): создать пользователя+доступ, вставить строку в today_payloads_cache
  напрямую через db_session (минимальный payload: focus.events[1 событие] +
  v2.activationEvidence[1 запись]) → GET 200, camelCase ключи, значения сходятся;
  GET с чужим event_id → 404.

## 8. Verification (одна команда)

```bash
cd apps/api && source .venv/bin/activate && python -m pytest tests/test_focus_event_drilldown.py -q && ruff check app/ && python3 ../../scripts/grace_lint.py app
```

## 9. Expected evidence

- Список изменённых/новых файлов, вывод verification-команды, пример JSON ответа
  (из теста) в отчёте.

## 10. Escalation

Нужно менять today_service/кеш-формат/фронт — стоп, доклад ревьюеру, новый packet.

## 11. No-commit

Ничего не коммитить и не пушить — коммит делает ревьюер.
