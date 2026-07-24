# Slice 05 — horary API client instrumentation

## Цель

Завершить один доменный client: все horary calls через instrumentedFetch и
diagnostic response contracts. Не менять wrapper, другие API clients, UI или
backend.

## Разрешённые файлы

- `lib/api/horary.ts`
- новый `__tests__/api/horary-instrumentation.test.ts`

## Требования

1. Заменить последний raw `fetch` в `createHoraryQuestion` на
   `instrumentedFetch`:
   - operation `horary.create_question`;
   - route template `POST /api/horary/questions`;
   - сохранить method, credentials, Content-Type и exact JSON body.
2. Подключить `responseContract` ко всем четырём horary calls:
   - quota -> `HoraryQuotaSchema.safeParse`;
   - list -> `HoraryQuestionSchema.array().safeParse`;
   - detail/create -> `HoraryQuestionSchema.safeParse`.
   Contract names/version стабильные и без PII. Существующие authoritative
   `.parse(await res.json())`, HTTP mapping и public return/error behavior
   сохранить без изменений.
3. Все route templates статические, без limit/offset/id/body values.
4. Обновить module contract dependencies/emitted_logs на реальные делегированные
   events. Не менять бизнес-копирайт/error mapping.

## Test

Новый test с GRACE header/contracts должен mock-ать `instrumentedFetch` и
доказывать:

- четыре public calls передают ожидаемые operation/routeTemplate;
- create сохраняет exact POST init/body и не вызывает raw global fetch;
- каждый `responseContract.validate` принимает valid fixture и отвергает `{}`;
- existing 404 detail -> null и HTTP error mapping не сломаны хотя бы одним
  regression assertion.

Не тестировать wrapper повторно — только wiring horary client.

Проверка:

```bash
npx vitest run __tests__/api/horary-instrumentation.test.ts __tests__/contracts/horary.test.ts && npx tsc --noEmit
```

Другие файлы не менять. Ничего не коммить и не пушить — коммит делает ревьюер.
