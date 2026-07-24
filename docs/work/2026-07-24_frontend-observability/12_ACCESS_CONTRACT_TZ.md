# Slice 12 — access client response contract

## Цель

Подключить авторитетный runtime contract к одному access endpoint и сохранить
точную UI mapping/error semantics.

## Разрешённые файлы

- `lib/api/access.ts`
- `__tests__/api/access.test.ts`

## Требования

1. Импортировать `AccessSummaryWireSchema` из stable
   `@/packages/contracts/runtime`.
2. Передать в `instrumentedFetch` response contract:
   - `contractName: "AccessSummary"`;
   - `contractVersion: "v1"`;
   - validator через `AccessSummaryWireSchema.safeParse`;
   - diagnostics содержат только safe issue paths, без values/messages.
3. После успешного HTTP-ответа authoritative decode сделать через
   `AccessSummaryWireSchema.parse(await res.json())`, затем сохранить текущий
   `toAccessInfo`/date mapping без изменений.
4. Сохранить exact operation, route template, headers, credentials и текущий
   приоритет backend detail errors.
5. Обновить GRACE module/function contracts и реальные emitted log names.

## Tests

- mock `instrumentedFetch`, а не raw global fetch;
- сохранить текущие mapping и HTTP error assertions;
- проверить operation/route/init/responseContract;
- validator принимает canonical valid summary и отклоняет `{}`;
- успешный HTTP 200 с invalid shape отвергается authoritative parse;
- cleanup mocks/globals.

Проверка:

```bash
npx vitest run __tests__/api/access.test.ts __tests__/hooks/useAccess.test.ts && npx tsc --noEmit
```

Другие файлы не менять. Ничего не коммить и не пушить — коммит делает ревьюер.
