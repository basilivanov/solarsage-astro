# Slice 03 — non-committing additive access grant primitive

## Локальная цель

Подготовить `AccessService` к atomic promo service без promo-specific logic:
вычислять первый день нового grant после уже выданного доступа и возвращать
созданную `AccessLedger` row.

## Разрешённые файлы

- `apps/api/app/services/access_service.py`;
- `apps/api/tests/test_access_service.py`.

## Реализация

1. Добавить public method с ясным именем, например:

```py
async def next_grant_start(
    self,
    user_id: UUID,
    requested_start: date,
) -> date
```

Семантика:

```text
latest_end absent or latest_end < requested_start -> requested_start
latest_end >= requested_start -> latest_end + 1 day
```

Учитываются все `AccessLedger.entry_type`, включая referral и subscription.
Метод только читает и не commit/flush.

2. Изменить `grant_subscription(...) -> AccessLedger`:

- existing `commit=True` behavior сохраняется;
- `commit=False` делает flush, но не commit;
- метод всегда возвращает созданный ORM object с assigned ID;
- legacy callers, игнорирующие return, не ломаются;
- validate `days > 0` до insert; deterministic `ValueError` без DB mutation.

3. Обновить GRACE contracts/map, реальный return и side effects. Не добавлять
promo event в этот generic service.

## Tests

- no ledger -> requested start;
- expired ledger -> requested start;
- active/future multiple ledgers -> day after max end;
- subscription row has inclusive `days - 1` end;
- returned row has ID;
- `commit=False` row виден в той же transaction и исчезает после rollback;
- `commit=True` legacy behavior сохранён;
- `days <= 0` не создаёт row.

## Targeted verification

```bash
cd apps/api && source .venv/bin/activate && python -m pytest tests/test_access_service.py -q
```

## Out of scope

Не менять `BillingService`, access summary semantics, promo models/service,
referral commits, Subscription/YooKassa. Не коммитить и не пушить.

