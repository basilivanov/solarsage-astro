# Slice 08 — election response contract wiring

## Цель

Добавить diagnostic response contracts только в уже инструментированный election
client, сохранив все public/domain semantics.

## Разрешённые файлы

- `lib/api/election.ts`
- `__tests__/lib/election-api.test.ts`

## Требования

1. Response contracts для четырёх calls:
   - quota -> `HoraryQuotaSchema.safeParse`;
   - list -> `z.array(ElectionSearchSchema).safeParse`;
   - detail/create -> `ElectionSearchSchema.safeParse`.
2. Стабильные contract names + version `v1`; issue paths capped/structural,
   без values/messages.
3. Существующие `.parse`, 404->null, `ElectionApiError`, idempotency body и
   routes/operations не менять.
4. Полностью оформить существующий файл по GRACE для затронутых public functions:
   module contract/map, blocks/function contracts, реальные delegated
   `emitted_logs`. Не переписывать схемы или UI.

## Tests

Расширить существующий election test (добавить полноценный GRACE contract/map):

- сохранить текущий Zod v2 test;
- mock instrumentedFetch и проверить 4 operation/routeTemplate/contracts;
- каждый validator принимает quota/valid search/list и отвергает `{}`/`[{}]`;
- regression: detail 404 -> null;
- regression: create сохраняет exact POST body/idempotency key;
- cleanup mocks/globals.

Проверка:

```bash
npx vitest run __tests__/lib/election-api.test.ts && npx tsc --noEmit
```

Другие файлы не менять. Ничего не коммить и не пушить — коммит делает ревьюер.
