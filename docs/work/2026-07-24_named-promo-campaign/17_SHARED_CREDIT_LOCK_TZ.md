# Slice 17 — election/horary shared credit row locking

## Локальная цель

Закрыть существующую race перед выдачей promo gift credits: election должен
списывать общий HoraryCredit под тем же row lock contract, что horary.

## Разрешённые файлы

- `apps/api/app/services/election_service.py`;
- наиболее узкий election service test file.

## Изменение

В create/search spend transaction вызвать:

```py
select_spendable_credit(user_id, now, lock=True)
```

Lock, increment `used_amount`, `ElectionCreditSpend` insert и commit остаются в
одной AsyncSession/transaction. Не менять priority order, public errors,
refund/background generation или HoraryCredit schema.

## Tests

- service передаёт `lock=True`;
- gift source по-прежнему выбирается как bonus;
- no-credit behavior прежний;
- idempotent election request не списывает второй раз;
- compiled PostgreSQL candidate select содержит `FOR UPDATE`.

Real cross-flow concurrency доказывает финальный PostgreSQL acceptance slice,
не SQLite unit.

## Targeted verification

```bash
cd apps/api && source .venv/bin/activate && python -m pytest tests/test_election_service.py -q
```

Если exact test filename отличается, кодер указывает его в отчёте и запускает
только этот file.

## Out of scope

Promo models/service, credit ordering, new ledger table, refund redesign. Не
коммитить и не пушить.

