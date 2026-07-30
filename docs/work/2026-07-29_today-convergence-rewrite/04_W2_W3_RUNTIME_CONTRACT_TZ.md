# W2–W3 RUNTIME CONTRACT TZ — Today Convergence Rewrite

Дата: 2026-07-30
Статус: **implementation-ready** для W2/W3; не меняет frozen W1-формулу.
Нормативные источники: `00_MASTER_TZ.md` v1.12, `grace/canon/today_convergence.v1.yml`, `02_TONE_POLICY_AMENDMENT.md`.
Потребители: W5 API/pregen, W6 LLM, W7 frontend, W8 cutover.

Этот документ фиксирует runtime-поверхность, которой не хватает в W1: wire
контракт, persistence, профиль времени рождения, локальную дату и правила
связи snapshot с check-in. Он не создаёт compatibility-layer для старых
Today/V1/V2 shapes.

## 1. Граница и порядок источников

1. Расчётная истина и eligibility берутся только из `00_MASTER_TZ.md` и
   `grace/canon/today_convergence.v1.yml`.
2. Этот документ уточняет способ доставки и хранения этой истины.
3. `03_W7_FRONTEND_DESIGN_TZ.md` уточняет presentation и DOM-контракт.
4. При расхождении с legacy-кодом действует новый envelope; старый shape не
   адаптируется и не выдаётся вторым полем.

В production до W8 остаётся старый immutable release. Новый контракт сначала
тестируется в отдельном dev/staging release, затем API и frontend переключаются
атомарно.

## 2. Единственный источник wire-схемы

Wire Source of Truth — новые Pydantic-модели в
`apps/api/app/schemas/` (по правилу `packages/contracts/README.md`). Pipeline:

```text
Pydantic → scripts/contracts/export_openapi.py
         → packages/contracts/openapi.json
         → _generated.ts + _generated.zod.ts
```

Запрещено вручную объявлять wire-Zod во frontend или редактировать generated
артефакты. В рамках W2/W3 должны появиться:

- public roots `TodayConvergencePayload`, `TodayCalendarPayload`,
  `TodaySphereDrilldownPayload`, `SpherePagePayload`, `DayHistoryPayload`,
  `TodayRetryAccepted` и `TodayImpressionRequest`, плюс вложенные модели;
- регистрация моделей в `contract_registry.py`;
- минимум по одному JSON-fixture для каждого состояния из §3.2;
- `pnpm contracts:generate` и `pnpm contracts:check` в gate.

`schemaVersion=1` — версия нового envelope. `formulaVersion` и
`calculationVersion` — разные поля: первое относится к продуктовой формуле,
второе — к расчётному движку/кэшу.

## 3. Root envelope

### 3.1 Поля

| Поле | Тип | Условие | Владелец |
|---|---|---|---|
| `schemaVersion` | `1` | всегда | API contract |
| `snapshotId` | opaque string или `null` | null для `locked` и `state=unavailable` | persistence |
| `targetDate` | ISO date | локальная дата пользователя | date resolver |
| `timezone` | IANA string | timezone, использованный для дня | date resolver |
| `publishedAt` | ISO datetime или `null` | заполняется при атомарной публикации, включая pregen | snapshot |
| `access` | existing `ContentAccessState` | всегда | access service |
| `birthTime` | object | всегда после профиля | profile contract |
| `state` | enum или `null` | `null` только при `access=locked` | deterministic pipeline |
| `dayTone` | enum или `null` | null при `state=unavailable` или `access=locked` | tone policy |
| `personal` | boolean или `null` | false для общего фона; null для locked/unavailable | presentation policy |
| `previewTeaser` | object или `null` | только server-side projection для preview | access projection |
| `convergences` | array, 0..3 | selected canonical groups; 0 для quiet | selector |
| `mainEvent` | object или `null` | только одиночное исключительное событие | selector |
| `impulses` | array, 0..3 | quiet-day presentation | selector |
| `periodContext` | object или `null` | обязателен для quiet без impulse/mainEvent | context layer |
| `lookahead` | object или `null` | только quiet + published snapshot следующего дня | snapshot projection |
| `events` | array | все IDs, на которые ссылаются блоки | evidence ledger |
| `contentState` | enum | зависит от state/access | LLM orchestration |
| `formulaVersion` | string | `today-convergence-2` | canon |
| `calculationVersion` | string | `ss-calc-1.3.0` или новее | py-contracts |

`dayStatus`, `relativeStatus`, `v2`, `focus` и старые valence-поля в новый
envelope не входят.

`birthTime` имеет одну wire-форму во всех состояниях:

```json
{
  "mode": "exact",
  "bucket": null,
  "rangeStart": "12:34",
  "rangeEnd": "12:34",
  "capabilities": {
    "houses": true,
    "angles": true,
    "lots": true,
    "exactTiming": true
  }
}
```

Для bucket/unknown `rangeStart` включён, `rangeEnd` исключён; unknown передаёт
`rangeStart="00:00"`, `rangeEnd="24:00"`. Значение `24:00` разрешено только
как исключённая правая граница суток. Для exact оба поля равны фактическому
времени рождения и обозначают точку, а не интервал. Это диапазон входной
неопределённости, не обещание точного времени события. Canon-поле
`exact_timing` маппится в wire-ключ `exactTiming`; `angles` — отдельная
capability и не подразумевается полем `houses`.

### 3.2 Состояния и доступ

Расчётное состояние (`state`) и доступ (`access.state`) ортогональны:

| access | state | snapshot | что отдаём |
|---|---|---|---|
| `full` | `convergence_today` / `quiet_day` | published | полный deterministic payload + LLM-слой |
| `preview` | `convergence_today` / `quiet_day` | published | server-side preview-проекцию из правила ниже |
| `locked` | `null` | отсутствует | paywall и метаданные режима; никаких персональных событий |
| `full/preview` | `unavailable` | отсутствует | честный статус и retry, без частичных выдуманных фактов |

`state=unavailable` — это технически не полученный персональный расчёт:
`snapshotId`, `publishedAt`, `dayTone`, `personal`, `previewTeaser`,
`periodContext` и `lookahead` равны `null`; `convergences`, `impulses` и `events`
пусты, `mainEvent=null`. Текст UI: «Не удалось рассчитать день. Обновить».

`contentState=unavailable` при `state=convergence_today|quiet_day` означает
только сбой LLM: deterministic snapshot, tone, events и spheres сохраняются,
LLM-поля равны `null`. Это не `state=unavailable`.

Для `preview` API оставляет `state`, `dayTone`, `personal` и
`previewTeaser={"spheres": [...]}` с максимум тремя названиями сфер.
`convergences`, `mainEvent`, `impulses`, `events` пусты; `periodContext`,
`lookahead` и LLM-owned поля null; `contentState=not_needed`. Paywall следует
сразу за этим детерминированным тизером. Проекция выполняется server-side:
frontend не получает скрытые evidence и не обрезает full payload самостоятельно.
Для `full`, `locked` и `state=unavailable` поле `previewTeaser=null`.

Полная матрица верхнего уровня:

| access | state | contentState | обязательная проекция |
|---|---|---|---|
| `full` | `convergence_today` | `ready / pending / unavailable` | deterministic + разрешённая LLM-зона |
| `full` | `quiet_day` | `ready / pending / unavailable / not_needed` | 0–3 импульса или mainEvent + context |
| `preview` | `convergence_today / quiet_day` | `not_needed` | только previewTeaser |
| `locked` | `null` | `not_needed` | paywall metadata, без snapshot |
| `full / preview` | `unavailable` | `unavailable` | retry status, без snapshot/тизера |

### 3.3 Вложенные caps и ссылки

- `convergences`: 0..3 canonical groups; первый по сортировке — hero, остальные
  дают максимум две вторичные строки; «сошлось» показывается только здесь;
- `mainEvent`: 0..1 и взаимоисключён с `convergences`;
- `impulses`: 0..3, сортировка significance ↓ → local time ↑ → ID ↑;
- `quiet_day` обязан иметь хотя бы один из `mainEvent`, `impulses` или
  `periodContext`; при отсутствии активного периода используется
  `PeriodContext.kind=no_strong_accent`, а не LLM-заглушка;
- одна физическая группа получает primary и максимум одну secondary sphere;
- физическая группа присутствует в массиве один раз; объединение presentation-
  сфер всех выбранных групп ограничено тремя;
- `events[].id` уникальны в payload; все ссылки на event/convergence проверяются
  валидатором;
- `evidenceLevel`: только `high|medium` публично;
- `polarity`: `supportive|tense|mixed`; `steady` существует только у `dayTone`;
- LLM-owned `summary`, `meaning`, `action` могут быть `null`; их отсутствие не
  создаёт шаблонного fallback;
- `summary.text` валидируется server-side с `max_length=220`; frontend не
  обрезает переполненный текст, а весь narrative отклоняется атомарно.

Каждое ненулевое LLM-поле имеет форму
`{"text": "…", "sourceEventIds": ["evt_v1_…"]}`. Пустой список source IDs,
ссылка не на selected event или частично валидный narrative запрещены: весь
LLM-блок отклоняется атомарно.

Минимальная форма события:

```json
{
  "id": "evt_v1_…",
  "kind": "aspect",
  "sphere": "work",
  "polarity": "tense",
  "evidenceLevel": "high",
  "time": {"mode": "exact", "peak": "15:40", "start": "13:00",
           "end": "18:00", "partOfDay": null},
  "sourceIds": ["…"]
}
```

Минимальная форма convergence-группы:

```json
{
  "id": "cvg_v1_…",
  "primarySphere": "work",
  "secondarySphere": "documents",
  "polarity": "tense",
  "evidenceLevel": "high",
  "eventIds": ["evt_v1_…", "evt_v1_…"],
  "summary": null,
  "meaning": null,
  "action": null
}
```

`lookahead` содержит только `targetDate`, `sphere` и `snapshotId` следующего
локального дня. Он присутствует только в `quiet_day`, если тот snapshot уже
published; API не запускает расчёт следующего дня ради заполнения поля.

Остальные вложенные модели фиксируются до генерации frontend-типов:

| Модель | Детерминированные поля | LLM-owned nullable поля |
|---|---|---|
| `BirthTime` | `mode`, `bucket`, `rangeStart`, `rangeEnd`, `capabilities` | — |
| `PreviewTeaser` | `spheres` (0..3 canonical keys) | — |
| `Convergence` | `id`, `primarySphere`, `secondarySphere`, `polarity`, `evidenceLevel`, `eventIds` | `summary`, `meaning`, `action` |
| `MainEvent` | `id`, `eventId`, `sphere`, `polarity`, `evidenceLevel`, `time` | `summary`, `meaning`, `action` |
| `Impulse` | `eventId`, `sphere`, `polarity`, `evidenceLevel`, `time` | `summary`, `meaning`, `action` |
| `PeriodContext` | `id`, `kind=active_period\|no_strong_accent`, `sphere`, `title`, `activeFrom`, `activeUntil`, `eventIds` | — |
| `Lookahead` | `targetDate`, `sphere`, `snapshotId` | — |
| `EventTime` | `mode`, `peak`, `start`, `end`, `partOfDay` | — |

`EventTime.mode=exact` разрешает `HH:MM` в `peak/start/end` и требует
`partOfDay=null`; `partofday` требует `partOfDay=night|morning|day|evening` и
null в часовых полях; `date` требует null во всех полях точного времени.
Frontend форматирует эти структуры, API не передаёт локализованную строку как
единственный источник времени.

Для `PeriodContext.kind=no_strong_accent` sphere/dates равны null, eventIds
пусты, а title берётся из versioned реестра констант. Это проверенный результат
отсутствия публичного акцента, не имитация персональной LLM-интерпретации.

Для `bucket` `time.mode=partofday`, для `unknown` — `partofday|date`; точные
часы запрещены валидатором вне `exact`.

## 4. Профиль и время рождения

### 4.1 Поля

В `UserProfile` и `Profile` wire-модели additive добавляются:

```text
birth_time_mode: exact | bucket | unknown
birth_time_bucket: night | morning | day | evening | null
birth_time_prompt_dismissed: boolean
```

Это Python/DB-имена; generated JSON использует `birthTimeMode` и
`birthTimeBucket`, `birthTimePromptDismissed` по действующему camelCase
contract.

Границы по локальному времени места рождения используют единственную
полуоткрытую форму `[start, end)`:

```text
night   [00:00, 06:00)
morning [06:00, 12:00)
day     [12:00, 18:00)
evening [18:00, 24:00)
```

Часовые пары в frozen canon трактуются с той же семантикой.

Миграция существующих данных: `birth_time != null → exact`, `birth_time == null
→ unknown`. `bucket` не восстанавливается догадкой из старых данных. Для строк,
мигрированных из `birth_time == null`, `birth_time_prompt_dismissed=true`, чтобы
релиз не показал массово новую плашку; для новых профилей default `false`.

Capabilities вычисляются детерминированно:

| mode | houses/angles/lots | exact timing |
|---|---|---|
| exact | available | available |
| bucket | unavailable | unavailable |
| unknown | unavailable | unavailable |

Никаких `birth_time or "12:00"`, `find_house(...) or 1` или скрытой условной
полуденной карты.

### 4.2 Переход режима

`unknown/bucket → exact` меняет `profile_hash`, input/cache identity и создаёт
новые будущие snapshots. Уже published snapshots не переписываются. В UI один
раз показывается спокойное подтверждение из W7 §5.8.

`PUT /api/profile` валидирует комбинацию атомарно: exact требует `birthTime` и
null bucket; bucket требует выбранный bucket и не хранит выдуманный `birthTime`;
unknown требует null в обоих полях времени. Дата/место/birth timezone остаются
обязательными для завершённого onboarding во всех трёх режимах. Обновление
профиля инвалидирует только непublished cache/будущие candidates, но не удаляет
исторические published snapshots. Dismiss плашки выполняет только переход
`birthTimePromptDismissed: false → true`; это UX-флаг и он не входит в
profile/input hash расчёта.

## 5. Локальная дата

Ввести один backend helper `resolve_user_local_date(user, now)` с приоритетом:

```text
profile.current_tz → profile.birth_tz → UTC
```

Его используют `/api/day/{date}`, `today`, calendar, drilldown, yesterday,
check-in и pregen. Запрещены прямые `datetime.now(UTC).date()` и `Date.today()`
в этих путях.

Минимальные проверки: пользователь западнее/восточнее UTC в момент полуночи,
переход DST и запрос `today` против явной ISO-даты.

## 6. HTTP-поверхность

Все endpoints требуют Telegram session и проверяют ownership. Ошибка ownership
возвращает 404, а не факт существования чужого snapshot.

| Метод и путь | Назначение | Результат |
|---|---|---|
| `GET /api/day/{date}` (`date=YYYY-MM-DD` или `today`) | получить envelope; cache hit не запускает новый LLM | `TodayConvergencePayload` |
| `POST /api/day/{date}/retry` | idempotent retry расчёта/LLM | envelope или `202 + Retry-After` |
| `POST /api/day/snapshots/{id}/impression` | зафиксировать показ `day` или `lookahead` | idempotent `204` |
| `GET /api/day/snapshots/{id}/spheres/{key}` | deterministic drilldown «почему» | evidence chain |
| `GET /api/spheres/{key}` | статическая страница сферы: natal + period layers | sphere payload |
| `GET /api/calendar?month=YYYY-MM` | hero/ordinary/not-computed календарь | calendar payload |
| `GET /api/readings/day-history?limit=N` | история только из published snapshots | day-history payload |
| `GET /api/checkin/yesterday` | check-in + post-submit recap из snapshot, не legacy dayStatus | `YesterdayCheckinResponse` |
| `POST /api/checkin` | existing create/update + observed spheres | check-in response |
| `GET /api/profile` / `PUT /api/profile` | прочитать/изменить birth-time mode | generated Profile contract |

Polling pending выполняется повторным `GET /api/day/{date}`. WebSocket/SSE не
нужны. Retry после клика получает cooldown и не создаёт второй generation call.

Невалидная Telegram session возвращает 401, чужой snapshot — 404, невалидная
дата/профиль до завершения onboarding — 422. `state=unavailable` возвращается с
HTTP 200 только для валидного запроса, где персональный расчёт технически не
удалось опубликовать; это позволяет отрисовать честный retry-state.

Calendar wire-state должен различать:

```text
hero          — snapshot опубликован и имеет convergence
ordinary      — snapshot опубликован, hero нет
not-computed  — published snapshot отсутствует
```

Никаких старых valence-заливок или неявного «нет строки = ordinary».
Month/history endpoints только читают snapshot index и никогда не запускают
sidecar или LLM для отсутствующих дат. `DayHistoryPayload` несёт date,
snapshotId, state, dayTone, selected sphere keys, impulseCount и access
projection; legacy `reading.paragraphs`/`dayStatus` в нём нет.

`YesterdayCheckinResponse` имеет одну новую generated форму:

```text
targetDate, hadCheckin, checkin,
forecastAvailable,
forecastRecap: null | {snapshotId, state, dayTone, sphereKeys}
```

`forecastAvailable=true` означает только наличие показанного snapshot за этот
локальный день. До первого submit `forecastRecap=null`: предсказанные сферы и
tone не подсказываются до ответа пользователя. После submit recap возвращается
только при валидной snapshot/impression lineage; без показанного прогноза он
остаётся null. Streak и существующий `(user_id, target_date)` не меняются.

## 7. Persistence и snapshot lineage

### 7.1 Deterministic snapshot

Новая таблица `today_snapshots` (название может быть адаптировано к модели)
содержит минимум:

```text
id, user_id, target_date, timezone,
profile_hash, input_hash, canon_hash,
formula_version, calculation_version, ephemeris_artifact_id,
birth_time_mode, birth_time_range,
deterministic_result_json, canonical_input_json,
created_at, published_at, first_day_seen_at, first_lookahead_seen_at,
supersedes_snapshot_id
```

Уникальность: `(user_id, target_date, input_hash, formula_version,
calculation_version, canon_hash)`. `canonical_input_json` содержит только нормализованный
privacy-safe factor pack; raw Telegram/profile fields запрещены. Его SHA-256
является `input_hash`/`canonical_input_ref`.

После publish deterministic fields неизменяемы. Исправление создаёт новый row с
`supersedes_snapshot_id`; ссылка разрешена только внутри того же owner/date,
циклы и перезапись прошлого дня запрещены. Publish выполняется одной транзакцией
через insert-on-conflict/load-winner, поэтому два конкурентных GET получают один
и тот же `snapshotId`, а не две опубликованные версии.

Narrative rows удаляются каскадно только вместе со snapshot. FK check-in имеет
`ON DELETE SET NULL`, но новые published snapshots не входят в W9 legacy cleanup
и сохраняются минимум 180 дней для lineage/live-validation, затем — по отдельной
retention/privacy policy.

### 7.2 Narrative lease

LLM-слой не мутирует deterministic snapshot. Нужна одна versioned content/lease
запись (допустимо объединить её с operational generation record) на
`(snapshot_id, prompt_version)`:

```text
status: pending | ready | unavailable
content_json, attempt_count, lease_until, next_retry_at,
last_error_code, created_at, updated_at
```

Это обеспечивает pending→ready, single-flight и честный retry без второй
таблицы контрфактов и без очередного LLM-вызова на refresh.

### 7.3 Check-in linkage

Additive-поля `EveningCheckin`:

```text
forecast_snapshot_id: nullable FK
prediction_seen_at: nullable datetime
prediction_seen_surface: day | lookahead | null
observed_spheres: nullable JSON array
```

Impression endpoint принимает только enum `surface=day|lookahead`; клиент не
передаёт user ID или timestamp. Для `day` server проверяет authenticated owner
и дату snapshot. Для `lookahead` дополнительно передаётся `sourceSnapshotId`, и
server проверяет, что опубликованный snapshot-источник действительно ссылается
на `{id}` в своём `lookahead`. Затем идемпотентно заполняется соответствующий
первый timestamp.

При первом создании check-in сервис выбирает фактически показанную версию за
этот локальный `target_date`: full-day exposure имеет приоритет над lookahead;
иначе берётся lookahead. FK, timestamp и surface после первого submit не
перепривязываются при обычном редактировании check-in. Непоказанный прогноз
оставляет все три поля null. В live-validation `day` и `lookahead` считаются
раздельными стратами; старый Telegram `DayFeedback` без snapshot linkage в
engine agreement не участвует. `(user_id, target_date)` и streak-constraint
остаются без изменений.

## 8. Приёмка W2/W3

### 8.1 Gate 0 — до pipeline logic

1. **Noon fallback.** Первый W2 changeset вводит один mode-aware resolver
   (`exact | bucket | unknown`) и тесты, затем переводит на него Day/Calendar.
   В deployable ветке запрещена временная замена на безусловный `422`: она
   сломает legacy-пользователей без времени до W3. Старые вызовы заменяются
   атомарно с profile mode/range либо changeset остаётся branch-only до этой
   миграции. Gate:

   ```bash
   rg -n 'birth_time.*12:00|12:00.*birth_time' \
     apps/api/app/services/today_service.py \
     apps/api/app/services/calendar_service.py \
     apps/api/app/services/natal_context_service.py
   # expected: 0 executable matches
   ```

   Совпадение в `synastry_service.py` вне scope Today rewrite; новый Day path не
   импортирует и не вызывает его.

2. **Legacy contract isolation.** Новый Pydantic root живёт в отдельном модуле
   и регистрируется как `TodayConvergencePayload` в
   `schemas/contract_registry.py`. Feature shim
   `packages/contracts/today-convergence.ts` только re-export'ит generated
   convergence-типы; ручной wire/Zod запрещён. Ни один новый W2–W7 модуль не
   импортирует `TodayPayload`, `DayStatus`, `TodayFocus`, `relativeStatus` или
   `packages/contracts/today.ts`. Legacy roots могут обслуживать старый runtime
   до cutover, но не входят в новый feature shim. После замены Calendar/history
   consumers W8 удаляет legacy roots из `PUBLIC_CONTRACT_ROOTS`, регенерирует
   OpenAPI/TS/Zod и проверяет их отсутствие; W9 удаляет уже недостижимый код.

3. Gate 0 и его команды регистрируются отдельной строкой W2 в
   `grace/verification-matrix.md`; без этого pipeline logic не принимается.

### 8.2 Completion gates

До W5 должны быть зелёными:

1. `contracts:generate`/`contracts:check` и полный state/access/content matrix;
2. unit-тесты canonical ID, caps, ownership, immutability и no-fallback;
3. migration round-trip и backfill `null birth_time → unknown`;
4. profile hash/cache changes for all three birth-time modes;
   invalid mode/time/bucket combinations возвращают 422;
5. local-date tests for day/calendar/drilldown/yesterday/check-in/pregen;
6. snapshot→day/lookahead impression→check-in SQL join на одном owner/date;
7. `contentState=unavailable` сохраняет deterministic fields;
8. locked не раскрывает snapshot/event IDs.
9. preview выдаёт только `previewTeaser`, без event IDs/timing/LLM;
10. lookahead появляется только из уже published snapshot следующего локального дня.
11. lookahead impression нельзя записать без валидной ссылки из source snapshot;
12. повторное редактирование check-in сохраняет исходную prediction lineage.
13. mutation fixtures 1–6 из master §9 выполняются как deterministic gate W2
    и повторно входят в W4 replay; их команды регистрируются в
    `grace/verification-matrix.md`.
14. до submit `YesterdayCheckinResponse.forecastRecap=null`; после submit recap
    появляется только для фактически показанного snapshot и того же owner/date.
15. migration выставляет `birthTimePromptDismissed=true` существующим
    `null → unknown`, но оставляет `false` новым bucket/unknown профилям.

W2/W3 не удаляют старый runtime и не меняют production release. Они изолируют
новый feature contract; W7 заменяет fixtures, W8 очищает generated public roots,
W9 удаляет оставшуюся недостижимую реализацию.

## 9. Явно не входит

Не добавляются отдельные counterfactual snapshots, multi-engine ephemeris,
очередь сообщений или per-sphere check-in matrix. Replay остаётся offline
инструментом W4.
