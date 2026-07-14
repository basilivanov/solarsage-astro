# R4A — последние два пропуска перед live runtime

Статус: **REWORK REQUIRED, ровно два исправления**.

Никаких иных изменений. No live config/restart/commit/push.

## 1. `bind_log_context` всё ещё использует старый regex

Файл: `apps/api/app/core/logging.py`, ветка `if user_id_hash`.

Сейчас:

```python
if re.match(r"^h1_[0-9a-f]{24}$", user_id_hash):
```

Исправить строго:

```python
from app.core.log_identity import is_opaque_log_id

if is_opaque_log_id(user_id_hash):
    user_id_hash_var.set(user_id_hash)
else:
    user_id_hash_var.set("[redacted-identifier]")
```

Можно объединить inline imports `normalize_correlation_id` и `is_opaque_log_id` в одном месте/модульном import, если это не создаёт cycle. Не оставлять local regex.

Regression test:

```python
bind_log_context(
    correlation_id="h1_" + "a" * 24,
    user_id_hash="h1_" + "b" * 24 + "\n",
    slice="W", module="M", block="B",
)
envelope = build_envelope("system.request")
assert envelope["user_id_hash"] == "[redacted-identifier]"
```

Использовать `try/finally: clear_log_context()`.

## 2. Redactor failure test monkeypatch-ит не тот symbol

Файл: `apps/api/tests/test_logging_privacy.py`, `test_logging_failures_swallowed`.

`apps/api/app/core/logging.py` импортирует `redact_dict` напрямую. Поэтому:

```python
monkeypatch.setattr(redactor_module, "redact_dict", ...)
```

не меняет `logging_module.redact_dict` и текущая первая фаза теста ничего не доказывает.

Исправить точный target:

```python
monkeypatch.setattr(
    logging_module,
    "redact_dict",
    lambda value: (_ for _ in ()).throw(ValueError("synthetic")),
)
logging_module.log_event("system.request")  # must not raise
```

После первой фазы восстановить original symbol либо использовать отдельный `with monkeypatch.context() as patch:` для каждой фазы. Не применять глобальный `monkeypatch.undo()` посередине теста, если после него нужны другие fixture patches.

Вторая фаза отдельно monkeypatch-ит `logging_module._emit -> RuntimeError` при нормальном `logging_module.redact_dict`.

Третья фаза unknown event по-прежнему ждёт `ValueError`.

## 3. Проверки

```bash
cd /opt/solarsage-astro
apps/api/.venv/bin/python -m ruff check \
  apps/api/app/core/logging.py \
  apps/api/tests/test_logging_privacy.py \
  apps/api/tests/test_logging.py

cd apps/api
source .venv/bin/activate
python -m pytest \
  tests/test_logging.py \
  tests/test_logging_privacy.py \
  tests/test_log_envelope_shape.py \
  -q

cd /opt/solarsage-astro
python3 scripts/check_logging_guardrails.py
apps/api/.venv/bin/python -m pytest apps/api/tests -q
apps/api/.venv/bin/python -m compileall -q apps/api/app
git diff --check
```

После этого остановиться и сообщить exact counts. Никаких других рефакторингов.
