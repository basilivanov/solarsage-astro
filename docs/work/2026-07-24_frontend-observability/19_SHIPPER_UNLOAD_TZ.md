# Slice 19 — shipper unload fallback and GRACE contract

## Цель

Не терять unload batch, когда `navigator.sendBeacon` доступен, но возвращает
`false`, и завершить GRACE-разметку shipper без изменения retry/backoff логики.

## Разрешённые файлы

- `lib/log/shipper.ts`
- `__tests__/lib/log-shipper.test.ts`

## Требования

1. `flushSync`:
   - сериализует только canonical envelopes, без tracked attempt/notBefore;
   - `sendBeacon(...) === true` считается доставленным;
   - `sendBeacon(...) === false` или синхронный throw -> fallback `fetch` с
     `method POST`, JSON headers/body, `keepalive: true`,
     `credentials: "include"`;
   - если JSON serialization не удалась, batch возвращается в buffer;
   - если beacon не доставил и fetch недоступен/синхронно бросил, batch
     возвращается в buffer;
   - async rejection fallback fetch swallowing и не ломает user flow; по
     возможности вернуть batch в buffer для pagehide/BFCache, без лог-рекурсии.
2. Не менять batch=50/5s, retryable statuses, attempts=5, exponential
   backoff/jitter/notBefore и concurrency behavior.
3. Убрать legacy map до header; добавить named module map и function contracts
   для public class methods/exports (`constructor` при необходимости,
   `destroy`, `enqueue`, `calculateBackoff`, `flush`, `getLogShipper`,
   `resetLogShipperForTests`).

## Tests

- существующие 16 tests сохранить;
- sendBeacon true -> fetch не вызывается;
- sendBeacon false -> exact keepalive fetch body с canonical envelopes;
- sendBeacon throw -> fallback fetch;
- serialization failure не бросает и batch не исчезает (можно проверить
  повторным unload после исправления/удаления bad payload либо безопасным test
  introspection);
- fallback fetch sync throw не бросает;
- cleanup timers/listeners/globals.

Проверка:

```bash
npx vitest run __tests__/lib/log-shipper.test.ts && npx tsc --noEmit
```

Другие файлы не менять. Ничего не коммить и не пушить — коммит делает ревьюер.
