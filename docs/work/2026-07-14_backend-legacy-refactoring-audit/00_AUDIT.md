# Аудит backend, sidecar и legacy SolarSage Astro

- Дата: 2026-07-14
- Режим: **audit only** — код, конфигурация, БД и runtime не изменялись
- Ветка: `main`
- Проверенный commit: `8f9aa022550653020e0dc9d1f1269d73f6ee63cf`

## 1. Итоговый вердикт

Backend уже нельзя считать «хаотичным legacy»: в нём есть сильная доменная база, большое покрытие тестами, Alembic с одной актуальной головой, общий контракт activation layer и заметная работа по V2. Но архитектура сейчас находится в переходном состоянии, а production-конфигурация расходится с задуманными ограничениями.

Главные выводы:

1. Сначала нужен не большой рефакторинг, а короткая аварийная волна безопасности. Публичный API фактически запущен с `APP_ENV=development`; из-за этого произвольный Origin принимается вместе с credential-cookie. Это подтверждено запросом к работающему контуру.
2. В production открыты диагностические и административные endpoints, которые не должны быть публичными: `/api/debug`, `/api/metrics`, `/api/health/extended`, `/api/admin/microcopy/misses`. Часть из них отдаёт внутренние сведения или делает внешние dependency-пробы за счёт сервера.
3. В структурные логи попадают сырые `user_id`, а horary дополнительно формирует сообщения с идентификаторами сущностей. Текущий redactor не считает `user_id` PII.
4. Самая дорогая продуктовая зона — Today/Calendar. Один холодный Today может сделать до шести последовательных LLM-вызовов, а затем запустить недельный prefetch. Холодный Calendar способен последовательно рассчитать десятки дней с множеством DB- и sidecar-вызовов.
5. Today V2 payload/cache перегружен доказательной диагностикой: средний сериализованный блок `v2` в production-кэше около 173 KB, `concrete_advice` — около 139 KB; максимальная строка кэша — около 582 KB. Полные evidence и score breakdown нельзя продолжать передавать как обычную продуктовую read model.
6. V1/V2, старый и новый LLM-слои, а также часть sidecar-классов сосуществуют как незавершённые миграции. Их нельзя удалять одним коммитом: сначала нужны parity-ворота и наблюдаемое отключение старого пути.
7. Есть безопасный legacy-кандидат на удаление уже после короткой проверки ссылок: `YesterdayService`, runtime day fixtures, неиспользуемый sidecar calculator и случайно закоммиченные локальные DB/artifacts. Есть и сущности, которые выглядят пустыми, но удалять их только по нулевым строкам нельзя: payments, chat, natal reports.
8. CI не отражает заявленные правила проекта: Ruff/mypy сейчас красные, но не являются обязательным backend gate; несколько workflow используют устаревшие порты, Python/npm-команды и запрещённый ручной запуск API.

Рекомендуемая стратегия: **security/config → стоимость и надёжность → упрощение Today/LLM → завершение V2-миграции → декомпозиция sidecar → удаление подтверждённого legacy**.

## 2. Область и метод аудита

Проверено:

- `apps/api/app`: routes, services, clients, schemas, models, migrations, logging, security и config;
- `apps/solarsage/solarsage`: HTTP API, расчётный core, activation builder, модели и версии;
- `packages/py-contracts`: versioned activation contracts;
- backend/sidecar tests, статические проверки, CI workflows, compose/systemd/runbooks;
- read-only состояние работающих API/sidecar endpoints;
- только агрегаты production PostgreSQL без вывода персональных значений;
- git references для проверки реального использования legacy-кандидатов.

Не выполнялось:

- никаких изменений runtime, systemd, nginx, `.env`, БД или кода;
- никаких POST/PUT/DELETE в production;
- нагрузочный тест production;
- удаление или миграция данных;
- commit/push.

Субагенты были запущены для параллельных частей аудита, но их окружение не имело shell-доступа. Поэтому все приведённые ниже технические факты повторно проверены основным агентом локально и read-only.

## 3. Текущая архитектурная карта

```text
Telegram WebApp / Frontend
          |
          v
Nginx :80/:443
  |-- /api/* --------> FastAPI :8000
  |                       |-- PostgreSQL :5433
  |                       |-- SolarSage sidecar :18091
  |                       |-- OpenRouter / LLM provider
  |                       `-- GeoNames
  `-- /* ------------> Next.js :3002
```

Ключевые backend-потоки:

| Поток | Текущее состояние | Главная проблема |
|---|---|---|
| Telegram auth/session | Работает, production HMAC path есть | Каждая авторизация создаёт новую сессию; нет разумного cap/reuse |
| Today | Работает, V2 включён | God-service, 6 LLM-вызовов, тяжёлый payload, cache races, недельный prefetch |
| Calendar | Работает | Последовательный N+1 по дням, access/cache/sidecar |
| Activation sidecar | Работает, общий activation contract есть | CPU-bound sync core внутри async routes; монолитный builder |
| Horary | Работает | Ненадёжный `asyncio.create_task`, долгие транзакции вокруг внешних вызовов |
| Chat | Публичный контракт есть | Ответ пока echo, quota/transactions некорректны |
| Natal report | Feature flag выключен | Долгий sync-flow, retry конфликтует с unique constraint |
| Payments | Намеренно отключены | Публичный stub surface остаётся в API |
| Microcopy | Endpoint существует | Нет продуктовых callers и данных; admin endpoint без auth |

## 4. Приоритеты

### P0 — исправить до крупного рефакторинга

| ID | Находка | Риск | Рекомендуемое действие |
|---|---|---|---|
| SEC-01 | Production API запущен с `APP_ENV=development`; CORS отражает произвольный Origin с credentials | Cross-origin чтение/действия от имени пользователя в браузерах, где third-party cookie проходит | Немедленно выставить production env, fail-closed валидатор startup и explicit allowlist Origins |
| SEC-02 | `/api/debug` смонтирован без production guard | Утечка внутренних auth/runtime сведений | Не монтировать в production; endpoint должен быть dev-only на уровне router registration |
| SEC-03 | Сырые `user_id` и entity IDs попадают в логи | Privacy incident и расширение зоны чувствительных данных | Хешировать actor identity, расширить redactor, очистить message strings, проверить retention журналов |
| SEC-04 | Неавторизованные admin/diagnostic surfaces | Разведка, внешняя нагрузка, раскрытие внутренних метрик | Закрыть или убрать `/metrics`, `/health/extended`, `/admin/microcopy/misses`; оставить минимальные liveness/readiness |

### P1 — ближайшая волна надёжности и стоимости

| ID | Находка | Риск | Рекомендуемое действие |
|---|---|---|---|
| PERF-01 | Calendar делает последовательную работу по трём месяцам | Большая latency и лавина DB/sidecar вызовов | Batch access/cache, ограниченный диапазон расчёта, background materialization |
| PERF-02 | Today после cold response запускает недельный prefetch | До 7 дополнительных тяжёлых Today и до 42 LLM-вызовов | Отключить до появления бюджета, dedupe, access-aware политики и worker |
| PERF-03 | До 6 последовательных LLM-вызовов на один Today | Latency, цена, высокий failure surface | Один versioned structured generation либо максимум 2 bounded parallel stages |
| PERF-04 | Today cache/payload содержит полные evidence | Большие JSON, память, сеть, медленный parse | Отделить audit model от product read model, передавать top evidence/IDs |
| REL-01 | Concurrent cold Today не имеет singleflight/upsert recovery | Дублирование дорогой работы и возможный 500 на unique race | Per-key singleflight/lock и idempotent upsert+reread |
| REL-02 | Horary job живёт в process-local task | Потеря работы/кредита при рестарте | DB-backed job/outbox, recovery и idempotent refund/finalize |
| REL-03 | API создаёт чрезмерное число сессий | Рост таблицы, большая поверхность credentials | Frontend auth singleflight + backend reuse/rotation/cap/cleanup |
| REL-04 | Sidecar CPU-bound расчёты выполняются из async route | Блокировка event loop и health под нагрузкой | Безопасная process/executor модель после проверки thread-safety Swiss Ephemeris |
| ABUSE-01 | `/_log` принимает неавторизованные и неограниченные batches | Log amplification/DoS и токсичные данные в stdout | Auth или signed intake, batch/body limits, rate/sampling, schema bounds |
| ABUSE-02 | Geo autocomplete публичен и fan-out вызывает timezone на каждый result | Внешний quota amplification | Auth, cache, rate limit, query/result bounds и сокращение fan-out |

### P2 — архитектурное упрощение

| ID | Находка | Рекомендуемое действие |
|---|---|---|
| ARCH-01 | `TodayService.get_today_payload` — длинный orchestration method | Разделить на use-case stages: context, chart snapshot, scoring, narrative, persistence |
| ARCH-02 | V1 и V2 считаются одновременно, V2 импортирует private V1 helpers | Вынести общие scoring primitives, остановить dual-run после измеряемого convergence window |
| ARCH-03 | LLM существует как монолит и незавершённый split package | Выбрать один canonical package, мигрировать callers/tests, затем удалить второй |
| ARCH-04 | `activation_builder.py` — 1849 строк, основная функция около 1371 строки | Выделить chart context и registry независимых technique handlers |
| ARCH-05 | Natal/transits contracts дублируются между API и sidecar | Ввести общий versioned chart snapshot contract, включая `planet.house` |
| ARCH-06 | Commit ownership размазан между routes/services | Use-case владеет транзакцией; сервисы делают `flush`, внешняя работа вне DB lock |
| ARCH-07 | Profile completeness/date timezone определяются по-разному | Единый predicate и user-local date policy |
| ARCH-08 | Config допускает dev defaults в публичном сервисе | Environment-specific validation и отказ старта при опасной конфигурации |

### P3 — controlled cleanup

| ID | Находка | Решение |
|---|---|---|
| LEG-01 | Dead `YesterdayService` и старые day fixtures | Удалить после одной reference/contract проверки |
| LEG-02 | Sidecar calculator и несколько compatibility models/services не используются продуктом | Удалять по одному после проверки внешних consumers |
| LEG-03 | Transitional checkin columns dual-write | Завершить migration/backfill, потом drop legacy columns новой миграцией |
| LEG-04 | Случайные DB/pip artifacts tracked в репозитории | Удалить из tip, добавить ignore, оценить очистку истории из-за возможных PII/session hashes |
| LEG-05 | Stale compose, runbooks, workflows, Prefect config | Выбрать один ops canon, переписать или архивировать противоречащие файлы |

## 5. Детальные находки

### 5.1. Security и privacy

#### SEC-01. Production CORS фактически работает в development-режиме

Код:

- `apps/api/app/main.py:72-83` использует production allowlist только при `APP_ENV == "production"`;
- в иной среде выставляется wildcard origin при `allow_credentials=True`;
- `apps/api/app/core/security.py:49-70` выдаёт session cookie с `SameSite=None; Secure`.

Runtime-проверка показала:

```text
APP_ENV=development
Origin: https://evil.example
Access-Control-Allow-Origin: https://evil.example
Access-Control-Allow-Credentials: true
```

Это не теоретическая конфигурационная неточность, а работающий fail-open режим. Даже если конкретная версия браузера блокирует часть third-party cookie сценариев, полагаться на это как на security boundary нельзя.

Что сделать:

1. Исправить EnvironmentFile, который реально читает `solarsage-api.service`.
2. Добавить startup validator: публичный deployment не стартует при `APP_ENV != production`, wildcard CORS, пустом bot token, некорректном provider или небезопасной cookie-конфигурации.
3. Хранить явный список Telegram/frontend origins.
4. Добавить regression test и post-deploy probe: evil Origin не получает `Access-Control-Allow-Origin`.

#### SEC-02. Debug router противоречит собственному контракту

- `apps/api/app/api/debug.py:26` говорит, что endpoint нельзя включать в production;
- `apps/api/app/main.py:90` монтирует router без environment guard;
- `apps/api/app/api/debug.py:47-111` может показывать UUID, Telegram metadata, cookie/header сведения и версии;
- endpoint использует устаревшее имя cookie `grace_session` вместо текущего `grace_session_v2`;
- anonymous runtime request возвращает HTTP 200.

Правильное исправление — не «спрятать больше полей», а вообще не регистрировать debug router в production. Проверка должна подтверждать 404, а не только отсутствие отдельных ключей.

#### SEC-03. Redactor не защищает `user_id`

- `apps/api/app/core/redactor.py:52-75` не включает `user_id` в PII keys;
- exact-key обработка находится в `redactor.py:118-131`;
- raw IDs пишутся, в частности, в `day_scoring_runtime_service.py:182,202`, `today_service.py:328`, `calendar_service.py:339`;
- horary включает `user_id`, question/credit IDs и другие идентификаторы в message strings/payloads (`horary_service.py:361-411,504-541`);
- middleware пытается определить route template до завершения routing (`middleware/correlation.py:93-100`), поэтому сырой path parameter тоже может оказаться в журнале.

Read-only journal audit обнаружил 114 структурных полей с именем `user_id` с момента текущего старта API. Значения в отчёт намеренно не выводились.

Нужны одновременно:

- стабильный неперсональный `actor_hash`, если корреляция действительно нужна;
- запрет raw `user_id`, Telegram ID и entity IDs в свободном тексте логов;
- расширение redactor и negative guardrail по ключам и message patterns;
- определение route template после routing;
- решение по retention/rotation уже созданных журналов.

#### SEC-04. Публичные operational endpoints

Подтверждены anonymous HTTP 200:

- `/api/metrics` — отдаёт продуктовые агрегаты, включая пользовательские counts;
- `/api/health/extended` — проверяет DB, OpenRouter и GeoNames, раскрывает причины ошибок;
- `/api/admin/microcopy/misses` — в коде явно оставлен без auth «для MVP»;
- `/api/debug` — рассмотрен отдельно выше.

Extended health дополнительно превращает каждый внешний запрос в server-side dependency probes, включая запрос к OpenRouter с настроенным ключом. Следует разделить:

- `/health/live` — процесс жив, без сети и БД;
- `/health/ready` — короткие локальные readiness checks, закрытые сетью/monitoring policy;
- подробную диагностику — только internal/admin auth, с cache и timeout.

#### ABUSE-01. Frontend log intake не имеет обязательных защит

- `apps/api/app/api/_log.py:83-95` принимает список произвольного размера и не требует session;
- `apps/api/app/services/log_intake.py:60-112` не применяет заявленный rate limit, а каждый envelope выводит в stdout;
- module/test contract расходится с поведением: тест фиксирует anonymous 200.

Минимальный контракт: ограничение HTTP body и batch count, длины строк/metadata depth, rate limit, sampling, запрет неизвестных event names и либо authenticated session, либо отдельная подписанная intake-схема.

#### ABUSE-02. Geo autocomplete умножает внешние вызовы

- `apps/api/app/api/geo.py:46-92` не требует auth и не ограничивает запрос на уровне route;
- `apps/api/app/services/geonames.py:74-139` после search может вызвать timezone endpoint для каждого результата;
- default result count 8 означает до 9 внешних вызовов на один входной request, а fallback query modes могут добавить ещё search-вызовы.

Нужны cache по нормализованному query, rate limit, min/max query length, меньший result limit и отделение timezone lookup от autocomplete либо batch/ленивое обогащение выбранного города.

### 5.2. Today, Calendar и стоимость вычислений

#### PERF-01. Calendar cold path — последовательный N+1

`apps/api/app/services/calendar_service.py:85-174` собирает предыдущий, текущий и следующий месяцы по одному дню. Для каждого дня:

- `AccessService.can_access_day` снова читает access state;
- `_get_cached_day_status` делает до двух cache queries (`calendar_service.py:200-268`);
- при miss `_compute_and_cache_day_status` вызывает sidecar и commit (`calendar_service.py:270-438`).

При холодном V2 это может означать десятки sidecar calculations и около 90 повторных access checks.

Целевой дизайн:

1. Один access snapshot на весь диапазон.
2. Один batch SELECT кэша на диапазон.
3. Вычислять только реально видимые/необходимые дни.
4. Материализовать диапазоны background worker-ом или range endpoint sidecar.
5. Использовать ограниченный concurrency и один transaction boundary для записи результата.

#### PERF-02. Недельный prefetch не знает стоимости и права доступа

- `TodayService` запускает background task после cold response (`today_service.py:592-596`);
- `_prefetch_week` создаёт расчёты для семи дней (`today_service.py:964-998`);
- dedupe — process-local set, а не per-user/cache-key/distributed control;
- вызов с `access_state=None` трактуется как full path (`today_service.py:203-205`).

Следствие: один пользовательский miss может породить семь дополнительных тяжёлых расчётов, включая narrative для дней, которые пользователь может не открыть. При шести LLM stages это до 42 дополнительных LLM requests.

Рекомендация: временно отключить prefetch либо оставить только deterministic chart/scoring materialization без LLM. Возвращать его можно после появления job queue, бюджета, access-aware политики, dedupe и метрик hit-rate/cost saved.

#### PERF-03. LLM pipeline раздроблен на последовательные вызовы

В cold Today отдельно формируются headline, reading, notes, why, concrete advice и planet interpretations (`today_service.py:412-446`, `today_interpretation_service.py:483,653`). Каждый вызов создаёт новый `httpx.AsyncClient` (`llm_service.py:133-172`).

Предлагаемый target:

- один versioned JSON schema для narrative package: headline, human explanation, three horizons, actions и concise planet copy;
- если качество требует двух проходов — generation + validator/editor, но не шесть независимых сетевых round trips;
- один lifespan-owned HTTP client с connection pooling;
- отдельные deterministic fallbacks без повторной отправки персональных исходных данных.

#### PERF-04. Product response смешан с audit evidence

Production `today_payload_cache`:

| Метрика | Значение |
|---|---:|
| Строк | 34 |
| Общий объём JSON | 7,679,583 bytes |
| Средняя строка | 225,870 bytes |
| Максимальная строка | 582,414 bytes |
| Средний `v2` среди содержащих его строк | 172,953 bytes |
| Средний `concrete_advice` | 138,639 bytes |
| Среднее число evidence items на advice row | 28.07 |
| Максимальное число evidence items на advice row | 199 |

Причина видна в контракте: `TodayV2Block` несёт полный activation evidence и score breakdown, а advice копирует evidence для каждой из 12 сфер.

Нужно разделить три модели:

1. **Calculation/audit artifact** — полный воспроизводимый evidence graph, внутреннее хранение.
2. **Product read model** — top signals, короткие explanations, evidence IDs и только то, что рисует frontend.
3. **Observability summary** — counts, versions, timings, без персонального содержимого.

Рекомендуемый первый бюджет: p95 обычного Today JSON менее 100 KB без потери видимого UI; точное значение утвердить после замера frontend waterfall.

#### REL-01. Cache race и кэширование деградировавшего текста

- `_cache_payload` делает SELECT-then-INSERT без обработки конкурентного unique conflict (`today_service.py:795-831`);
- два одинаковых cold requests могут оба выполнить всю дорогую работу, после чего один упадёт на записи;
- при LLM failure в payload кладётся «Данные временно недоступны», затем весь payload кэшируется (`today_service.py:456-468,590`).

Нужно:

- per-cache-key singleflight или distributed lock;
- idempotent upsert с reread победившей строки;
- deterministic и narrative cache разделить;
- degraded narrative не кэшировать либо давать короткий TTL/status, чтобы временная ошибка не жила как нормальный результат.

### 5.3. LLM subsystem

#### ARCH-03. Split начат, но canonical implementation остался не определён

- `apps/api/app/services/llm_service.py` — монолит примерно на 1141 строку и текущий production caller target;
- `apps/api/app/services/llm/*` — новый пакет, но продуктовые callers на него не переведены;
- история репозитория содержит split и последующий revert.

Пока оба варианта живут, любое исправление provider/fallback/prompt может расходиться. Необходимо выбрать пакет как canonical, перенести публичный facade и patch points тестов, провести parity, затем удалить монолит.

#### LLM-01. Provider abstraction сейчас логически неполна

В split-версии:

- Anthropic client создаётся в зависимости от provider (`llm/client.py:60-70`);
- `_anthropic_generate` вызывает sync API внутри async функции (`llm/client.py:113-119`);
- `_generate_text` всё равно всегда пробует OpenRouter, затем DeepSeek (`llm/client.py:121-145`);
- DeepSeek settings в canonical config отсутствуют, поэтому fallback практически мёртв;
- разные типы ошибок сворачиваются в reason `timeout`.

`TodayInterpretationService` считает LLM доступным при наличии любого provider key, даже если выбран другой provider.

Target: typed provider adapters с одним интерфейсом, async clients, startup validation именно выбранного provider, корректная классификация timeout/429/5xx/schema error и только реально настроенный fallback. Мёртвый DeepSeek branch лучше удалить, чем имитировать отказоустойчивость.

#### PRIV-01. Natal report передаёт LLM больше персональных данных, чем требуется

`natal_report_service.py:649-669` собирает имя, точные дату/время/место рождения и timezone. Для интерпретации уже рассчитанной карты модели достаточно chart facts и нейтрального display name либо вообще обращения без имени.

До включения natal reports в production нужно применить data minimization и явно описать third-party data boundary.

### 5.4. Sidecar и вычислительный контракт

#### REL-04. CPU-bound sync core вызывается из async routes

`activation_layer.py`, `natal.py`, `transits.py` объявляют async endpoints, но внутри напрямую запускают синхронные CPU-bound вычисления Swiss Ephemeris. При одном uvicorn worker это блокирует event loop, включая health requests.

Нельзя механически отправлять расчёты в произвольный thread pool: сначала требуется проверить thread-safety глобального состояния Swiss Ephemeris. Предпочтительный вариант — выделенный process worker/serialized calculation executor либо несколько изолированных процессов с контролируемой очередью.

#### ARCH-04. Activation builder стал монолитом техники

`apps/solarsage/solarsage/services/activation_builder.py` — около 1849 строк; `build_activation_layer` — около 1371 строки. Внутри объединены chart context, house calculations и множество техник. Есть lazy/circular imports с progressions/eclipses и дублируются `_find_house`, `_angular_distance`.

Разделять следует не по случайным helper-файлам, а по контракту:

```text
ChartSnapshot/CalculationContext
        |
        +-- transit handler
        +-- progression handler
        +-- profection handler
        +-- firdaria handler
        +-- eclipse handler
        `-- ...
        |
ActivationAggregator -> versioned ActivationLayerResponse
```

Каждый handler — pure насколько возможно, с фиксированными golden/parity fixtures. Aggregator отвечает только за версии, дедупликацию, ordering и общий response contract.

#### ARCH-05. Контракты chart snapshot не унифицированы

Activation layer уже использует `solarsage_contracts`, но natal/transits модели локально продублированы. Sidecar не отдаёт `planet.house`; API повторно вычисляет дом через longitude/cusps.

Нужен общий versioned контракт `ChartSnapshot`, который включает:

- planet longitude/sign/degree/house;
- houses/cusps;
- calculation version и ephemeris identity;
- timezone/input normalization metadata без лишней PII;
- стабильные enum/string conventions без `Transit_`/`Natal_` leakage.

Миграция: additive field → API dual-read → метрики old/new → require new version → удаление локальной нормализации.

#### SIDECAR-01. Health сообщает неверную версию

Live sidecar health возвращает:

```text
version=dev
calculation_version=ss-1.0.0
```

При этом shared canonical calculation version — `ss-calc-1.2.0`. Версия расчёта участвует в cache identity и воспроизводимости, поэтому health не должен показывать default. Значение должно импортироваться из одного version source и валидироваться на startup.

#### SIDECAR-02. Exception details возвращаются клиенту

Activation/natal/transits routes формируют HTTP detail из исходного exception. Public API должен получать стабильный error code/correlation ID; stack/error detail остаётся в redacted structured log.

### 5.5. Persistence, jobs и transaction boundaries

#### REL-02. Horary background job недолговечен

`apps/api/app/api/horary.py:219-222` использует bare `asyncio.create_task`. При рестарте процесса задача исчезает, а вопрос/кредит могут остаться в промежуточном состоянии. Внутри генерации row lock удерживается через внешние sidecar/LLM вызовы (`horary_service.py:382` и далее).

Target flow:

1. Короткая транзакция создаёт question + job/outbox и резервирует credit idempotently.
2. Worker claim-ит job с lease.
3. Внешние вычисления идут без долгого DB lock.
4. Короткая compare-and-set транзакция сохраняет answer.
5. Retry/recovery безопасны; refund тоже идемпотентен.

#### TX-01. Referral может частично зафиксироваться

Route вставляет `Referral`, затем `AccessService.grant_referral_bonus` выполняет собственные commits. Это допускает частичное состояние. У таблицы нет DB unique constraint на invitee, хотя доменная логика предполагает одну активацию.

Нужно перенести transaction ownership в один referral use-case, использовать `flush`, добавить unique constraint/idempotency key и concurrency test на PostgreSQL.

#### SESSION-01. Сессии бесконтрольно множатся

Агрегаты production DB:

```text
sessions total: 2860
active: 2525
revoked: 17
expired: 318
users with sessions: 39
average active per such user: 64.74
maximum active for one user: 1765
users with >10 active sessions: 18
users with >100 active sessions: 2
```

Причина: auth path каждый раз создаёт новую session, backend не делает reuse/cap/cleanup, а frontend auth hook может инициироваться несколькими consumers.

Решение:

- один application-level `AuthProvider`/singleflight на frontend;
- backend session reuse/rotation по устройству или Telegram WebApp instance;
- разумный cap активных sessions на пользователя/устройство;
- scheduled cleanup expired/revoked;
- метрики session creation rate и active sessions per actor.

#### NATAL-01. Retry natal report конфликтует с unique constraint

Feature выключен, что сейчас правильно. Перед включением нужно исправить:

- восемь последовательных LLM sections выполняются в одном HTTP-flow;
- `GENERATING` может остаться навсегда после рестарта;
- код пытается создать новый row для retry/force regenerate, но unique constraint `(user, natal_context, prompt, schema)` запрещает это;
- тот же конфликт делает ветку `MAX_RETRY` практически недостижимой.

Правильная модель: один logical report + отдельные attempts/jobs либо обновляемый report с attempt counter, lease и versioned immutable completed artifact.

#### CHAT-01. Chat route уже публичный, но продуктовая реализация не завершена

- `api/chat.py:163-170` формирует echo response;
- quota проверяется и коммитится до проверки ownership thread;
- конкурентные запросы могут превысить quota;
- user и assistant messages коммитятся отдельно;
- content не ограничен, history не пагинируется.

В production таблицы chat почти пусты. Нужен продуктовый выбор: временно скрыть/unmount surface либо завершить атомарный bounded chat use-case. Оставлять echo как будто это готовый API — худший промежуточный вариант.

### 5.6. Domain consistency

#### DOMAIN-01. Profile completeness определяется неодинаково

- onboarding может считаться завершённым при наличии birthday/city/gender;
- natal context требует birthday, exact time, coordinates, timezone и gender;
- day route использует ещё один набор условий и обращается к profile до полной null-проверки.

Нужны явные predicates, например:

```text
is_onboarding_complete
can_calculate_day
can_calculate_natal
can_generate_natal_report
```

Они должны жить в одном domain policy module, а не повторяться в routes/services.

#### DOMAIN-02. «Сегодня» считается по UTC, а не по timezone пользователя

`/day/today` и calendar current-day marker используют UTC. Для астрологического продукта граница дня должна быть user-local. Нужна единая функция `user_local_date(profile.timezone, now)` и тесты около полуночи/DST.

#### DOMAIN-03. Известный баг `Transit_` уже исправлен

В AGENTS.md всё ещё указан bug про `Transit_Moon`/`Natal_`. В текущем коде `TodayService._planet_label` уже удаляет эти префиксы (`today_service.py:609-638`, исправление появилось в commit `c2baf94`).

Это stale documentation, а не текущая backend-задача. Запись следует обновить, чтобы команда не сделала повторный «fix». Второй известный gap — отсутствие `planet.house` в sidecar contract — остаётся актуальным.

### 5.7. Logging architecture

Помимо PII:

- `core/dependencies.py:60-69` использует raw `print` на каждом защищённом запросе и выводит cookie names/token length/rejection reason, обходя GRACE logger/redactor;
- `logging.py:260-297` обещает, что logger не ломает flow, но unknown event validation находится вне `try` и способна бросить `ValueError`;
- в `logging.py` остаются unused fallback/setup/global logger branches;
- guardrail проверяет некоторые imports, но не запрещённые PII keys/free-text patterns.

Рефакторинг должен сначала закрепить один безопасный logging facade и negative tests, а затем удалить старые ветки. Простая замена `print` на `logger.info` без data policy проблему не решит.

## 6. Что считать legacy и что удалять

### 6.1. Можно готовить к быстрому удалению

| Кандидат | Почему legacy | Ворота перед удалением |
|---|---|---|
| `apps/api/app/services/yesterday_service.py` | Нет production references; frontend использует checkin endpoint | `rg` по импорту/контракту, versioned удаление `yesterday_echo`, tests green |
| `apps/api/app/fixtures/day_2026-05-30.json` | Runtime fixture без callers | Проверить scripts/tests/docs references |
| `apps/api/app/fixtures/day_generic.json` | То же | То же |
| `apps/solarsage/solarsage/services/calculator.py` | Нет импортов | Sidecar tests + external packaging consumer check |
| `apps/api/=0.40.0` | Случайный pip output artifact | Удалить, убедиться, что CI не ссылается |
| `apps/api/dev.db` | Пустая локальная DB | Удалить, добавить `*.db`/точечный ignore |
| `apps/api/astro_dev.db` | Локальная SQLite с пользовательскими/session данными | Удалить из tip, оценить history purge/privacy response |
| raw debug router в production | Противоречит контракту и опасен | Dev-only import/mount test |
| microcopy admin route | Нет auth, нет product callers, таблица пуста | Product owner подтверждает отсутствие planned consumer |

### 6.2. Удалять только после миграционных ворот

| Кандидат | Почему пока нельзя удалить | Ворота |
|---|---|---|
| V1 day scoring | Нужен rollback/parity reference | Convergence metrics, V2 rollback plan, cache version cutover |
| Local activation fallback | Может быть аварийным fallback sidecar | Sidecar SLO, explicit breaker/fallback policy |
| Монолит `llm_service.py` | Все product callers пока используют его | Полная миграция на package + parity tests |
| `TransitsService`, `Transit`, `PlanetPosition` compatibility exports | Возможен внешний consumer package | Repo/package consumer audit, deprecation release |
| Legacy checkin `mood`/`notes` columns | Идёт dual-read/write переход | Production backfill validation, stop dual write, новая Alembic migration |
| Полный V2 evidence | Нужен для аудита и воспроизводимости | Отдельное audit storage/API до slimming product payload |
| Stale Poetry lock | Сначала выбрать package manager | Canonical pip/uv/Poetry решение и воспроизводимый lock |

### 6.3. Не удалять только потому, что таблицы пусты

- payments;
- chat;
- natal reports;
- horary auxiliary tables;
- historical Alembic migrations.

Для них нужен продуктовый ADR: feature закрывается окончательно либо доводится. Исторические миграции не переписывать; schema cleanup делать новой миграцией.

### 6.4. Не трогать без замены parity oracle

- golden astrology fixtures;
- frozen reference collector `collect_solarsage_western_deep.py`;
- расчётные эталоны activation layer.

В fixtures встречаются реальные или реалистичные имена и birth data. Их следует синтетизировать/анонимизировать с сохранением расчётных значений либо документировать consent/retention. Удалять oracle до появления эквивалентной синтетической базы нельзя.

## 7. Репозиторий, deployment и CI как источник legacy

### 7.1. Несколько несовместимых operational truth

Канон из AGENTS.md и live systemd:

```text
DB 5433
API 8000
Frontend 3002
Sidecar 18091
```

Но repository artifacts говорят другое:

- root `docker-compose.yml`: DB 5432, sidecar 8001, старый frontend path/стек;
- `docker-compose.prod.yml`: API 8002, sidecar 8003, лишний Redis и устаревший frontend block;
- `scripts/deploy.sh` дважды проверяет API health и второй check называет sidecar, печатает 8001;
- `DEPLOYMENT_GUIDE.md` рекомендует ручной uvicorn на 8001, что прямо запрещено каноном;
- repo systemd artifact не соответствует реально используемому `solarsage-sidecar.service`;
- `grace/orchestrator/project.yml` всё ещё указывает Prefect, хотя проект объявляет Prefect удалённым.

Это operational legacy с высоким риском: новый инженер или automation может поднять второй API, неверный sidecar или проверить не тот процесс.

Решение: один machine-readable service manifest, из которого проверяются docs, compose, systemd templates и deploy smoke. Устаревшие файлы либо переписать, либо явно перенести в `docs/archive` и исключить из executable path.

### 7.2. CI не закрепляет текущий quality contract

- API tests зелёные, но Ruff production выдаёт 66 ошибок, mypy — 29 ошибок в 10 файлах;
- CI не делает Ruff/mypy обязательными, хотя проект декларирует guardrails;
- frontend workflows используют `npm install`, тогда как package manager проекта — pnpm;
- manual E2E workflow использует Python 3.11, отсутствующий `apps/api/requirements.txt`, запрещённый API port 8001 и не поднимает sidecar;
- visual workflow использует старые Node/actions/npm assumptions;
- `npm ci --dry-run` сейчас не разрешает dependency tree.

Нельзя просто включить все static gates одним PR: текущий долг заблокирует весь pipeline. Нужен baseline approach:

1. Канонизировать pnpm и Python environment.
2. Исправить workflows/порты.
3. Зафиксировать текущий static baseline.
4. Новые/изменённые файлы — zero new violations.
5. По модулям погашать baseline до полного strict gate.

### 7.3. Тесты сильные по количеству, но слабы в нескольких типах риска

Результаты:

```text
API tests from repository root: 1406 passed, 4 skipped
API documented cwd command: 1394 passed, 14 skipped, 2 failed
Sidecar: 201 passed
```

Два documented-command failures вызваны тем, что тесты жёстко ожидают repo-root relative paths. Это test harness bug, а не product regression.

Пробелы:

- большинство DB tests используют SQLite, поэтому не проверяют PostgreSQL `FOR UPDATE`, partial indexes, concurrency и некоторые JSON/date semantics;
- integration tests активно мокают sidecar/HTTP и не дают полноценного API→sidecar→Postgres lane;
- много тестов привязано к private methods, monkeypatch и source/AST shape, что повышает цену безопасного рефакторинга;
- нет обязательных security smoke для production CORS/router mounting;
- нет performance budgets на число DB/sidecar/LLM calls.

Нужны отдельные небольшие lanes, а не замена текущей unit-базы:

- PostgreSQL migration/concurrency tests;
- real local API→sidecar contract smoke;
- CORS/auth/public-surface security tests;
- request-budget tests для Today/Calendar;
- golden contract tests на product read model отдельно от internal evidence.

## 8. Рекомендуемый план рефакторинга

### Волна 0. Emergency security/config — 1–2 дня

1. Исправить production `APP_ENV` и CORS allowlist.
2. Добавить fail-closed production config validator.
3. Не монтировать debug/microcopy admin; закрыть metrics/extended health.
4. Запретить raw `user_id`/Telegram/entity IDs в логах, убрать auth `print`.
5. Ограничить `/_log` и geo либо временно закрыть auth/network policy.
6. Добавить deploy smoke на CORS и публичные routes.

В этой волне не начинать декомпозицию Today или sidecar: сначала убрать текущую внешнюю поверхность риска.

### Волна 1. Cost/reliability containment — 3–7 дней

1. Отключить или резко ограничить недельный LLM prefetch.
2. Batch access/cache для Calendar; не рассчитывать весь трёхмесячный диапазон синхронно.
3. Добавить Today cache singleflight/upsert recovery.
4. Ввести frontend auth singleflight и backend session cap/cleanup.
5. Исправить sidecar health calculation version.
6. Спроектировать DB-backed horary job и убрать внешний I/O из row lock.

### Волна 2. Today read model и LLM — 1–3 недели

1. Зафиксировать versioned product Today contract, содержащий только UI-необходимые поля.
2. Вынести full evidence в отдельный audit artifact.
3. Свести narrative к одному structured generation или двум bounded stages.
4. Ввести lifespan HTTP clients и typed provider adapters.
5. Разделить deterministic/narrative cache и degraded TTL.
6. Разбить Today orchestration на наблюдаемые stages без изменения продукта.

### Волна 3. Завершение V2 migration — после метрик parity

1. Вынести общие V1/V2 scoring primitives из private helpers.
2. Собирать divergence/cost/latency метрики на контролируемом окне.
3. Выключить dual-run по feature flag.
4. Сохранить короткий rollback window.
5. После окна удалить V1 selection path и старые cache identities.

### Волна 4. Sidecar modularization и contracts — 2–4 недели

1. Versioned `ChartSnapshot` contract с `planet.house`.
2. Shared calculation context без повторного natal/transit расчёта.
3. Technique handler registry вместо giant conditional builder.
4. Безопасная execution model для CPU-bound Swiss Ephemeris.
5. Stable error codes и единый version source.

### Волна 5. Controlled cleanup и repository canon

1. Удалить подтверждённый dead code/fixtures/artifacts.
2. Завершить checkin column migration.
3. Принять ADR по chat/payments/natal/microcopy.
4. Синтетизировать golden personal fixtures.
5. Канонизировать compose/systemd/deploy docs/CI/package lock.
6. Обновить stale known-bugs в AGENTS.md.

## 9. Acceptance gates

### Security

- evil Origin не получает `Access-Control-Allow-Origin` и credentials;
- production не стартует при `APP_ENV != production` или wildcard CORS;
- `/api/debug` и microcopy admin возвращают 404 в production;
- metrics/readiness доступны только разрешённому internal consumer;
- journal negative scan не находит raw `user_id`, Telegram IDs, cookie/token material;
- `/_log` и geo имеют auth/rate/body bounds.

### Performance/cost

- cold Today делает согласованное максимальное число LLM calls: цель 1, допустимый переходный максимум 2;
- один Today request не создаёт семь narrative jobs;
- Calendar выполняет O(1) access/cache queries на диапазон, а не O(days);
- p95 product Today payload укладывается в утверждённый бюджет, стартовая цель <100 KB;
- cache hit-rate, LLM calls/day, sidecar calls/request и generation latency доступны в обезличенных метриках.

### Reliability

- конкурентные одинаковые Today requests не дублируют generation и не дают unique 500;
- рестарт API не теряет horary job и не списывает credit дважды;
- active sessions имеют cap/rotation и cleanup;
- sidecar health остаётся responsive под расчётной нагрузкой;
- degraded LLM result не становится долгоживущим успешным cache entry.

### Architecture

- один canonical LLM implementation;
- один shared chart contract между API и sidecar;
- V2 не импортирует private V1 helpers;
- use-case владеет транзакцией, services не делают неожиданные commits;
- product read model не содержит полного internal evidence graph.

### Quality gates

- API pytest запускается одинаково из documented cwd и repo root;
- sidecar pytest green;
- Ruff/mypy baseline не растёт, затем доводится до zero;
- есть PostgreSQL concurrency lane;
- CI использует канонические Python/pnpm/ports и не запускает ручной API на 8001.

## 10. Команды и доказательства аудита

Ключевые проверки выполнялись read-only:

```bash
git status --short
rg --files apps/api apps/solarsage packages/py-contracts
rg '<imports/callers/commits/routes>' apps/api apps/solarsage
python -m pytest ...
python -m ruff check ...
python -m mypy ...
alembic heads
alembic current
systemctl show solarsage-api.service ...
curl -i -H 'Origin: https://evil.example' ...
curl /api/debug
curl /api/metrics
curl /api/health/extended
curl /api/admin/microcopy/misses
```

Production DB использовалась только для агрегатных `COUNT`, размеров JSON и распределения состояний. Ни одно персональное значение не включено в этот документ.

Статические результаты на проверенном commit:

| Проверка | Результат |
|---|---:|
| API Ruff, production `app` | 66 ошибок, 39 auto-fixable |
| API Ruff, app + tests | 172 ошибки |
| API mypy | 29 ошибок в 10 файлах |
| Sidecar Ruff, production + tests | 38 ошибок |
| Alembic | одна head/current: `0019` |

Pytest и Ruff также показывают deprecation warning Starlette TestClient/httpx integration. Это не срочный runtime defect, но dependency upgrade должен иметь отдельную совместимостную задачу.

## 11. Архитекторское заключение

Репозиторий не нуждается в «переписать backend заново». Нужна последовательная ликвидация переходных слоёв и опасных расхождений между кодом, runtime и операционным каноном.

Первый рефакторинг должен уменьшить риск и стоимость без изменения пользовательской семантики:

1. fail-closed production security;
2. ограничение фоновых и fan-out вычислений;
3. лёгкая versioned read model для Today;
4. надёжные job/transaction/session boundaries;
5. только затем удаление V1, LLM monolith и sidecar legacy.

Если начать с механического удаления файлов или большой декомпозиции `TodayService`, проект сохранит самые опасные проблемы — публичный fail-open CORS, PII logs и недолговечные jobs — но одновременно потеряет rollback/parity опоры. Поэтому предложенный порядок является частью архитектурного решения, а не только удобной очередью задач.
