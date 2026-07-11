# S2.W1 Architecture Guidance R1 — do not weaken timing accuracy tests

Дата: 2026-07-11
Основание: review текущего `test_transit_timing.py` после первых solver runs.
Статус: обязательное дополнение к `36_S2_W1_REAL_TIMING_IMPLEMENTATION_TZ.md`.

## Blocking guidance

Не заменять точностные assertions строковыми проверками вида:

```py
assert "11:59" in actual or "12:00" in actual
assert actual.startswith("2026-07-08")
```

Такая проверка может пропустить ошибку почти в минуту для exact и почти в сутки
для boundary. Она не доказывает заданный numerical contract.

## Правильная проверка

Добавить test helper, который строго парсит canonical UTC-Z:

```py
from datetime import datetime, timezone

def parse_utc_z(value: str) -> datetime:
    assert value.endswith("Z")
    parsed = datetime.fromisoformat(value.removesuffix("Z") + "+00:00")
    assert parsed.tzinfo is not None
    return parsed.astimezone(timezone.utc)

def seconds_between(actual: str, expected: str) -> float:
    return abs((parse_utc_z(actual) - parse_utc_z(expected)).total_seconds())
```

Assertions:

```py
assert seconds_between(result.exact_at_utc, expected_exact) <= 60.0
assert seconds_between(result.active_from_utc, expected_from) <= 300.0
assert seconds_between(result.active_until_utc, expected_until) <= 300.0
```

Если solver уже refine exact до 1 секунды, допустимо и предпочтительно проверить:

```py
assert seconds_between(result.exact_at_utc, expected_exact) <= 1.0
```

но public acceptance contract всё равно report как `<= 60 seconds`.

## Inclusive boundary

`active_until` обязан возвращать последний подтверждённый inside-side instant.
Поэтому значение на 1 секунду раньше математического crossing корректно и
должно проходить numerical `<= 300 seconds` assertion. Не заставлять solver
выдавать outside/exclusive instant только ради exact string equality.

Аналогично `active_from` возвращает первый подтверждённый inside-side instant.

## Triple pass/tangent

- Каждый из трёх expected roots сравнить численно с соответствующим sorted hit.
- Проверить `len == 3`, strict ascending order и max error каждого hit.
- Tangent root сравнить численно, не префиксом строки.
- Near-miss по-прежнему обязан иметь boundaries + `exact_at=None` + warning.

## Дальнейшее выполнение

После исправления assertions продолжить все §§12–20 основного ТЗ. Не считать
focused solver tests достаточным завершением волны. `today_service.py` не менять.
Commit/push запрещены до architect acceptance.
