# Slice 13 — today facade response contract

## Цель

Подключить canonical Today runtime contract к минимальному `lib/api/today.ts`
facade, не меняя date-path и compatibility alias.

## Разрешённые файлы

- `lib/api/today.ts`
- `__tests__/api/today-instrumentation.test.ts` (новый)

## Требования

1. Импортировать `TodayPayloadWireSchema` из stable runtime barrel.
2. Добавить response contract к существующему `instrumentedFetch`:
   - `contractName: "TodayPayload"`;
   - `contractVersion: "v1"`;
   - validator через safeParse, diagnostics только safe issue paths.
3. После успешного ответа вернуть результат authoritative
   `TodayPayloadWireSchema.parse(await res.json())`.
4. Сохранить без изменений:
   - UTC `toISOString().split("T")[0]` path;
   - operation `today.load` и template `GET /api/day/{date}`;
   - credentials/Accept;
   - HTTP error priority `detail.message` -> `API error {status}`;
   - reference-equal `getTodayPayloadAsync = getTodayPayload`.
5. Полная GRACE module/map/function/block разметка с реальными emitted events.

## Tests

- mock `instrumentedFetch` boundary;
- canonical success fixture использовать
  `e2e/mock-visual/fixtures/day-v2-2026-07-08`;
- проверить URL/date, operation/template/init/contract;
- validator принимает fixture и отклоняет `{}`;
- authoritative parse отвергает invalid 200 response;
- HTTP detail и fallback error semantics;
- alias reference equality;
- cleanup mocks.

Проверка:

```bash
npx vitest run __tests__/api/today-instrumentation.test.ts __tests__/api/grace-client.test.ts && npx tsc --noEmit
```

Другие файлы не менять. Ничего не коммить и не пушить — коммит делает ревьюер.
