# ТЗ: аудит и доработка structured logging / log-driven development

Дата: 2026-06-10
Репозиторий: `basilivanov/solarsage-astro`
Статус: draft → ready for GRACE slicing

## 1. Короткий вердикт

Сейчас в проекте **не логируется “каждый чих”**.

В репозитории уже есть сильный observability canon (`grace/canon/observability.xml`) и волны `W-CANON-LOG`, `W-1.6`, `W-1.7`, но фактическая реализация частичная и разъехалась с каноном:

- есть минимум две фронтовые реализации логгера: `lib/logger.ts` и `lib/log/index.ts`;
- backend JSON formatter не совпадает с каноническим envelope;
- нет обязательных `slice`, `module`, `block` в каждом log event;
- `correlation_id` кладётся в `request.state`, но не прокидывается автоматически в каждый backend log через contextvars;
- много ключевых бизнес-операций явно имеют `emitted_logs: none`;
- часть логов — ad-hoc строковые `logger.info(...)` / `logger.error(...)` без event id, payload schema, slice/module/block;
- redactor неполный относительно канона;
- frontend fetch telemetry пишет сырой URL/кусок body в `console.error`, что опасно для PII;
- CI-гейты на события/envelope/redaction фактически не закрывают drift.

Цель доработки: сделать настоящий log-driven development: по логам можно восстановить каждый пользовательский сценарий, каждую мутацию, каждый внешний вызов, каждый cache hit/miss, каждый background task stage и каждую ошибку.

---

## 2. Внешние ориентиры по structured logging

Использовать текущий canon проекта как основной источник истины, но при реализации сверяться с общими практиками:

- OpenTelemetry Logs Data Model: лог должен иметь стабильные top-level поля, event name, severity, resource/scope/attributes и trace/correlation контекст.
- Python logging поддерживает contextual logging через `LoggerAdapter` / `extra`, но для async web-приложения удобнее централизованно bind-ить request context.
- Для FastAPI/asyncio подход с contextvars подходит, но нужно учитывать, что sync/async контексты могут быть изолированы; поэтому middleware и все async task entrypoints должны явно bind/reset контекст.

---

## 3. Обязательный envelope после доработки

Каждая строка лога backend/frontend/sidecar/worker должна быть валидным JSON объектом.

Обязательные поля:

```json
{
  "ts": "2026-06-10T20:00:00.000Z",
  "level": "info|warn|error|fatal|debug",
  "env": "dev|test|staging|prod",
  "service": "api|web|solarsage|worker",
  "service_version": "git_sha_or_semver",
  "slice": "W-HORARY|W-NATAL-FULL|W-6.1|...",
  "module": "M-API-HORARY|M-PROFILE.service|...",
  "block": "ROUTE_CREATE|PROFILE_WRITE|GENERATION_TASK|...",
  "event": "horary.question_created",
  "correlation_id": "uuid",
  "msg": "short human message",
  "payload": {},
  "duration_ms": 123
}
```

Опциональные поля:

```json
{
  "session_id": "uuid",
  "user_id_hash": "12_hex_chars",
  "error": {
    "kind": "ValueError",
    "message": "redacted/safe message",
    "stack": "redacted stack in non-prod or gated prod"
  },
  "http": {
    "method": "POST",
    "route": "/api/horary/questions",
    "status": 201,
    "ip_hash": "optional"
  }
}
```

Правила:

- `slice`, `module`, `block` обязательны для всех application/business logs.
- Для system-level logs (`system.startup`, `system.request`, `system.error`) `module` и `block` тоже должны быть заполнены техническими значениями, например `M-API-BOOT` / `APP_CONSTRUCTION`.
- Raw `user_id`, `tg_user_id`, `email`, birth data, lat/lon/tz, payment ids, tokens, cookies, raw URL query/body — запрещены.
- Вместо raw user identity использовать `user_id_hash`.
- Payload должен содержать **только факты о событии**, без пользовательских значений. Для profile update — только `changed_fields`, но не новые значения.

---

## 4. Нужно сначала расширить canon

Текущий `grace/canon/observability.xml` уже задаёт envelope и closed event registry, но в нём нет обязательных `slice`, `module`, `block`. Пользовательское требование: “везде должен быть указан slice, модуль, start and block”.

### Задача 4.1 — canon patch

Создать micro patch:

`W-CANON-LOG-EXT-SLICE-MODULE-BLOCK`

Изменения:

1. В `grace/canon/observability.xml` добавить top-level поля:
   - `slice` — GRACE wave/slice id;
   - `module` — module contract id;
   - `block` — semantic block id from `START_BLOCK` / `GRACE_ANCHORS`;
   - `phase` — optional, если есть phase-level orchestration;
   - `operation_id` — optional для multi-step background jobs.
2. Уточнить event lifecycle convention:
   - `*.started` / `*.succeeded` / `*.failed` для крупных операций;
   - для коротких операций можно один past-tense event, но route-level middleware всё равно пишет `system.request`.
3. Запретить `emitted_logs: none` в function contracts для impure functions. Разрешить только:
   - `emitted_logs: n/a (pure)` для чистых helper-функций;
   - `emitted_logs: inherited from caller` для маленьких приватных функций без собственного side effect.
4. Добавить horary/natal/payment/chat/checkin/geo events в registry.

---

## 5. Найденные проблемы и задачи

### 5.1 Frontend: две реализации логгера

Файлы:

- `lib/logger.ts`
- `lib/log/index.ts`
- `lib/log/shipper.ts`

Проблема:

- `lib/logger.ts` шипит в `/api/logs`, а новый shipper — в `/api/_log`.
- Envelope в обоих случаях не совпадает с canon.
- Нет typed event registry.
- Нет `slice/module/block`.
- Нет гарантированного `session_id` / `user_id_hash`.

Задачи:

1. Удалить или заdeprecated-ить `lib/logger.ts`.
2. Оставить один публичный frontend logging API:
   - `logEvent(event, payload, meta)`;
   - `logStart(event, payload, meta)`;
   - `logSuccess(event, payload, meta, startedAt)`;
   - `logFailure(event, error, payload, meta, startedAt)`;
   - `withLogBlock({slice,module,block,event}, fn)`.
3. Все frontend events должны идти через `lib/log/index.ts`.
4. Все `console.log/error/warn` в app/components/hooks заменить на logger, кроме тестов и dev-only fenced debug code.
5. `lib/log/shipper.ts` обновить под canon envelope.
6. `/api/logs` полностью убрать, оставить только `/api/_log`.

Acceptance:

- `grep -R "@/lib/logger\|from .*lib/logger\|/api/logs"` не находит production call sites.
- `grep -R "console\." app components hooks lib` не находит production logs вне `lib/log` и test/dev exceptions.
- Unit test проверяет, что frontend envelope содержит `slice/module/block/event/correlation_id`.

---

### 5.2 Backend logger: envelope не канонический

Файл:

- `apps/api/app/core/logging.py`

Проблема:

Сейчас formatter пишет:

- `timestamp`
- `level`
- `message`
- `module`
- `function`
- `line`
- optional `correlation_id`
- optional `extra`

Но canon требует другой envelope и closed event registry.

Задачи:

1. Переписать logging spine на единый `log_event(...)` API.
2. Добавить contextvars:
   - `correlation_id_var`
   - `user_id_hash_var`
   - `http_route_var`
   - `slice_var`
   - `module_var`
   - `block_var`
   - `operation_id_var`
3. Middleware должен bind/reset контекст на каждый request.
4. Background task entrypoint должен bind свой контекст вручную.
5. JSON formatter должен брать contextvars автоматически.
6. Все unknown extra fields дропать или класть только в `payload` после redaction.
7. Настроить logger без duplicate handlers:
   - `logger.handlers.clear()` при setup;
   - `logger.propagate = False`;
   - root/uvicorn logs привести к одному формату или явно исключить из gate.

Acceptance:

- Любой `logger.info/error` из request scope содержит `correlation_id` без ручного проброса.
- Любой app log содержит `slice/module/block/event`.
- CI проверяет JSON parse и schema validation для backend logs.

---

### 5.3 Correlation middleware: есть request.state, но нет автопрокидывания в logs

Файл:

- `apps/api/app/middleware/correlation.py`

Проблема:

Middleware создаёт/читает `X-Correlation-Id` и кладёт в `request.state.correlation_id`, но logger сам его не подтягивает. Итог: call sites должны передавать correlation вручную, а многие не передают.

Задачи:

1. В middleware делать:
   - `clear_log_context()`;
   - `bind_log_context(correlation_id=..., http_route=..., method=...)`;
   - после response добавить status/duration через `system.request`.
2. Для uncaught exception middleware/global handler должен писать `system.error`.
3. Для FastAPI background tasks / `asyncio.create_task` передавать `correlation_id` явно или создавать новый `operation_id`.

Acceptance:

- E2E request к `/api/profile` даёт минимум `system.request` с route/status/duration/correlation_id.
- Лог из вложенного service layer содержит тот же `correlation_id`.

---

### 5.4 `/api/_log`: intake schema не совпадает с canon

Файлы:

- `apps/api/app/api/_log.py`
- `apps/api/app/services/log_intake.py`

Проблемы:

- Contract говорит auth required, код принимает optional auth.
- Schema принимает только `timestamp/level/message/correlation_id/extra`.
- Validation проверяет только три поля.
- Frontend log кладётся в backend logger как `[FRONTEND] {message}` и nested `frontend_log`, а не как полноценный canon event.

Задачи:

1. Решить policy: auth optional или required. Если optional — поправить contract и добавить anonymous session handling.
2. Принимать только canon `LogEnvelopeV1`.
3. Валидировать:
   - required fields;
   - enum level/service/env;
   - event из registry;
   - payload schema по event;
   - route templating, не raw URL.
4. Redact before stdout.
5. Нельзя превращать frontend event в строку `[FRONTEND] ...`; нужно emit exactly same envelope with `service="web"`.

Acceptance:

- Invalid envelope rejected with count and structured warning.
- Valid frontend event appears in stdout as canon envelope, not nested legacy object.

---

### 5.5 Redactor неполный

Файл:

- `apps/api/app/core/redactor.py`

Проблема:

Список PII keys сильно меньше canon. Нет pattern-based redaction, хотя canon требует email/jwt/bearer/ip/tg-id regex. Сейчас, например, `email`, `phone`, `first_name`, `lat`, `lon`, `tz`, `payment_id`, `cookie`, `authorization`, `user_agent` не покрыты полностью.

Задачи:

1. Сгенерировать redaction keys/patterns из `grace/canon/observability.xml` или держать вручную с drift test.
2. Добавить recursive key redaction.
3. Добавить string pattern redaction.
4. Добавить allow-list.
5. Добавить tests-canaries для каждого ключа и паттерна.
6. Прогонять redactor и на frontend перед ship, и на backend intake/stdout.

Acceptance:

- Для каждого redact-key из canon есть unit test.
- Сентинелы `secret@example.com`, `Bearer abc`, `tg_user_id=123456`, `127.0.0.1` не появляются в serialized logs.

---

## 6. Retrofit по бизнес-модулям

### 6.1 Auth

Файл:

- `apps/api/app/api/auth.py`

Проблемы:

- Есть TODO на `auth.tg_login_failed`.
- Есть TODO на `auth.tg_login_succeeded`.
- Есть TODO на `auth.logout`.
- Есть TODO на `auth.dev_login`.
- В dev login используются raw test user values, логи должны быть безопасными.

Нужно добавить events:

- `auth.tg_login_started`
- `auth.tg_login_failed` payload: `{reason}`
- `auth.tg_login_succeeded` payload: `{is_new_user}`
- `auth.logout` payload: `{had_cookie, revoked}`
- `auth.dev_login_blocked`
- `auth.dev_login_succeeded`

Все события:

- `slice`: `W-1.2` или текущий auth slice;
- `module`: `M-AUTH-TG.api`;
- `block`: `ROUTE_AUTH_TG` / `ROUTE_AUTH_LOGOUT` / `ROUTE_AUTH_DEV`.

---

### 6.2 Profile

Файлы:

- `apps/api/app/api/profile.py`
- `apps/api/app/services/profile_service.py`
- `hooks/use-profile.ts`
- `lib/profile.ts`

Проблемы:

- Contract прямо говорит `no audit log (W-1.6 retrofit)`.
- `PUT /api/profile` имеет TODO `profile.updated`.
- `mark_profile_dirty` имеет TODO log event.
- Client localStorage profile save/load никак не логируются.

Нужно добавить events:

Backend:

- `profile.viewed`
- `profile.update_started`
- `profile.updated` payload: `{changed_fields, became_onboarded}`
- `profile.update_failed` payload: `{reason}`
- `profile.cache_invalidation_requested`
- `profile.cache_invalidated`
- `profile.lazy_created`

Frontend:

- `profile.screen_viewed`
- `profile.form_changed` payload: `{field}` без значения
- `profile.form_submit_started`
- `profile.form_submit_succeeded`
- `profile.form_submit_failed`
- `profile.local_saved` только если legacy local profile всё ещё используется

Запрещено логировать:

- birthday;
- birth_time;
- birth_city;
- lat/lon/tz;
- first_name value;
- gender value, если это считается sensitive для продукта; минимум можно логировать только field name.

---

### 6.3 Horary

Файлы:

- `apps/api/app/api/horary.py`
- `apps/api/app/services/horary_service.py`
- `apps/api/app/services/horary_credit_service.py`
- `components/readings/horary/*`
- `lib/api/horary.ts`

Проблемы:

- В route contracts несколько раз `emitted_logs: none`.
- Создание вопроса тратит credit и запускает background generation без structured logs.
- Credit ledger мутирует баланс без logs.
- Background generator пишет ad-hoc строки и raw ids.
- Ошибки stage/failure пишутся, но нет полноценного lifecycle trace.

Нужно добавить events:

Routes:

- `horary.quota_viewed`
- `horary.questions_list_viewed`
- `horary.question_viewed`
- `horary.question_create_started`
- `horary.question_created`
- `horary.question_reused_idempotent`
- `horary.question_create_failed`
- `horary.idempotency_conflict`
- `horary.no_credits`

Credit ledger:

- `horary.weekly_credit_resolved`
- `horary.weekly_credit_created`
- `horary.balance_computed`
- `horary.credit_selected`
- `horary.credit_spent`
- `horary.credit_refunded`
- `horary.credit_not_refundable`

Generation task:

- `horary.generation_enqueued`
- `horary.generation_started`
- `horary.profile_loaded`
- `horary.sidecar_natal_started`
- `horary.sidecar_natal_succeeded`
- `horary.sidecar_transits_started`
- `horary.sidecar_transits_succeeded`
- `horary.normalization_succeeded`
- `horary.engine_analyzed`
- `horary.llm_requested`
- `horary.llm_response_validated`
- `horary.answer_saved`
- `horary.generation_succeeded`
- `horary.generation_failed`
- `horary.rollback_update_failed`
- `horary.ttl_expired_failed`

Payload policy:

- `question_id` можно логировать только как `question_id_hash` или internal UUID если policy допускает non-PII; лучше hash.
- `question.text` запрещён.
- `category` можно логировать, если enum безопасный.
- `failure_stage`, `public_error_code`, `status` можно.
- `credit.source` можно.
- Raw credit id/payment id не логировать.

---

### 6.4 Natal

Файлы:

- `apps/api/app/api/natal.py`
- `apps/api/app/services/natal_service.py`
- `apps/api/app/services/natal_context_service.py`
- `apps/api/app/services/natal_report_service.py`
- `apps/api/app/services/llm_service.py`
- `components/natal/*` / readings UI если есть

Проблемы:

- Preview/generate/report routes не логируют normal path.
- Есть error logs как строки, но нет `slice/module/block/event`.
- `NatalContextService` логирует cache build/invalidation строками с raw ids.
- Нет явного cache hit/miss trace.
- Нет report lifecycle trace в API layer.

Нужно добавить events:

- `natal.preview_requested`
- `natal.preview_succeeded`
- `natal.preview_failed`
- `natal.context_requested`
- `natal.context_cache_hit`
- `natal.context_cache_miss`
- `natal.context_build_started`
- `natal.sidecar_called`
- `natal.sidecar_failed`
- `natal.sidecar_response_validated`
- `natal.normalization_succeeded`
- `natal.scoring_succeeded`
- `natal.context_cached`
- `natal.context_invalidated`
- `natal.report_generation_requested`
- `natal.report_generation_reused`
- `natal.report_generation_started`
- `natal.report_generation_succeeded`
- `natal.report_generation_failed`
- `natal.report_viewed`
- `natal.report_section_viewed`

Payload policy:

- `profile_hash` можно, если он не обратим и не содержит raw birth data.
- `birth_*`, `lat`, `lon`, `tz`, `first_name` запрещены.
- `cache_status`, `duration_ms`, `prompt_version`, `schema_version`, `section_id` можно.

---

### 6.5 Payment / access / subscription

Файлы:

- `apps/api/app/api/payment.py`
- `apps/api/app/services/payment_service.py`
- `apps/api/app/services/access_service.py`
- `apps/api/app/services/chat_quota_service.py`

Проблемы:

- Payment intent creation не логируется.
- Webhook receive/status update не логируется.
- Subscription grant и chat quota increase не логируются.
- Payment ids нельзя писать raw.

Нужно добавить events:

- `payment.intent_create_started`
- `payment.intent_created`
- `payment.intent_create_failed`
- `payment.webhook_received`
- `payment.status_updated`
- `payment.succeeded`
- `payment.failed`
- `access.subscription_grant_started`
- `access.subscription_granted`
- `chat.quota_increased`

Payload policy:

- `amount`, `currency`, `provider`, `status` можно.
- `payment_id`, provider payment id, receipt — hash/redact.
- `description` не логировать или redacted/truncated safe enum only.

---

### 6.6 Frontend UI / fetch / onboarding

Файлы/зоны:

- `public/telemetry/fetch-interceptor.js`
- `components/onboarding/*`
- `components/profile/*`
- `components/readings/*`
- `hooks/use-telegram-auth.ts`
- `lib/api/*`

Проблемы:

- Fetch interceptor пишет raw URL и response body snippet в console.
- UI actions логируются точечно, но не системно.
- Нет стандарта для user action → fetch → backend correlation.

Задачи:

1. Убрать или переписать `public/telemetry/fetch-interceptor.js`.
2. Сделать `apiFetch()` wrapper:
   - добавляет/создаёт `correlation_id`;
   - пишет `ui.fetch_started`;
   - пишет `ui.fetch_succeeded` / `ui.fetch_failed`;
   - читает response header `X-Correlation-Id`;
   - route is templated, not raw URL.
3. Сделать `useLoggedAction({slice,module,block,event})` для кнопок/forms.
4. Onboarding/Profile/Horary/Natal actions должны иметь start/success/failure logs.

---

## 7. Общие правила логирования

### 7.1 Routes

Каждый public route обязан иметь минимум:

- start event или `system.request` из middleware;
- success event для бизнес-операции;
- failure event с safe reason/stage;
- duration_ms.

### 7.2 DB mutations

Каждая DB mutation обязана логировать:

- operation started;
- rows affected / entity type;
- success/failure;
- no raw PII values.

### 7.3 External calls

Каждый внешний вызов обязан логировать:

- started;
- succeeded with duration/status/cache_status;
- failed with duration/error kind/stage.

Касается:

- SolarSage sidecar;
- LLM provider;
- payment provider;
- Telegram auth/payment/webhook;
- geo/city autocomplete provider.

### 7.4 Cache

Каждый cache path обязан логировать:

- requested;
- hit/miss/bypass;
- invalidated;
- rebuilt;
- stale/expired.

### 7.5 Background tasks

Каждая background task обязана логировать:

- enqueued;
- started;
- every stage boundary;
- success;
- failure;
- rollback/compensation result.

### 7.6 Pure helpers

Pure helper functions не обязаны логировать. Но contract должен писать:

`emitted_logs: n/a (pure)`

А не `emitted_logs: none`.

---

## 8. Event registry additions

Добавить в canon registry минимум следующие namespaces:

```text
auth.*
profile.*
onboarding.*
horary.*
natal.*
payment.*
access.*
chat.*
geo.*
ui.*
system.*
sidecar.*
llm.*
scoring.*
```

Для каждого event в XML указать:

- owner slice;
- allowed payload fields;
- required payload fields;
- privacy notes;
- examples.

---

## 9. CI / guardrails

Добавить новые guardrails:

### Gate A — no legacy logging

Fail если production code содержит:

```bash
grep -R "console\.\|print(" app components hooks lib apps/api/app \
  --exclude-dir=node_modules --exclude='*.test.*'
```

Исключения только через allowlist.

### Gate B — no raw Python logger in app services

Fail если не-core файлы создают ad-hoc logger:

```bash
grep -R "logging.getLogger(__name__)" apps/api/app \
  --exclude='apps/api/app/core/logging.py'
```

Нужно заменить на project logging API.

### Gate C — no `emitted_logs: none` for impure functions

Fail если:

```bash
grep -R "emitted_logs: none" apps/api/app
```

Разрешить только `emitted_logs: n/a (pure)` или `inherited from caller`.

### Gate D — canonical envelope validation

Тестовый прогон должен валидировать, что каждая app log line:

- JSON parseable;
- соответствует schema;
- содержит `slice/module/block/event/correlation_id`;
- проходит redaction canary.

### Gate E — event registry drift

Generated artifacts must match XML:

- `apps/api/app/core/logging_events.py`
- `lib/log/events.gen.ts`

CI fails if generated files differ.

---

## 10. Тесты

### Backend unit tests

- `test_log_envelope_shape.py`
- `test_log_contextvars.py`
- `test_redactor_canaries.py`
- `test_event_registry_generated.py`
- `test_log_block_context_manager.py`

### Backend integration tests

- Auth login success/failure emits expected events.
- Profile PUT emits changed_fields and cache invalidation.
- Horary create emits credit spend + generation enqueue.
- Horary generation fake success emits full stage chain.
- Horary generation fake failure emits failure + refund.
- Natal preview cache hit/miss emits expected events.
- Payment webhook succeeded emits payment/access/chat quota events.

### Frontend unit tests

- Logger creates canonical envelope.
- `apiFetch` attaches `X-Correlation-Id` and logs started/succeeded/failed.
- Redactor removes PII before ship.
- UI action hook emits start/success/failure.

### E2E tests

- One happy path scenario: auth → profile edit → natal preview → horary ask.
- Assert log sink contains correlated chain by one `correlation_id` where applicable.

---

## 11. Suggested implementation order

### P0 — canon + spine

1. Canon patch for `slice/module/block`.
2. Generate event types.
3. Backend `log_event` + contextvars.
4. Redactor parity with canon.
5. Backend envelope tests.

### P1 — frontend consolidation

1. Remove/merge `lib/logger.ts`.
2. Canon `lib/log` envelope.
3. `apiFetch` wrapper.
4. Replace `public/telemetry/fetch-interceptor.js`.
5. Frontend tests.

### P2 — high-value business retrofit

1. Auth.
2. Profile.
3. Horary route/service/credit/generator.
4. Natal route/context/report.
5. Payment/access/chat quota.

### P3 — full grep cleanup

1. Remove all `emitted_logs: none` from impure functions.
2. Replace raw `logger.info/error` strings.
3. Add guardrails to `scripts/guardrails.sh`.
4. Make guardrails mandatory in `pnpm guardrails:strict`.

---

## 12. Acceptance checklist

- [ ] В `grace/canon/observability.xml` добавлены `slice/module/block`.
- [ ] В registry добавлены horary/natal/payment/chat/checkin/geo/frontend events.
- [ ] Есть единый backend logging API.
- [ ] Есть единый frontend logging API.
- [ ] `lib/logger.ts` удалён или не используется.
- [ ] `/api/logs` не используется.
- [ ] `/api/_log` принимает canon envelope.
- [ ] Correlation id автоматически попадает во все backend logs.
- [ ] Background tasks имеют operation/correlation context.
- [ ] Redactor покрывает canon keys + patterns.
- [ ] Нет raw `console.*` в production code вне logger.
- [ ] Нет raw `logging.getLogger(__name__)` в feature services.
- [ ] Нет `emitted_logs: none` для impure functions.
- [ ] Profile PUT логирует changed_fields.
- [ ] Horary create/generation/refund логируются stage-by-stage.
- [ ] Natal preview/context/report логируются cache/stage-by-stage.
- [ ] Payment webhook/subscription/quota логируются.
- [ ] CI валидирует envelope, event registry, redaction canaries.

---

## 13. Definition of done

Фича считается закрытой только когда по логам можно ответить на вопросы:

1. Что пользователь нажал?
2. Какой frontend action стартовал?
3. Какой backend route был вызван?
4. Какой slice/module/block обработал действие?
5. Какие DB/cache/external-call стадии прошли?
6. Где и почему операция упала?
7. Был ли refund/rollback/compensation?
8. Какие поля профиля изменились без раскрытия значений?
9. Какой `correlation_id` связывает frontend/backend/background task?
10. Прошли ли logs redaction и schema validation?

Если на любой из этих вопросов нельзя ответить из логов — log-driven development ещё не достигнут.
