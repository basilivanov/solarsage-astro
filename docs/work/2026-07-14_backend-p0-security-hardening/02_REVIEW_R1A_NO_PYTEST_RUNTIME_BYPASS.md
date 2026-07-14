# Архитектурная поправка R1A: запрет pytest-bypass в runtime policy

Статус: обязательный blocker.

В `runtime_security.py` запрещено проверять:

- `pytest` в `sys.modules`;
- `pytest` в `sys.argv`;
- `PYTEST_CURRENT_TEST`;
- CI/test process markers;
- любые другие признаки test runner.

Runtime security policy должна быть чистой функцией только от переданного `Settings`. Публичный `APP_ENV=development` с non-loopback `APP_DOMAIN` всегда даёт `ValueError`, независимо от вызывающего процесса.

Правильное исправление test collection:

1. В `apps/api/tests/conftest.py` установить безопасные test env values **до** импорта `app.core.config.settings` и `app.main.app`:

```python
import os

os.environ["APP_ENV"] = "test"
os.environ.setdefault("APP_DOMAIN", "localhost")
```

При необходимости аналогично задать только безопасные test defaults, но не читать/копировать deployment secrets.

2. Либо перестроить fixture так, чтобы app создавался через isolated `Settings(_env_file=None, APP_ENV="test", ...)` до импорта global app. Первый вариант минимальнее.
3. Unit policy tests по-прежнему используют `_env_file=None` и explicit settings.
4. Удалить весь `import sys` и test-runner conditional из production module.

Нельзя чинить падающие tests ослаблением security invariant. После исправления повторить targeted suite из R1.
