# Архитектурное ревью R1: обязательные корректировки P0

- Дата: 2026-07-14
- Статус: **REWORK REQUIRED**
- Ветка: `fix/backend-p0-security-hardening`

Первая реализация полезна и полный API pytest зелёный, но acceptance ещё не достигнут. Ниже обязательные исправления. Live `.env`, nginx, systemd, restart, commit и push по-прежнему запрещены.

## B1. Убрать несвязанный diff из TodayService

В P0-ветку попали изменения, не относящиеся к security hardening:

- birth identity validation;
- изменение prefetch access state;
- отдельная session factory/последовательный prefetch;
- дополнительные horizon typing changes.

На baseline HEAD tracked diff был пуст. В `apps/api/app/services/today_service.py` оставить только P0-изменение logging payload: удалить raw `user_id`/raw exception. Все остальные hunks восстановить byte-for-byte к HEAD.

После исправления `git diff -- apps/api/app/services/today_service.py` не должен содержать prefetch, profile/birth, session factory или unrelated typing.

## B2. GRACE-контракт

Текущий `grace_lint.py` сообщает 22 нарушения.

Исправить:

1. Удалить дублированный старый banner/module contract из `apps/api/app/main.py`. Оставить один актуальный banner/contract/map.
2. Добавить function contract для `create_app`.
3. Добавить полный GRACE banner/contract/map и function contracts в:
   - `apps/api/tests/test_runtime_security_policy.py`;
   - `apps/api/tests/test_public_surface_security.py`;
   - `apps/api/tests/test_cors_security.py`;
   - `apps/api/tests/test_logging_privacy.py`.
4. Обновить contract/map `config.py`, который сейчас не отражает новые security settings.

Acceptance: scoped `scripts/grace_lint.py` по всем changed/new Python files возвращает 0 violations.

## B3. Runtime security policy edge cases

### B3.1. Explicit empty APP_ENV

Сейчас `Settings(APP_ENV="")` принимается как development. Исправить:

- отсутствие переменной продолжает использовать field default `dev`;
- явно пустая/whitespace строка даёт safe `ValueError`;
- test выполняется с `_env_file=None`.

### B3.2. Public development запрещён

Canonical `development` с non-loopback `APP_DOMAIN` должен fail closed. Разрешённые deployment modes:

```text
development + localhost/loopback
staging + real HTTPS domain
production + real HTTPS domain
```

Test process должен установить `APP_ENV=test` до импорта singleton settings либо использовать полностью isolated settings. Unit tests не должны читать deployment values/secrets из рабочей `.env`.

### B3.3. Loopback bug

Сейчас `127.0.0.2` принимается: `ValueError` от loopback check поглощается `except ValueError` парсера.

Использовать отдельную parse/result проверку:

```python
try:
    parsed_ip = ipaddress.ip_address(domain)
except ValueError:
    parsed_ip = None
if parsed_ip is not None and parsed_ip.is_loopback:
    raise ValueError(...)
```

Добавить IPv4/IPv6 loopback cases.

### B3.4. Origin parser

- обращаться к `parsed.port`, чтобы malformed port не проходил;
- в deployed запрещать localhost/loopback origins;
- по-прежнему запрещать userinfo, wildcard, path/query/fragment;
- errors не выводят secrets/DSN/token.

## B4. App factory

1. Перенести `validate_canon_bundle()` внутрь `create_app()`.
2. Убрать internal routers из верхнего общего import list. Импортировать `debug`, `metrics`, `health_extended`, `microcopy` только внутри `if policy.internal_routes_enabled`.
3. Staging/production tests должны проверять физическое отсутствие paths в `app.routes` и OpenAPI.
4. `create_app(custom_settings)` не меняет global settings.

## B5. Redactor hash bypass

Сейчас проходят raw значения под безопасным именем:

```python
{"user_id_hash": "123e4567-e89b-12d3-a456-426614174000"}
{"question_id_hash": 123456789}
```

Это P0 bypass через `/api/_log`.

Исправить:

1. Для `user_id_hash` и любого `*_id_hash` разрешать только строку `^h1_[0-9a-f]{24}$`.
2. Любое другое значение заменять на `[redacted-identifier]`.
3. Добавить tests: raw UUID, integer, malformed short hash, valid helper hash.
4. Проверить browser log intake: raw value под `user_id_hash` не попадает в emitted JSON.

## B6. HMAC identity helper

Исправить:

- namespace обязателен и соответствует `[a-z0-9_-]+`;
- deployed missing/short salt не маскируется local fallback;
- fallback разрешён только development/test;
- не возвращать одинаковый `h1_error_failed_to_hash` для разных обычных inputs;
- error/output никогда не содержит raw input.

Tests: determinism, namespace isolation, invalid namespace, deployed salt failure, raw input absence.

## B7. AST guardrail проверяет значения

Сейчас gate проверяет forbidden keys, но пропускает:

```python
log_event("system.error", payload={"actor": user_id})
log_event("system.error", error={"detail": question.text})
```

Расширить AST-анализ внутри `log_event`:

- recursively проверять `payload`, `error`, `http` values;
- запрещать raw identifier expressions (`user_id`, `question_id`, `.id` и аналоги);
- запрещать input-bearing `.text`, `.content`, `.question` в telemetry;
- `<entity>_id_hash` допускает только вызов hash helper/готовую переменную с `_hash` suffix;
- positional и keyword `msg` проверяются одинаково;
- добавить self-tests/fixtures: минимум один safe positive и два unsafe negative cases.

Не сканировать обычные DB/cache dictionaries вне `log_event`.

## B8. Scoped Ruff

Текущий scoped Ruff: 18 ошибок. Исправить все в changed/new files:

- duplicate imports в `api/_log.py`;
- unused imports в `debug.py`, `natal.py`, `calendar_service.py`, `horary_service.py`, `natal_report_service.py`;
- unused `sidecar_error` в Today/Calendar;
- unused imports новых tests;
- `E402 import ast` в guardrail.

Не делать mass-fix вне текущего changed-file scope.

## B9. Tests должны быть независимы от рабочей .env

`test_runtime_security_policy.py` сейчас проходит локально только потому, что `Settings` дочитывает `/opt/solarsage-astro/.env`. В isolated env он падает.

Исправить:

1. Policy tests используют `_env_file=None` или helper, который явно задаёт все required fields.
2. Добавить explicit empty APP_ENV test.
3. Добавить public development rejection.
4. Добавить `127.0.0.2` и IPv6 loopback rejection.
5. CORS: проверять evil preflight и обычный GET.
6. Logging privacy tests реально проверяют:
   - `user_id_hash` binding после valid session;
   - отсутствие raw cookie/token prints;
   - representative horary/chat/natal events без raw UUID;
   - malformed hash bypass.
7. Не использовать sync `TestClient` поверх async fixture session; использовать `AsyncClient` + `ASGITransport` в async tests.

## B10. Повторные проверки

Выполнить:

```bash
apps/api/.venv/bin/python scripts/grace_lint.py <all changed/new python files>
apps/api/.venv/bin/python -m ruff check <all changed/new python files>
python3 scripts/check_logging_guardrails.py
cd apps/api && source .venv/bin/activate && python -m pytest \
  tests/test_runtime_security_policy.py \
  tests/test_public_surface_security.py \
  tests/test_cors_security.py \
  tests/test_logging.py \
  tests/test_logging_privacy.py \
  tests/test_redactor_canaries.py \
  tests/test_microcopy_misses.py \
  tests/test_auth_endpoints.py -q
cd /opt/solarsage-astro
apps/api/.venv/bin/python -m pytest apps/api/tests -q
apps/api/.venv/bin/python -m compileall -q apps/api/app
git diff --check
```

Ожидания:

- GRACE 0 violations;
- scoped Ruff 0 errors;
- guardrail all passed;
- full API suite green;
- TodayService diff только logging privacy;
- no live config/restart/commit/push.

После исправлений остановиться и ждать повторного архитектурного ревью.
