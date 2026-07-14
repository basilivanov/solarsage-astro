# Архитектурное ревью R3: доказанные bypass-ы correlation/logging и упрощение CORS

- Дата: 2026-07-14
- Ветка: `fix/backend-p0-security-hardening`
- Статус: **REWORK REQUIRED — P0 ещё не закрыт**
- Основание: независимые исполняемые probes после заявленных `1441 passed, 4 skipped`.

Live `.env`, nginx, systemd, restart, commit и push по-прежнему запрещены. Замороженные untracked paths не трогать.

## 1. Доказанные дефекты текущей реализации

### R3-B1. `/api/_log` сохраняет caller-controlled correlation UUID raw

Независимый direct-service probe текущего `LogIntakeService` дал:

```text
intake_result {'accepted': 1, 'rejected': 0}
intake_raw_leaked True
intake_corr 123e4567-e89b-12d3-a456-426614174000
```

Причина в `apps/api/app/services/log_intake.py`:

- в bounded unsafe ветке импортируется `hash_log_identifier`, но результат не присваивается обратно в envelope;
- строки примерно 110–154 содержат большой оставшийся поток временных рассуждений/отладки;
- затем `redact_dict()` сохраняет raw `correlation_id`, потому что ключ unconditional allow-listed.

Это прямой обход SEC-03 и R2-B3.

### R3-B2. Прямой `bind_log_context(correlation_id=raw_uuid)` также обходит redactor

Независимый probe:

```text
bound_raw_leaked True
bound_corr 123e4567-e89b-12d3-a456-426614174000
```

`bind_log_context()` принимает correlation без проверки, а full-envelope redactor сохраняет этот ключ как allow-key. Middleware-нормализация не защищает другие callers.

### R3-B3. `log_event()` нарушает собственный never-break контракт

При synthetic `ValueError` из redactor:

```text
logger_raised ValueError
```

Причина — новый код повторно бросает любой `ValueError`, `AssertionError` или `RuntimeError` из operational logging path. Это слишком широкий class-based rethrow: такие ошибки могут возникнуть в redactor/envelope/emit и уронить пользовательский flow.

Registry validation неизвестного event может по-прежнему fail-fast до operational `try`, как было задумано. Но после успешной registry validation любые внутренние logging failures должны swallowing/handled и не ломать бизнес-операцию.

### R3-B4. Startup errors всё ещё включают полное значение config

Независимый probe production-like policy:

```text
startup_error CORS origin 'http://secret-bearing-host.example' must use https in deployed environment
```

Текущий `runtime_security.py` также включает raw `APP_ENV`, `APP_DOMAIN`, origin/hostname и expected origin в нескольких exception messages. Это не соответствует исходному ТЗ: exception должен содержать только key/index/reason, без значения config.

### R3-B5. AST guardrail пропускает наиболее обычный raw ORM identifier

Независимый probe `_check_expr_for_forbidden_vars()`:

```text
user_id      -> violation
question.id  -> no violation
credit.id    -> no violation
report.id    -> no violation
question_id  -> violation
```

Исходное ТЗ явно требовало ловить `credit.id`, `thread.id`, `report.id` и аналоги внутри `log_event`.

### R3-B6. Самописный CORS не нужен и потерял стандартную семантику

Текущий `SafeCORSMiddleware`:

- дублирует security-sensitive код Starlette;
- не выставляет `Vary: Origin` для ответа, зависящего от Origin;
- всегда отвечает `Access-Control-Allow-Headers: *`, не отражая стандартную preflight-семантику;
- не выставляет стандартный `Access-Control-Max-Age`;
- увеличил composition root примерно на 90 строк самописного protocol-кода.

Исполняемый probe подтвердил, что разрешённый GET/preflight работает, evil origin не получает ACAO, но `Vary` отсутствует. Отдельный probe со штатным `CORSMiddleware` подтвердил корректные exact-origin, preflight и `Vary: Origin`.

Наличие `Access-Control-Allow-Credentials: true` без совпадающего `Access-Control-Allow-Origin` у штатного Starlette middleware само по себе не даёт браузеру доступ: browser authorization определяется совпадающим ACAO. Поэтому прежнее R2-требование «обязательно убрать ACAC и для denied origin» было избыточным. Security acceptance здесь: denied origin никогда не получает совпадающий ACAO и никогда не получает wildcard.

## 2. Обязательная архитектура correlation identity

Сделать один центральный контракт, используемый всеми путями. Не дублировать regex/UUID/HMAC логику в middleware и intake service.

### 2.1. `apps/api/app/core/log_identity.py`

Добавить публичные helpers с GRACE contracts:

```python
OPAQUE_LOG_ID_PATTERN = re.compile(r"^h1_[0-9a-f]{24}$")

def new_correlation_id() -> str:
    ...

def normalize_correlation_id(raw: object | None) -> str:
    ...
```

Точный invariant:

1. Результат **всегда** соответствует `^h1_[0-9a-f]{24}$`.
2. `raw is None`, empty/whitespace, oversized (>100 chars) или содержит control/non-printable characters:
   - не хранить и не хешировать caller value;
   - сгенерировать random UUID внутри процесса;
   - вернуть HMAC через `hash_log_identifier("correlation", generated_uuid)`.
3. Уже валидный `h1_[0-9a-f]{24}` сохранить byte-for-byte.
4. Любое другое bounded printable caller value вернуть только как `hash_log_identifier("correlation", raw)`.
5. Raw input не включать в exception text/logs.
6. Deployed short/missing salt остаётся fail-closed; local/test fallback остаётся допустимым.

Почему generated correlation также должен быть `h1_`, а не raw UUID: тогда `bind_log_context` может строго принимать только один opaque формат и raw DB UUID не сможет маскироваться под server correlation ID.

### 2.2. `apps/api/app/middleware/correlation.py`

- удалить локальные `re`/`uuid` ветки нормализации;
- вызвать только `normalize_correlation_id(request.headers.get(...))`;
- один и тот же opaque результат использовать в:
  - `request.state.correlation_id`;
  - bound log context;
  - `X-Correlation-Id` response header;
  - emitted request/error event;
- raw header не должен встречаться ни в response, ни в capture `_emit`;
- oversized/control header даёт новый opaque `h1_...`, не raw UUID.

### 2.3. `apps/api/app/core/logging.py`

- `bind_log_context(correlation_id=...)` обязан defense-in-depth прогонять non-empty value через `normalize_correlation_id()`;
- `build_envelope()` fallback correlation должен создаваться через `new_correlation_id()`, а не невалидную строку `h1_fallback_correlation_id_value`;
- `user_id_hash` strict validation сохранить через общий compiled pattern/fullmatch;
- `build_envelope()` и emitted envelope всегда имеют валидный opaque correlation ID.

### 2.4. `apps/api/app/services/log_intake.py`

- удалить весь временный debug/reasoning comment block;
- не мутировать caller dict хаотично: допустимо сделать shallow copy envelope;
- до redaction обязательно присвоить:

```python
normalized["correlation_id"] = normalize_correlation_id(
    normalized.get("correlation_id")
)
```

- затем central redactor и `_emit`;
- direct service path и HTTP `/api/_log` должны иметь одинаковое поведение;
- не добавлять test-runner/env bypass.

### 2.5. `apps/api/app/core/redactor.py`

`correlation_id` не должен быть unconditional `ALLOW_KEYS`.

Обрабатывать его раньше общего allow-list:

- valid `h1_[0-9a-f]{24}` сохранить;
- всё остальное заменить на `[redacted-identifier]`;
- `operation_id`/`packet_id` оставить по текущему контракту, если они не являются raw DB/session IDs.

Это defense-in-depth: даже если новый caller забудет helper, redactor не выпустит raw correlation.

## 3. Восстановить never-break logging policy

В `apps/api/app/core/logging.py`:

1. Closed registry validation неизвестного event оставить до operational `try`; этот programmer error может давать `ValueError`.
2. После validation убрать class-based rethrow:

```python
if isinstance(e, (ValueError, AssertionError, RuntimeError)):
    raise
```

3. Любая ошибка `build_envelope`, redactor или `_emit` не должна выйти из `log_event()`.
4. Fallback emission не должна включать raw exception string/input.
5. Если fallback `_emit` тоже упал, молча завершить logging call.

Regression tests:

- monkeypatch `redact_dict` -> `ValueError`: бизнес-вызов `log_event(valid_event)` не бросает;
- monkeypatch `_emit` -> `RuntimeError`: вызов не бросает;
- unknown event по-прежнему rejected programmer error;
- deployed short salt проверяется на уровне `hash_log_identifier`/startup policy, а не через расширенный rethrow любого logging exception.

## 4. Safe startup exception text

В `runtime_security.py` все validation errors привести к safe code-style messages. Примеры допустимого формата:

```text
APP_ENV:invalid
APP_ENV:empty
APP_DOMAIN:empty-deployed
APP_DOMAIN:loopback-deployed
APP_DOMAIN:invalid-format
CORS_ALLOWED_ORIGINS:empty-deployed
origin[0]:missing-scheme-or-netloc
origin[0]:userinfo-forbidden
origin[0]:http-forbidden-deployed
origin[0]:loopback-forbidden-deployed
CORS_ALLOWED_ORIGINS:own-origin-missing
DEV_MODE:true-deployed
SESSION_COOKIE_SECURE:false-deployed
TELEGRAM_BOT_TOKEN:empty-deployed
GRACE_USER_SALT:too-short-deployed
DATABASE_URL:sqlite-deployed
```

Нельзя включать raw `settings.app_env`, domain, origin, hostname, token, salt или DSN.

Добавить parametrized canary test: в каждое invalid field положить уникальный marker вроде `SECRET_CANARY_...`; после exception marker отсутствует в `str(exc)`.

## 5. Вернуть штатный CORS middleware

В `apps/api/app/main.py`:

- полностью удалить `SafeCORSMiddleware`;
- использовать `from fastapi.middleware.cors import CORSMiddleware`;
- wiring:

```python
application.add_middleware(
    CORSMiddleware,
    allow_origins=list(policy.cors_allowed_origins),
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)
```

- app factory и conditional internal routes сохранить;
- module contract/map снова назвать `CORSMiddleware`, не `SafeCORSMiddleware`;
- не писать собственный CORS protocol implementation.

CORS tests для valid staging/production app:

- allowed preflight/GET: exact ACAO, credentials true;
- allowed response имеет `Vary: Origin`;
- evil preflight/GET: нет `Access-Control-Allow-Origin`;
- нигде нет `Access-Control-Allow-Origin: *`;
- отсутствие Origin не добавляет ACAO/wildcard;
- не требовать отсутствия ACAC у denied origin отдельно от ACAO: без matching ACAO браузер не разрешает credentialed read.

## 6. Закрыть `.id` bypass в AST guardrail

В `scripts/check_logging_guardrails.py` внутри аргументов `log_event` ловить как минимум:

```python
user.id
session.id
question.id
credit.id
thread.id
message.id
report.id
profile.id
natal_context.id
```

Не запрещать любой `.id` во всём репозитории. Проверка действует только внутри `payload`/`error`/`http`/`msg` конкретного `log_event` и определяет entity base name/attribute chain.

Обязательные self-tests:

- unsafe `payload={"actor": credit.id}`;
- unsafe `msg=f"question {question.id}"`;
- unsafe nested `error={"context": {"actor": report.id}}`;
- safe `payload={"credit_id_hash": hash_log_identifier("credit", credit.id)}` не должен падать из-за `.id`, потому что raw value находится только внутри одобренного hash helper call;
- safe prepared variable `credit_id_hash` остаётся допустимым.

Важно: текущий walker не должен ошибочно флагать argument внутри самого разрешённого `hash_log_identifier(...)`; нужно распознавать и не заходить в raw argument одобренного helper call для соответствующего `*_id_hash`.

## 7. Усилить доказательность tests

### `apps/api/tests/test_logging_privacy.py`

- `test_correlation_id_normalization` должен проверять не только response header, но и captured emitted event/context:
  - raw UUID отсутствует;
  - bounded arbitrary/email отсутствует;
  - returned correlation совпадает с logged correlation;
  - oversized/control -> новый valid `h1_...`;
- direct `bind_log_context(raw_uuid)` -> `build_envelope()` и `log_event()` не содержат raw;
- invalid raw `user_id_hash` проверить и в `build_envelope`, и в emitted output;
- очистка context обязательна через `try/finally`, чтобы тесты не загрязняли друг друга.

### `apps/api/tests/test_log_intake.py` или новый focused test

Monkeypatch централизованный `_emit`, отправить через HTTP `/api/_log` envelope с:

- raw UUID correlation;
- email-like correlation;
- already-safe `h1_...`;
- raw UUID под `user_id_hash`/`question_id_hash`.

Проверить:

- accepted count корректен;
- ни один raw canary не попал в emitted dict/JSON;
- safe correlation сохраняется;
- unsafe correlation становится valid opaque `h1_...`;
- malformed `*_id_hash` редактируется.

### Logging failure tests

Добавить tests из раздела 3 для redactor/emit failure swallowing.

### Runtime policy tests

Добавить canary-safe exception test из раздела 4.

## 8. Scope cleanup

- удалить временные рассуждения, debug comments и dead code, появившиеся при R2;
- не менять Today/Calendar/natal/horary бизнес-логику;
- не ослаблять существующие tests ради зелёного результата;
- не вводить `pytest`, `sys.modules`, `PYTEST_CURRENT_TEST` или env-specific bypass в runtime code;
- `git diff --check` должен быть пуст;
- все новые/существенно изменённые functions имеют GRACE contracts.

## 9. Обязательные проверки R3

Сначала targeted:

```bash
cd /opt/solarsage-astro
apps/api/.venv/bin/python -m ruff check \
  apps/api/app/core/log_identity.py \
  apps/api/app/core/logging.py \
  apps/api/app/core/redactor.py \
  apps/api/app/core/runtime_security.py \
  apps/api/app/main.py \
  apps/api/app/middleware/correlation.py \
  apps/api/app/services/log_intake.py \
  apps/api/tests/test_cors_security.py \
  apps/api/tests/test_logging.py \
  apps/api/tests/test_logging_privacy.py \
  apps/api/tests/test_log_intake.py \
  apps/api/tests/test_runtime_security_policy.py \
  scripts/check_logging_guardrails.py

python3 scripts/check_logging_guardrails.py

cd apps/api
source .venv/bin/activate
python -m pytest \
  tests/test_runtime_security_policy.py \
  tests/test_public_surface_security.py \
  tests/test_cors_security.py \
  tests/test_logging.py \
  tests/test_logging_privacy.py \
  tests/test_log_intake.py \
  tests/test_log_envelope_shape.py \
  tests/test_redactor_canaries.py \
  tests/test_auth_endpoints.py \
  -q
```

Затем полный набор:

```bash
cd /opt/solarsage-astro
apps/api/.venv/bin/python -m pytest apps/api/tests -q
apps/api/.venv/bin/python -m compileall -q apps/api/app
git diff --check
```

Повторить четыре независимых probes по смыслу:

1. `/api/_log` raw correlation отсутствует в capture;
2. direct `bind_log_context(raw UUID)` не выпускает raw;
3. `log_event(valid_event)` не бросает при redactor/emit failure;
4. invalid deployed config exception не содержит canary value.

## 10. Stop condition

После зелёных проверок остановиться и сообщить архитектору:

- точные test counts;
- какие independent regression probes добавлены;
- `git diff --check` result;
- подтверждение: no commit, no push, no live config, no service restart.

Не переходить к runtime deployment самостоятельно.
