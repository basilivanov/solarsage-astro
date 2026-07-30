# W5–W8 OPERATIONS AND RELEASE TZ — Today Convergence Rewrite

Дата: 2026-07-30
Статус: **implementation-ready** для production wiring, LLM orchestration и
atomic cutover.
Нормативные источники: `00_MASTER_TZ.md` v1.12, `04_W2_W3_RUNTIME_CONTRACT_TZ.md`,
`03_W7_FRONTEND_DESIGN_TZ.md`, `W9_LEGACY_REMOVAL_MANIFEST.md`.

Цель — чтобы новый envelope был не только правильно рассчитан, но и стабильно
доставлялся пользователю менее чем за 75 секунд, с честным поведением при
сбоях. Это operational-ТЗ, не новая формула.

## 1. Production topology

Canonical production path — immutable OCI images через
`infra/production/docker-compose.app.yml` и `prod-orchestrator`. Нельзя запускать
новый pregen из mutable checkout на хосте и нельзя поднимать второй ручной API.

В Compose добавляется один one-shot profile `day-pregen`, использующий тот же
API image/digest, database network и env, что и `api`. В orchestrator добавляется
строго ограниченная команда `day-pregen`, которая запускает profile только из
installed digest-pinned compose и защищена отдельным `flock`.

Production hook состоит из repo-tracked
`infra/systemd/solarsage-day-pregen-compose.service` и
`infra/systemd/solarsage-day-pregen-compose.timer`: timer запускается ежедневно в
04:07 Europe/Moscow (`Persistent=true`), service вызывает только установленный
`/usr/local/libexec/solarsage/prod-orchestrator day-pregen`. Эти units
устанавливаются/проверяются `prod-host-prepare`, а не копируются вручную.
Существующий dev-unit, который запускает Python из mutable checkout и несёт
`TODAY_VALENCE_V1_ENABLED`, не является production hook новой модели.

Timer работает каждую ночь независимо от deploy; после нового deploy он
автоматически использует digest активного release. Job остаётся one-shot, а не
постоянно работающим сервисом.

W5 gate: `docker compose config` видит profile, `systemd-analyze verify` проходит
для новой пары units, `prod-host-prepare --check` проверяет их byte identity, а
два конкурентных ручных запуска доказывают действие flock. Enabled/active-state
проверяется release smoke после W8 cutover, не host-prepare до него.

## 2. Nightly pregen

### 2.1 Cohort

Ночью выбирается только cohort:

- session/active use за последние 14 дней (конфигурируемый параметр);
- заполнены дата, место и timezone рождения;
- `exact`, `bucket` и `unknown` допускаются одинаково;
- пользователь имеет допустимый access к Дню;
- dormant users не прогреваются, они получают on-demand snapshot.

Поля запуска:

```text
DAY_PREGEN_ACTIVE_DAYS=14
DAY_PREGEN_LLM_ACTIVE_DAYS=7
DAY_PREGEN_CONCURRENCY=3
DAY_PREGEN_MAX_USERS=500
DAY_PREGEN_DETERMINISTIC_DEADLINE_SECONDS=10
DAY_PREGEN_LLM_DEADLINE_SECONDS=45
TODAY_NARRATIVE_MAX_OUTPUT_TOKENS=700
TODAY_LLM_ON_DEMAND_CONCURRENCY=3
```

Это launch defaults в typed settings; production значения явно присутствуют в
`/etc/solarsage/app.env`. Невалидное/неположительное значение завершает job
fail-closed до выбора cohort.

При превышении cap job заканчивает run с typed outcome и не пытается незаметно
обработать всю базу. Выбор детерминирован: самые недавно активные первыми.
`targetDate` для каждой строки = завтра в timezone этого пользователя, через
resolver из runtime §5. Никакой отдельной очереди или распределённого scheduler
для v1 не требуется.

### 2.2 Две стадии

1. **Deterministic stage:** построить и атомарно опубликовать snapshot. Она не
   зависит от LLM и должна быть доступна пользователю сразу.
2. **Selective LLM warm-up:** вызвать LLM только когда access для targetDate
   равен `full` и последняя session не старше 7 дней. Остальные пользователи из
   14-дневного cohort получают только snapshot; текст запустится on-demand.
   Неуспех второй стадии не удаляет deterministic данные.

Pregen не создаёт impression: snapshot считается увиденным только после
`POST .../impression` из реального UI.

### 2.3 Idempotency и retry

- один generation lease на `(user, target_date, formula/canon)`;
- один content lease на `(snapshot_id, prompt_version)`;
- повторный запуск timer и повторный GET безопасны;
- `ready` — единственный успешный LLM outcome;
- `pending` не является ошибкой и не запускает параллельную генерацию;
- `unavailable` сохраняется с `error_code`, `attempt_count`, `next_retry_at`,
  но никогда не считается успешным pregen;
- warm-up делает максимум три bounded попытки в одном one-shot run (сразу,
  затем по due-time +5 и +20 минут), не удерживая provider slot между ними;
- retry имеет cooldown и `Retry-After`; после исчерпания попыток UI оставляет
  deterministic snapshot и честный текст «Персональный разбор пока не готов».

Шаблонный персональный fallback, универсальный совет и подмена `unavailable`
на сгенерированный текст запрещены.

### 2.4 On-demand orchestration без новой очереди

Cold GET сначала публикует deterministic snapshot, атомарно создаёт content
lease и сразу отвечает `contentState=pending`. Вызов LLM запускается через
FastAPI `BackgroundTasks` после отправки ответа; retry endpoint использует тот
же путь. Background task всегда сохраняет `ready` либо `unavailable` и не
оставляет вечный pending.

Если API-процесс завершился, lease истекает, и следующий GET/retry может
безопасно забрать работу. Запрещён бесконтрольный `asyncio.create_task` без
persistent lease. Pregen one-shot, напротив, дожидается своих bounded LLM-задач
перед итоговым summary. Поэтому message broker для v1 не нужен, а человек не
ждёт provider-call в HTTP response.

Перед provider-call background task проходит bounded process limiter
`TODAY_LLM_ON_DEMAND_CONCURRENCY` и затем забирает DB lease; конкурентные
background callbacks без lease завершаются как no-op.

## 3. LLM contract

LLM получает только selected events/convergences из published snapshot и
capabilities из `birthTime`. Он не может изменить:

- state/dayTone/polarity/evidence level;
- sphere, event ID, count или timing;
- доступность домов, ASC/MC, lots и точных часов.

Один компактный strict-JSON вызов на snapshot/prompt version: в prompt идут
только selected public units и нужный period context, а не весь ledger из ~150
параметров. Launch cap ответа — `max_output_tokens=700`; фактические input/output
tokens и latency пишутся в telemetry. Увеличивать cap обратно до 2000 ради
универсального текста запрещено без отдельного latency/copy измерения.

Каждый `summary/meaning/action` возвращается как `{text, sourceEventIds}`;
source IDs обязаны быть непустым подмножеством selected events конкретного
блока. Время и окно не генерируются моделью: UI получает их из deterministic
`EventTime`. Ответ валидируется и принимается только целиком.

Provider fallback допустим только внутри общего bounded deadline. После timeout,
schema failure, claim binding failure или невалидного ответа:

```text
contentState = unavailable
LLM fields = null
deterministic fields = unchanged
```

W6 обязан проверить claim binding: каждый narrative claim ссылается на source
event IDs; выдуманный сценарий с правильными IDs отклоняется целиком.

## 4. Latency и capacity gates

Минимальные launch-SLO:

| путь | цель |
|---|---|
| опубликованный cache hit | p95 < 1 s |
| deterministic cold path | p95 < 5 s, hard deadline 10 s, без ожидания LLM |
| LLM warm-up | p95 < 30 s, hard deadline 45 s, результат ready или unavailable |
| 20 параллельных GET одного user/date | не более одного provider-call |

Проверка выполняется с зависшим provider и с двумя конкурентными retry. Нельзя
лечить latency увеличением числа параллельных LLM-вызовов.

**W6 content-cap gate (до W8):** максимальные допустимые payload shapes из
frontend §13 проходят реальную strict-JSON сериализацию и валидацию при
`TODAY_NARRATIVE_MAX_OUTPUT_TOKENS=700`: fixture №4 —
`convergence_today` с тремя публичными сферами; fixture №8 — `quiet_day` с
`mainEvent`, тремя impulses и `lookahead`. Convergence и `mainEvent` намеренно
не объединяются: это запрещено runtime-контрактом. Для обоих обязательны
`contentState=ready`, отсутствие truncation/schema failure и измеренный output
в пределах cap тем же tokenizer/model, что используются в production. В том же
gate schema validator проверяет `summary.text ≤ 220` для каждого блока:
boundary fixture на 220 символов принимается, 221 символ отклоняет весь
narrative без обрезки и fallback. Token cap и per-field limit должны пройти
одновременно. Если gate не проходит, сначала сокращаются prompt/LLM-поля;
повышение cap допускается только отдельным измеренным решением с повтором
latency-gate.

Минимальные operational counters (без PII): cohort selected, deterministic
success/failure, snapshot hit/miss, LLM latency/status, retry count, pending
age, `state/dayTone` distribution. Новые log events сначала регистрируются в
`apps/api/app/core/logging_events.py`; логирование не должно ломать flow.

## 5. Consumer wiring

### 5.1 Обязательная матрица

| consumer | источник | access/cache invariant |
|---|---|---|
| Day | один snapshot user/local-date | full/preview/locked projection; on-demand compute допустим |
| Calendar month | snapshot index | не рассчитывает пропущенные даты; `not-computed` остаётся отдельным state |
| Readings history | `DayHistoryPayload` | только published rows; без семи параллельных cold Day-запросов |
| Yesterday/check-in recap | показанный snapshot локального вчера | детали скрыты до submit; recap отсутствует без day/lookahead impression; legacy dayStatus запрещён |
| Sphere drilldown | explicit snapshotId + sphere | только owner + full access; preview не получает evidence |
| Static sphere page | profile_hash + period identity | натал кэшируется до смены профиля; period layer обновляется только со сменой периода |
| Pregen | локальное завтра каждого cohort user | пишет snapshot/content, но не impression |

Все consumer'ы используют один local-date resolver и generated contracts.
Calendar/Readings не восстанавливают старый статус дня из `dayTone`.

### 5.2 W7 frontend integration

Frontend подключается только к контракту из `04_W2_W3_RUNTIME_CONTRACT_TZ.md` и
исполняет `03_W7_FRONTEND_DESIGN_TZ.md`:

- 16 mock fixtures для структурной/visual проверки;
- отдельный `contentState=unavailable` и отдельный `state=unavailable`;
- exact/bucket/unknown без домов/точных часов вне exact;
- календарь с `hero|ordinary|not-computed`;
- sphere navigator, deterministic drilldown и static sphere page;
- Yesterday/check-in без prediction priming: до submit только
  `forecastAvailable`, после submit — typed `forecastRecap` при lineage;
- `data-day-tone`, `data-content-state`, `data-access-state` вместо старого
  `data-status`.

LLM-зона может polling'ить тот же GET; full-screen spinner и websocket не нужны.

## 6. W8 release acceptance

До atomic cutover должны пройти следующие реальные сценарии без route
interception:

1. Telegram HMAC → full exact → `convergence_today`/`quiet_day`;
2. Telegram HMAC → unknown или bucket → устойчивый payload без домов и часов;
3. locked/preview access → нет скрытых snapshot/event data; cross-user snapshot
   request отдельно возвращает 404;
4. зависший/невалидный LLM → deterministic payload + `unavailable`, без
   fallback-copy;
5. calendar → day → drilldown → evening check-in с тем же snapshot ID;
   до submit recap скрыт, после submit связан с этим snapshot;
6. quiet lookahead → viewport impression → check-in следующего дня с тем же
   immutable snapshot ID и `prediction_seen_surface=lookahead`.

Mock/visual 16-state matrix остаётся отдельным быстрым gate; эти шесть сценариев
проверяют только настоящую связку auth → API → sidecar → DB → frontend.

Orchestrator smoke расширяется проверкой нового authenticated day contract или
эквивалентным обязательным real-e2e job перед записью release record. Одного
front+GeoNames smoke недостаточно.

## 7. Migration, cutover и rollback

Порядок:

1. `prod-host-prepare --apply/--check` устанавливает новый compose,
   orchestrator и pregen units, но timer пока остаётся disabled;
2. additive Alembic migration и round-trip на dev;
3. restore rehearsal из pre-migration dump;
4. удалить legacy Today/Calendar roots из `PUBLIC_CONTRACT_ROOTS`,
   регенерировать OpenAPI/TS/Zod и доказать, что новый frontend собирается без
   `TodayPayload`, `DayStatus`, `TodayFocus`, `relativeStatus`;
5. build/pin API, sidecar и frontend images одного SHA;
6. run migration profile и `alembic current --check-heads`;
7. deploy API+sidecar+frontend атомарно;
8. real-e2e/smoke + bounded `day-pregen` smoke на тестовом пользователе;
9. после зелёного smoke включить production timer и записать release record;
10. в том же release-doc change синхронизировать AGENTS.md и
   `docs/PRODUCTION_RUNBOOK.md` с реально установленным hook.

Rollback сначала выключает новый pregen timer, затем возвращает весь предыдущий
OCI release целиком. Schema rollback не делается. Timer снова включается только
на release, который прошёл его smoke; старые app services не запускаются
параллельно с новым envelope.

Protected data не трогается: users, profiles, auth/session, access ledger,
payments, subscriptions, EveningCheckin, DayFeedback, paid reports и streaks.
Legacy derived Today/cache rows удаляются только отдельным W9 allowlisted
cleanup после стабильного периода.

## 8. W8 → W9 handoff

W9 начинается только после:

- успешного real-e2e на production-like окружении;
- подтверждённого rollback target;
- dump/restore rehearsal;
- `rg` legacy gate, где оставшиеся совпадения объяснены manifest/supersession;
- отсутствия смешанных old/new payloads.

W10 live-validation (snapshot-linked check-in, 60–90 дней) не блокирует первый
релиз, но snapshot/impression linkage обязателен с первого дня.

## 9. Не добавляем в v1

Не нужны message broker, WebSocket, отдельный autoscaling worker pool,
multi-engine расчёт, повторный full replay или новая матрица из 12 вопросов
check-in. Один Compose one-shot job, один lease-механизм и один real-e2e flow
достаточны для запуска.
