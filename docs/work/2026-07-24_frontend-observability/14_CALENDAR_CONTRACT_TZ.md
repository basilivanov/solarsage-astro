# Slice 14 — calendar facade contracts

## Цель

Закрыть runtime contracts у day-status и month операций одного calendar facade,
сохранив существующую status normalization и UI read-model.

## Разрешённые файлы

- `lib/api/calendar.ts`
- `__tests__/api/calendar.test.ts`

## Требования

1. `getDayStatus`:
   - response contract `TodayPayload`/`v1` через `TodayPayloadWireSchema`;
   - после HTTP success authoritative parse полного Today payload;
   - затем прежняя normalization root `dayStatus` (`supportive`, `tense`,
     `steady -> even`, другое/null -> null).
2. `getMonthCalendar`:
   - authoritative boundary остаётся
     `validateCalendarPayloadReadModel(await res.json())`;
   - diagnostic response contract использует
     `CalendarPayloadReadModelSchema.safeParse`, contract
     `CalendarPayloadReadModel`/`v1`;
   - invalid diagnostics содержат только safe issue paths, без values/messages.
3. `getMonthStatuses`, zero-based month arithmetic, operations, URLs,
   headers/credentials, HTTP errors и reference-equal aliases не менять.
4. Полная GRACE module/function/block разметка и реальные emitted events.

## Tests

- mock `instrumentedFetch` boundary вместо raw fetch;
- для day response использовать canonical `dayPayloadV2`, меняя только
  contract-valid root `dayStatus` для normalization cases;
- проверить обе operations/templates/URLs/inits/contracts;
- оба validators: valid fixture принимается, `{}` отвергается;
- authoritative invalid 200 responses отвергаются;
- сохранить status map, access/lunar, HTTP/network и alias assertions;
- cleanup mocks.

Проверка:

```bash
npx vitest run __tests__/api/calendar.test.ts __tests__/components/WeekStrip.test.tsx __tests__/components/CalendarScreen.test.tsx && npx tsc --noEmit
```

Другие файлы не менять. Ничего не коммить и не пушить — коммит делает ревьюер.
