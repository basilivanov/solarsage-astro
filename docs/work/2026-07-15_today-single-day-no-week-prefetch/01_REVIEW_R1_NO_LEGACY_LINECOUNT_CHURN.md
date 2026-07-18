# Review R1 — не ужимать legacy test-файл ради GRACE line limit

Дата: 2026-07-15

Это обязательное уточнение к `00_TZ.md`.

## 1. Что произошло

`scripts/grace_lint.py apps/api/tests/test_today_preview_transport.py` сообщил, что legacy-файл имеет более 1000 строк. Кодер начал удалять blank lines вне функционального change-set, чтобы искусственно пройти GRC030.

Архитектор остановил процесс. Такое изменение запрещено правилами репозитория: старый файл нельзя переписывать ради формата отдельно от задачи.

## 2. Восстановить unrelated whitespace

В `apps/api/tests/test_today_preview_transport.py` восстановить все удалённые blank lines вне заменяемого старого prefetch-test блока.

Финальный diff этого файла вне двух разрешённых зон должен быть пустым.

Разрешённые зоны:

1. import:

   ```python
   from datetime import date as Date, timedelta
   ```

   становится:

   ```python
   from datetime import date as Date
   ```

   только потому, что старый prefetch test больше не использует `timedelta`.

2. Полная замена старого `test_prefetch_week_never_propagates_preview_context` на один новый regression test.

Все deletion-only blank-line hunks возле `_BoundaryStop`, `_route_user`, `_build_route_app`, `_route_get`, `_install_service_harness`, block markers и старых guard tests восстановить.

Не удалять комментарии/докстринги/blank lines для уменьшения line count.

## 3. Оставить только один focused regression test

Удалить добавленный большой async test:

```text
test_today_service_does_not_schedule_prefetch_after_cache_write
```

Он строит дополнительный mock pipeline, дублирует существующие успешные Today tests и создаёт fragile unrelated scope.

Оставить один sync source-boundary test на месте старого семидневного теста:

```python
def test_today_service_has_no_background_week_prefetch_surface() -> None:
    source = inspect.getsource(today_service_module)

    assert "_prefetch_week" not in source
    assert "_TODAY_PREFETCH_TASKS" not in source
    assert "asyncio.create_task" not in source
    assert "asyncio.gather" not in source
    assert "SessionLocal" not in source
```

Function contract должен быть коротким и правдивым. Не расширять test helper/mocks.

Behavior requested-day/cache покрывается существующими targeted/full tests; архитектор отдельно проверит runtime/source boundary.

## 4. Исправленная GRACE gate

GRACE lint запускать только для production-файла:

```bash
python3 scripts/grace_lint.py apps/api/app/services/today_service.py
```

Для legacy `test_today_preview_transport.py` запускать:

```bash
apps/api/.venv/bin/python -m ruff check apps/api/tests/test_today_preview_transport.py
apps/api/.venv/bin/python -m pytest apps/api/tests/test_today_preview_transport.py -q
git diff --check
```

Не запускать GRACE retrofit и не исправлять GRC030 в этой задаче.

## 5. Diff acceptance для test-файла

Перед handoff выполнить:

```bash
git diff -- apps/api/tests/test_today_preview_transport.py
```

Допустимый diff содержит только:

- удаление `timedelta` из import;
- удаление старого 7-session prefetch test;
- добавление одного focused no-prefetch test.

Никаких других hunks.

## 6. Продолжение

После восстановления продолжить static/targeted/full gates из `00_TZ.md`, с исправленной GRACE-командой из раздела 4.

Commit, push, restart и env/cache changes по-прежнему запрещены. После handoff остановиться.
