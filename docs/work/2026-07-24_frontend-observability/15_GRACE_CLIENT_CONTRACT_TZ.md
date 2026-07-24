# Slice 15 — GRACE day/calendar client instrumentation

## Цель

Перевести канонический GRACE day/calendar client с raw fetch на общий wrapper и
закрыть Calendar runtime contract без изменения preview-marker и ApiError API.

## Разрешённые файлы

- `lib/grace/api/client.ts`
- `__tests__/api/grace-client.test.ts`

## Требования

1. Оба raw fetch заменить на `instrumentedFetch`:
   - day: operation `day.fetch`, template `GET /api/day/{date}`;
   - calendar: operation `calendar.fetch`, template `GET /api/calendar`;
   - сохранить actual URL, credentials, Accept и Today preview header policy.
2. Day response contract/authoritative parse через `TodayPayloadWireSchema`,
   contract `TodayPayload`/`v1`, safe issue paths.
3. Calendar response contract/authoritative parse через
   `CalendarPayloadWireSchema`, contract `CalendarPayload`/`v1`, safe issue
   paths.
4. `ApiContractError` должен уметь безопасно сообщать Today или Calendar
   contract mismatch, сохранив для Today exact существующие name/status=502/
   code/message и публичный no-arg constructor. Calendar error не содержит raw
   payload/Zod issues.
5. HTTP `ApiError` detail/status/code, preview-marker decisions и exports не
   менять.
6. Обновить GRACE dependencies/emitted logs/function contracts.

## Tests

- сохранить все текущие preview-marker/ApiError/day assertions;
- global fetch assertions учитывать wrapper-added correlation header/signal
  через nested `expect.objectContaining`, не требовать случайный ID;
- все success calendar fixtures заменить на canonical contract-valid fixture;
- проверить Calendar success authoritative parsed result;
- invalid Calendar 200 -> safe `ApiContractError` с Calendar message и без raw
  sentinel/Zod paths;
- existing malformed Today behavior остаётся exact;
- cleanup globals/env/mocks.

Проверка:

```bash
npx vitest run __tests__/api/grace-client.test.ts __tests__/lib/instrumented-fetch.test.ts && npx tsc --noEmit
```

Другие файлы не менять. Ничего не коммить и не пушить — коммит делает ревьюер.
