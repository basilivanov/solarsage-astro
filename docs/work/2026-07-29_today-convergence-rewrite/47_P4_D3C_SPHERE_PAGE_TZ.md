# 47 — P4-D3C STATIC SPHERE PAGE TZ — Today Convergence Rewrite

Controller packet по coder-loop §10.7. Архитектор: main agent. Кодер: codex CLI
(первый), cwd `/tmp/solarsage-convergence-impl`, ветка `work/today-convergence-2`.

ВАЖНО: ты и есть coder. Skill coder-loop использовать НЕЛЬЗЯ — задачу
выполняешь сам и отчитываешься здесь ревьюеру. Параллельный кодер работает
только с frontend страницей дня — backend трогаешь только ты.

## 1. Packet title

P4-D3C — `GET /api/spheres/{key}` static sphere page: слой «В твоей карте»
(bounded natal LLM с claim binding, кэш по profile_hash) + слой «Сейчас
действует» (deterministic long-period темы с датами окончания).

## 2. Phase / Wave

W-TODAY-CONVERGENCE-REWRITE / P4 (W5-S1 API consumers), срез D3C.

## 3. Modules

- Новый: `M-API-TODAY-SPHERE-PAGE` — apps/api/app/api/today_sphere_page.py
- Новый: `M-TODAY-SPHERE-PAGE` — apps/api/app/services/today_sphere_page_service.py
- Новый: `M-TODAY-SPHERE-NATAL-NARRATIVE` — в том же service-модуле или
  отдельным — решай по размеру, но GRACE module ids явные
- Новый: `M-SCHEMAS-TODAY-SPHERE-PAGE` — apps/api/app/schemas/today_sphere_page.py
- Новый: миграция `apps/api/alembic/versions/0030_today_sphere_natal_narratives.py`
- Изменяемые: app/db/models.py (модель), app/main.py (router),
  schemas/contract_registry.py (root), core/logging_events.py (2 события),
  grace/canon/observability.xml + lib/log/events.gen.ts (sync),
  core/config.py (1 setting)

## 4. Goal

`GET /api/spheres/{key}` для full/preview пользователя возвращает:

```json
{
  "sphere": "work",
  "birthTimeMode": "exact",
  "natal": {
    "state": "ready | unavailable",
    "paragraphs": [{"text": "...", "sourceFactIds": ["natal:planet:SUN"]}] | null
  },
  "period": [
    {"id": "...", "technique": "firdar_major", "title": "Большой фирдар Юпитера",
     "activeFrom": "2024-05-01", "activeUntil": "2031-05-01"}
  ],
  "periodIdentity": "<sha256[:32]>"
}
```

locked → 403; invalid sphere → 422; incomplete profile → 422. Натальный
текст кэшируется до смены профиля; period layer deterministic и без LLM.

## 5. Норматив (прочитать перед кодированием)

- `docs/work/2026-07-29_today-convergence-rewrite/03_W7_FRONTEND_DESIGN_TZ.md`
  §7 (:186-190): два слоя; запрет слов «сегодня»/«завтра»; дома при
  bucket/unknown скрыты с честной пометкой; нет контента → честный статус.
- `docs/work/2026-07-29_today-convergence-rewrite/05_W5_W8_OPERATIONS_AND_RELEASE_TZ.md`
  §5.1 (:201): natal кэш по profile_hash; period обновляется со сменой периода.
- Существующее (использовать, не менять):
  - Canon: `load_today_convergence_canon()` → `planet_to_product`,
    `technical_to_product` (services/today_convergence_canon.py).
  - Natal facts: `NatalContextService.get_or_build_natal_context(user_id)`
    → `NatalContextData` (planets/houses/aspects/sphere_scores/
    special_points) — services/natal_context_service.py, schemas/natal.py:396.
  - Period источник: `get_solarsage_client().get_activation_layer(
    birth_..., target_date=сегодня пользователя, ...,
    techniques=["annual_profection","firdar_major","firdar_minor",
    "solar_return"])` — clients/solarsage_client.py:234 (raw dict;
    поля evidence: technique, target_key, house, active_from, active_until,
    evidence, polarity).
  - Profile hash: `NatalContextService.compute_profile_hash(profile)`
    (ТОТ ЖЕ hash, что у natal cache — переиспользовать).
  - Claim-validation прецеденты: natal_report_service.py
    `_check_hallucinated_planets` :227, llm_claim_validator.py.
  - Bounded LLM паттерн: services/today_narrative_service.py (P6):
    prompt build → один call → strict JSON validate → typed failure.
    Повторить паттерн, НЕ импортировать приватное.
  - Drilldown endpoint для конвенции ошибок: api/today_sphere_drilldown.py.
  - PG integration test pattern: tests/test_today_snapshot_postgres.py
    (TODAY_TEST_POSTGRES_URL, temp schema).
  - Registry sync pattern: observability.xml + events.gen.ts (см. коммит
    2b4accb2 — добавление 3 событий).

## 6. Exact write scope

- apps/api/app/api/today_sphere_page.py (новый)
- apps/api/app/services/today_sphere_page_service.py (новый)
- apps/api/app/schemas/today_sphere_page.py (новый)
- apps/api/app/db/models.py — модель `TodaySphereNatalNarrative`
- apps/api/alembic/versions/0030_today_sphere_natal_narratives.py (новый)
- apps/api/app/main.py — include_router
- apps/api/app/schemas/contract_registry.py — root TodaySpherePagePayload
- apps/api/app/core/config.py — `today_sphere_natal_prompt_version`
  (alias TODAY_SPHERE_NATAL_PROMPT_VERSION, default "sphere-natal-v1")
- apps/api/app/core/logging_events.py — ровно 2 события:
  `sphere.natal_generation_completed`, `sphere.natal_generation_failed`
- grace/canon/observability.xml, lib/log/events.gen.ts — sync этих 2 событий
- apps/api/tests/test_today_sphere_page_service.py (новый)
- apps/api/tests/test_today_sphere_page_api.py (новый)
- apps/api/tests/test_today_sphere_natal_postgres.py (новый, integration)
- apps/api/tests/test_contract_registry.py — EXPECTED_ROOT_NAMES +1
- packages/contracts/* — `pnpm contracts:generate`

## 7. Frozen / Out of scope

- НЕ менять: today_convergence_*.py, today_narrative_*.py,
  today_snapshot_service.py, natal_report_service.py, horizon_*,
  calendar/checkin/day API, миграции 0027-0029, frontend.
- НЕ добавлять: lease-таблицу для sphere natal (достаточно unique +
  insert-on-conflict), period persistent cache, WebSocket.

## 8. Функциональные требования

### 8.1 Access / errors

- require_session; profile incomplete/onboarding → 422.
- `AccessService.can_access_day(user.id, today_local)`: locked → 403
  `ACCESS_REQUIRED`; full/preview → полный payload (статическая страница
  не раскрывает дневные evidence).
- sphere_key вне 12 canonical → 422 `INVALID_SPHERE`.
- Все ошибки — существующий detail{"code": ...} паттерн.

### 8.2 Period layer (deterministic, no LLM)

- Один `get_activation_layer` вызов с techniques ровно
  `["annual_profection","firdar_major","firdar_minor","solar_return"]`;
  target = локальная дата пользователя (`resolve_user_local_date`).
- Фильтр по сфере: evidence относится к запрошенной сфере, если
  (target_key планета → planet_to_product содержит сферу) ИЛИ
  (house → техническая сфера по house→tech map из canon spheres →
  technical_to_product содержит сферу). Если canon не даёт house→tech map
  явно — используй техническую сферу из `grace/canon/spheres.v1.yml`;
  неизвестный target → пропуск (fail-closed, audit count).
- Items: стабильный `id` (sha от technique+target+activeFrom),
  `technique`, `title` — RU детерминированный шаблон (versioned реестр
  шаблонов в сервисе: планеты RU имена, «Большой фирдар {planet}»,
  «Малый фирдар {planet}», «Год профекции: {house} дом», «Соляр: ...»),
  `activeFrom`, `activeUntil` (ISO date; отсутствующие даты → item
  исключается, audit).
- Сортировка: activeUntil asc, затем id. Max 5 items.
- `periodIdentity` = sha256[:32] от sorted(ids+dates).
- Слова «сегодня»/«завтра» в title запрещены (тест-гейт).
- Sidecar failure/timeout → period: [] + periodIdentity от пустого набора?
  НЕТ: честный `periodUnavailable: true` (добавь поле в payload),
  natal слой не затрагивается.

### 8.3 Natal LLM layer

- Fact pack из `NatalContextData` ТОЛЬКО по сфере: планеты из
  planet_to_product[sphere], дома связанных tech-сфер (только exact mode),
  аспекты этих планет, sphere_scores[key], dominants. Fact IDs
  deterministic: `natal:planet:{NAME}`, `natal:house:{n}`,
  `natal:aspect:{A}-{B}`, `natal:score:{sphere}`.
- Bucket/unknown: дома/ASC/лоты исключены из pack (и из ответа);
  `birthTimeMode` в payload + UI пометка обеспечивается полем
  `housesAvailable: false`.
- Один bounded LLM call (тот же provider client, что P6;
  max_output_tokens=700, deadline 45s): строгий JSON
  `{paragraphs: [{text, sourceFactIds}]}` ≤4 абзацев; валидация:
  sourceFactIds ⊆ pack, непустые; banned patterns (Chiron/Selena/Lilith
  если нет в special_points; HH:MM всегда; «сегодня»/«завтра»);
  RU язык.
- Success → upsert row (user_id, profile_hash, sphere_key, prompt_version)
  unique insert-on-conflict → `natal.state=ready`.
- Failure (timeout/schema/claim/capability/provider) →
  `natal.state=unavailable`, paragraphs=null, НИКАКОГО template текста;
  row с content_json=null НЕ писать (следующий GET попробует снова).
- Повторный GET с тем же profile_hash → cache row → готовый ответ без LLM.
- Structured logs: `sphere.natal_generation_completed` (sphere,
  prompt_version, latency_ms, paragraphs count),
  `sphere.natal_generation_failed` (sphere, error_code, latency_ms) —
  через существующий log_event с guard.

### 8.4 Миграция 0030

- Таблица `today_sphere_natal_narratives`: id UUID PK, user_id FK
  (users.id, ON DELETE CASCADE), profile_hash String(64),
  sphere_key String(24), prompt_version String(64), content_json JSON NULL,
  created_at, updated_at. Unique
  `uq_sphere_natal_identity(user_id, profile_hash, sphere_key,
  prompt_version)`. Index (user_id, sphere_key).
- Additive; downgrade drop table. PG integration тест: upgrade/downgrade
  rehearsal + concurrent insert один winner (по образцу 0028/0029 тестов,
  TODAY_TEST_POSTGRES_URL).

### 8.5 GRACE / docs sync

- Полная разметка новых модулей; `grace/knowledge-graph.xml` — добавить
  новые модули и рёбра (по существующему формату).
- `grace/verification-matrix.md` — строка UC для sphere page, если
  существует подходящий срез (проверить формат, минимальная запись).

## 9. Must-preserve invariants

- Все существующие тесты зелёные; contracts:check зелёный;
  guardrails/grace lint PASS.
- Ни один путь не меняет Day/Calendar/Checkin поведение.
- LLM никогда не видит полный natal context (только sphere-scoped pack —
  assert в тесте размера/ключей prompt).

## 10. Verification

```bash
cd /tmp/solarsage-convergence-impl/apps/api
/opt/solarsage-astro/apps/api/.venv/bin/python -m pytest \
  tests/test_today_sphere_page_service.py tests/test_today_sphere_page_api.py \
  tests/test_contract_registry.py -q -p no:cacheprovider 2>&1 | tail -3
TODAY_TEST_POSTGRES_URL=<url из .env как раньше> \
  /opt/solarsage-astro/apps/api/.venv/bin/python -m pytest \
  tests/test_today_sphere_natal_postgres.py -q -p no:cacheprovider 2>&1 | tail -3
/opt/solarsage-astro/apps/api/.venv/bin/python -m pytest tests/ -q \
  -m "not integration and not benchmark" -p no:cacheprovider 2>&1 | tail -3
/opt/solarsage-astro/apps/api/.venv/bin/python -m ruff check app
cd /tmp/solarsage-convergence-impl && python3 scripts/grace_lint.py apps/api/app && \
  python3 scripts/check_logging_guardrails.py && \
  PYTHON=/opt/solarsage-astro/apps/api/.venv/bin/python pnpm contracts:check
```

## 11. Expected evidence

- Список файлов; вывод §10; пример period item и natal fact pack (без
  LLM текста); подтверждение knowledge-graph/verification-matrix sync.

## 12. Escalation rule

Нет house→tech маппинга в canon; нужны изменения frozen файлов; норматив
требует иного access-решения → СТОП, доложить.

## 13. No-commit rule

Ничего не коммить и не пушить — коммит делает ревьюер.
