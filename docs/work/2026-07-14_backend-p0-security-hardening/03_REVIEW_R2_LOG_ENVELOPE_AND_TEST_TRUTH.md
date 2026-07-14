# Архитектурное ревью R2: log envelope и доказательность privacy

Статус: **REWORK REQUIRED — P0 bypass найден независимой проверкой**.

## R2-B1. Raw user_id_hash выходит после redaction

Независимый probe текущего кода:

```python
bind_log_context(
    correlation_id="corr",
    user_id_hash="123e4567-e89b-12d3-a456-426614174000",
    slice="W", module="M", block="B",
)
build_envelope("system.request")
```

возвращает raw UUID в top-level `user_id_hash`.

Причина: `log_event()` redacts только `payload/error/msg/http`, а `user_id_hash` добавляется в envelope после этих операций.

Исправить одним из эквивалентных способов, предпочтительно обоими:

1. В `log_event()` прогонять весь envelope через центральный `redact_dict()` после добавления всех top-level fields.
2. В `bind_log_context()` принимать `user_id_hash` только если он соответствует `^h1_[0-9a-f]{24}$`; invalid value игнорировать/заменять safe marker, никогда не хранить raw.

Не редактировать `correlation_id` просто как произвольное allow-key: см. R2-B3.

Обязательный regression test: invalid raw `user_id_hash` в context не появляется ни в `build_envelope`, ни в emitted JSON.

## R2-B2. Deployed salt failure всё ещё маскируется fallback

`hash_log_identifier()` ловит `ValueError` от short/missing salt в deployed и затем возвращает HMAC от `LOCAL_TEST_LOG_SALT`. Это нарушает fail-closed invariant и создаёт одинаковую operational identity между средами.

Исправить:

- validation errors namespace/salt не проглатывать fallback-веткой;
- в deployed с short/missing salt бросать safe `RuntimeError`/`ValueError` без raw input;
- local/test fallback разрешать только после явного canonical environment check;
- fallback output, если он нужен для local, должен соответствовать валидному `h1_[0-9a-f]{24}`;
- добавить test прямого helper call в deployed-like settings с short salt: ожидается exception, а не `h1_err_*`.

Не включать raw namespace/value/salt в exception text.

## R2-B3. Caller-controlled correlation_id не должен быть PII bypass

`X-Correlation-Id` и browser `/api/_log` envelope могут содержать произвольный string, а `correlation_id` сейчас allow-listed и сохраняется без проверки. Простая проверка «это UUID» недостаточна: raw DB user UUID также является UUID.

Обязательный invariant: **ни один caller-provided correlation value не пишется raw**.

Рекомендуемая схема:

- если header отсутствует — middleware mint-ит собственный UUID;
- если header уже имеет валидный opaque формат `h1_[0-9a-f]{24}` — можно принять его;
- любой другой bounded header сначала HMAC-хешировать через `hash_log_identifier("correlation", raw_header)` и только hash использовать в context/response/log;
- oversized/control-character header не хешировать, а заменить server-minted UUID;
- `/api/_log` применяет ту же normalization либо redacts raw correlation до emit;
- `correlation_id` нельзя оставлять unconditional raw allow-key без normalization.

Так первый frontend UUID станет opaque server-visible correlation hash; response вернёт hash, и последующие запросы смогут использовать уже безопасное значение.

Добавить tests:

- raw UUID header не появляется в log/response, вместо него возвращается opaque hash;
- уже безопасный `h1_...` сохраняется;
- email/oversized/control-character header не появляется raw;
- `/api/_log` raw correlation value не появляется в emitted output.

## R2-B4. Logging tests должны проверять реальное поведение

Текущий `test_horary_chat_natal_events_no_raw_uuids` проверяет только hash helper, но не representative `log_event` payloads. Переименовать его либо добавить реальные calls:

- вызвать/замокать representative horary success/refund event;
- representative chat thread/message event;
- representative natal report event;
- прогнать через `log_event`/redactor и проверить, что raw UUID отсутствует, а `<entity>_id_hash` валиден.

`test_auth_rejection_no_prints` должен проверять `printed_messages == []`, а не только отсутствие трёх слов.

Добавить test для top-level envelope invalid `user_id_hash`, а не только `redact_dict` напрямую.

## R2-B5. CORS test completeness

`test_cors_security.py` проверяет evil preflight, но не обычный GET с evil Origin. Добавить:

```text
GET /api/health + Origin https://evil.example
=> нет Access-Control-Allow-Origin
=> нет Access-Control-Allow-Credentials:true для evil origin
```

## R2-B6. Safe startup error text

`runtime_security.py` сейчас включает целый `orig` в ошибки invalid origin. Если в ошибочном env окажется `https://user:password@example.com`, secret попадёт в startup journal.

Все origin parser errors должны содержать только индекс/причину (`origin[0]:userinfo-forbidden`, `origin[1]:invalid-port`), без raw origin value.

## R2-B7. Scoped quality cleanup

Независимый scoped Ruff всё ещё выдаёт два ошибки в изменённом `test_redactor_canaries.py`:

- unused `typing.Any`;
- unused `REDACT_PATTERNS`.

Убрать imports.

В `config.py` удалить повторный `apps/api/app/core/__init__.py` в `owns`.

`scripts/check_logging_guardrails.py` получил большой новый AST/self-test block. Добавить GRACE function contracts для новых public functions/helpers либо сделать helpers private; не оставлять новые GRC010 violations. Старые baseline violations в неизменённых legacy test functions не расширять.

## R2-B8. Проверки после исправления

```bash
apps/api/.venv/bin/python -m ruff check <all changed/new Python files>
python3 scripts/check_logging_guardrails.py
cd apps/api && source .venv/bin/activate && python -m pytest \
  tests/test_runtime_security_policy.py \
  tests/test_public_surface_security.py \
  tests/test_cors_security.py \
  tests/test_logging.py \
  tests/test_logging_privacy.py \
  tests/test_redactor_canaries.py \
  tests/test_auth_endpoints.py -q
cd /opt/solarsage-astro
apps/api/.venv/bin/python -m pytest apps/api/tests -q
apps/api/.venv/bin/python -m compileall -q apps/api/app
git diff --check
```

Не менять live `.env`, nginx, systemd; не рестартовать; не commit/push.
