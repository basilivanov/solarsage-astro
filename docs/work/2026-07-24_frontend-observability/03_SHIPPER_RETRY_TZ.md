# Slice 03 — retry state machine frontend log shipper

## Цель

Сделать transient retry автономным и bounded, не отправляя delayed retry раньше
срока при появлении нового события. Менять только shipper и его unit tests.

## Разрешённые файлы

- `lib/log/shipper.ts`
- `__tests__/lib/log-shipper.test.ts`

## Контракт

1. Network error, `429`, `5xx` автоматически retry без нового `enqueue`.
2. Не более 5 фактических send attempts на envelope (initial входит в лимит).
   После пятой transient failure envelope drop silently.
3. Backoff: первая повторная отправка около 1s, затем 2s/4s/8s, cap 30s,
   bounded jitter ±20%. `calculateBackoff` должен иметь однозначную семантику и
   тестируемые границы.
4. Delayed retry нельзя отправить раньше `notBefore`:
   - обычный 5s batch timer;
   - новый fresh event;
   - достижение fresh batch size
   не должны вытянуть старый retry до срока.
   Fresh eligible events при этом могут отправляться независимо, не ожидая
   backoff старого batch.
5. В каждый момент не более одного HTTP flush. Concurrent `flush()` не дублирует
   envelopes. После завершения очередь сама планирует eligible batch или самый
   ранний retry.
6. `400..499` кроме 429 drop без retry. Success удаляет только отправленный
   batch и не теряет события, добавленные во время in-flight request.
7. Debug mode по-прежнему flush each eligible enqueue immediately.
8. `beforeunload/pagehide` отправляет canonical `envelopes` без internal attempt/
   notBefore fields. `resetLogShipperForTests` очищает timers и зарегистрированные
   handlers, чтобы тесты/module reset не копили side effects.
9. Любая внутренняя ошибка (`fetch`, serialization, timer callback) не создаёт
   unhandled rejection и не ломает приложение. Не логировать ошибки shipper
   через сам shipper.

Можно выбрать queue design (`notBefore` entries либо раздельные fresh/retry
queues), но инварианты выше обязательны.

## Tests

Сохранить существующие batching/5s/beacon/kill-switch/debug assertions и добавить:

- automatic network retry;
- automatic 429 retry;
- automatic 5xx retry;
- backoff/jitter bounds: attempt 1≈1s, 2≈2s;
- max 5 sends and drop;
- non-retryable 4xx no retry;
- fresh event during old backoff sends fresh, old остаётся до notBefore;
- concurrent flush no duplicate;
- enqueue during in-flight not lost;
- reset clears timers/listeners;
- beacon body has envelopes only, no attempt/notBefore.

Использовать fake timers детерминированно, обязательно восстанавливать real
timers в `afterEach` даже при failure.

Проверка только:

```bash
npx vitest run __tests__/lib/log-shipper.test.ts && npx tsc --noEmit
```

Другие файлы не менять. Ничего не коммить и не пушить — коммит делает ревьюер.
