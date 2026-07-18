# R4 — финальная exactness и regression coverage перед live runtime

- Статус: **REWORK REQUIRED, небольшой ограниченный scope**
- Live config/restart/commit/push запрещены.
- Не менять business services.

Основные P0 probes R3 уже зелёные. Исправить только перечисленные ниже точные остатки.

## R4-B1. Exact opaque ID predicate: только `fullmatch`

Независимый probe текущего redactor:

```text
safe    -> preserved
suffix  -> redacted
newline -> preserved as 'h1_...\n'
```

Причина: `re.match(r"^...$", value)` допускает match перед финальным newline. Контракт требует exact `h1_[0-9a-f]{24}`.

### Реализация

В `apps/api/app/core/log_identity.py` добавить один helper:

```python
def is_opaque_log_id(value: object) -> bool:
    return isinstance(value, str) and OPAQUE_LOG_ID_PATTERN.fullmatch(value) is not None
```

С GRACE function contract; добавить в module map/public entrypoints, если helper публично импортируется.

Использовать его вместо дублированных regex во всех местах:

- `normalize_correlation_id`;
- `apps/api/app/core/logging.py` для `user_id_hash` validation;
- `apps/api/app/core/redactor.py` для `correlation_id`, `user_id_hash`, `*_id_hash`.

Не оставлять локальные `re.match(r"^h1_...")`.

Также заменить `NAMESPACE_PATTERN.match(ns_clean)` на `NAMESPACE_PATTERN.fullmatch(ns_clean)`.

### Extreme fallback

`hash_log_identifier()` не должен возвращать невалидное:

```text
h1_error_failed_to_hash_completely
```

В local/test second-level fallback вернуть deterministic valid `h1_` + 24 hex от static safe marker, не используя raw input. В deployed по-прежнему raise safe RuntimeError.

### Контракты

- Исправить ошибочный contract id у `normalize_correlation_id`: сейчас он назван `...new_correlation_id`.
- `new_correlation_id`/`normalize_correlation_id` не обещают `never raises`, если deployed salt/HMAC fail-closed может поднять safe exception. Описать фактическое поведение.

### Tests

Добавить parametrized exactness:

```text
h1_ + 24 lowercase hex       -> true/preserved
h1_ + 23 hex                 -> false/redacted
h1_ + 25 hex                 -> false/redacted
h1_ + 24 hex + suffix        -> false/redacted
h1_ + 24 hex + newline       -> false/redacted
h1_ + uppercase hex          -> false/redacted
integer / None               -> false/redacted where applicable
```

Проверить и `correlation_id`, и один `user_id_hash`/`question_id_hash`.

## R4-B2. CORS regression test закрепляет allowed GET и `Vary`

Runtime independent probe уже доказал:

```text
allowed GET      -> ACAO exact, Vary: Origin
evil GET         -> no ACAO
allowed preflight -> ACAO exact, Vary: Origin
evil preflight   -> no ACAO
```

Но текущий `test_cors_security.py` проверяет allowed только через OPTIONS.

Добавить отдельный allowed GET:

```python
allowed_get = client.get(
    "/api/health",
    headers={"Origin": "https://astro.example.com"},
)
assert allowed_get.status_code == 200
assert allowed_get.headers["access-control-allow-origin"] == "https://astro.example.com"
assert allowed_get.headers["access-control-allow-credentials"] == "true"
assert "origin" in allowed_get.headers.get("vary", "").lower()
assert allowed_get.headers["access-control-allow-origin"] != "*"
```

Для allowed preflight также проверить `Vary: Origin` и no wildcard. Для evil response `Vary` не требовать.

Не возвращать самописный middleware.

## R4-B3. Logging failure regression: redactor и emit — два независимых случая

Текущий `test_logging_failures_swallowed` проверяет только `_emit -> RuntimeError`, хотя contract говорит redactor/emit.

Сделать два независимых теста либо две фазы с явным restore:

1. `redact_dict -> ValueError`, `_emit` нормальный: `log_event(valid_event)` не бросает.
2. `redact_dict` нормальный, `_emit -> RuntimeError`: не бросает.
3. Отдельно unknown event всё ещё даёт programmer-error `ValueError` до operational try.

Не проверять это только текстом комментария.

## R4-B4. HTTP intake route regression

Текущий bypass test вызывает service напрямую. Сохранить его, но добавить один HTTP-level test через существующий `async_client`:

- monkeypatch `LogIntakeService._emit_line`;
- POST `/api/_log` с raw UUID correlation и malformed `user_id_hash`;
- status 200 / accepted 1;
- captured emitted correlation проходит `is_opaque_log_id`;
- raw UUID отсутствует во всём captured dict;
- malformed hash redacted.

Это доказывает route schema -> handler -> service wiring, а не только helper/service.

## R4-B5. AST guardrail не дублирует одно нарушение

Independent probe:

```text
question.id in msg -> два одинаковых violations
```

Причина: для `msg` отдельно обходится каждый `FormattedValue`, затем весь `JoinedStr` тем же analyzer.

Оставить только один вызов `_collect_log_expr_violations(kw.value)` для `msg`. Он уже рекурсивно видит `FormattedValue`.

Добавить self-test:

```python
violations = _violations_for_snippet(
    'log_event("system.error", msg=f"question {question.id}")'
)
assert violations.count("raw attribute chain: question.id") == 1
```

Safe hash helper по-прежнему даёт `[]`.

## R4-B6. Проверки

```bash
cd /opt/solarsage-astro
apps/api/.venv/bin/python -m ruff check \
  apps/api/app/core/log_identity.py \
  apps/api/app/core/logging.py \
  apps/api/app/core/redactor.py \
  apps/api/tests/test_cors_security.py \
  apps/api/tests/test_logging_privacy.py \
  apps/api/tests/test_log_intake.py \
  apps/api/tests/test_logging.py \
  apps/api/tests/test_redactor_canaries.py \
  scripts/check_logging_guardrails.py

python3 scripts/check_logging_guardrails.py

cd apps/api
source .venv/bin/activate
python -m pytest \
  tests/test_cors_security.py \
  tests/test_logging.py \
  tests/test_logging_privacy.py \
  tests/test_log_intake.py \
  tests/test_log_envelope_shape.py \
  tests/test_redactor_canaries.py \
  -q

cd /opt/solarsage-astro
apps/api/.venv/bin/python -m pytest apps/api/tests -q
apps/api/.venv/bin/python -m compileall -q apps/api/app
git diff --check
```

Повторить independent exactness probe для newline/suffix.

После этого остановиться. No live config/restart/commit/push.
