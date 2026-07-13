# S1.W1 Architecture Guidance — OpenAPI 3.1 `const` and discriminators

Дата: 2026-07-11

Статус: обязательное уточнение S1.W1 после локально воспроизведённого generator
failure. Не commit/push. S1.W2 не начинать.

## 1. Подтверждённая причина

Pydantic корректно экспортирует discriminator branches как OpenAPI 3.1:

```json
{
  "type": "string",
  "const": "paragraph",
  "default": "paragraph"
}
```

и parent union как:

```json
{
  "oneOf": ["...refs..."],
  "discriminator": { "propertyName": "type" }
}
```

`openapi-zod-client@1.18.3` в `openApiToZod.ts`:

- видит parent discriminator и генерирует `z.discriminatedUnion("type", ...)`;
- не обрабатывает JSON Schema `const`;
- поэтому branch property становится `z.string().optional().default(...)`;
- каждый branch допускает discriminator value `undefined`;
- Zod при module initialization падает:

```text
Discriminator property type has duplicate value undefined
```

Это не проблема TodayPayload и не причина убирать Pydantic discriminators.
Это compatibility gap конкретной версии генератора с OpenAPI 3.1 `const`.

## 2. Архитектурно принятое решение

Не редактировать `_generated.zod.ts` после генерации и не делать regex replace
по TypeScript output.

Добавить deterministic programmatic wrapper:

```text
scripts/contracts/generate-zod.cjs
```

Он использует pinned package API:

```js
const { generateZodClientFromOpenAPI } = require("openapi-zod-client")
```

Wrapper:

1. читает canonical `packages/contracts/openapi.json`;
2. создаёт in-memory deep clone;
3. применяет только описанную ниже compatibility normalization;
4. вызывает `generateZodClientFromOpenAPI` с:
   - canonical custom schemas-only template;
   - `shouldExportAllSchemas: true`;
   - `strictObjects: false`;
   - normal default-value behavior;
   - output `packages/contracts/_generated.zod.ts`;
5. не записывает normalized OpenAPI как отдельный artifact;
6. не меняет canonical `openapi.json`.

CLI остаётся pinned dependency, но `generate.sh` вызывает этот wrapper, потому
что CLI не предоставляет `schemaRefiner`/document normalizer option.

## 3. Exact compatibility normalization

Работать с in-memory document, без mutations canonical JSON file.

### Pass A — `const` to singleton enum

Рекурсивно пройти JSON tree. Для каждого schema-like object с own `const`:

```text
если enum отсутствует:
  enum = [const]
если enum уже существует и не содержит const:
  fail loudly: contradictory schema
```

`const` можно сохранить: генератор проигнорирует его и увидит singleton enum,
поэтому создаст `z.literal(value)`.

Не превращать обычный `default` в literal. Источник literal truth — только
OpenAPI `const`.

### Pass B — discriminator property required in referenced branches

Рекурсивно найти каждый schema object, содержащий одновременно:

```text
discriminator.propertyName
oneOf[]
```

Для каждого `$ref` branch из `oneOf`:

1. разрешать только local component ref формата:

```text
#/components/schemas/<name>
```

2. получить referenced component;
3. доказать, что у него есть property с именем discriminator;
4. доказать, что property имеет `const` или singleton `enum` после Pass A;
5. добавить discriminator property в component `required`, если его там нет;
6. сохранить существующий порядок required и append один раз.

Почему это корректно: parent Pydantic discriminated union требует discriminator
для выбора branch, даже если standalone component показывает default. Backend
response также сериализует `type`. Generated runtime validator должен отражать
semantics parent union, а не принимать неоднозначный object без `type`.

Если branch inline, `$ref` внешний, target/property отсутствует или literal
неоднозначен — wrapper падает с schema name/path. Никакого silent fallback.

## 4. Запрещённые обходы

- не заменять все `z.discriminatedUnion` на `z.union`;
- не удалять discriminators из Pydantic/OpenAPI;
- не делать `sed`/regex patch generated TS;
- не вручную менять generated branch schemas;
- не добавлять `as any` в runtime barrel/tests;
- не исключать horary/natal schemas из all-schema generation ради Today;
- не обновлять package выше pinned `1.18.3` внутри этой волны.

## 5. Wrapper contract/GRACE

Новый `generate-zod.cjs` должен иметь:

- `AI_HEADER`;
- named module contract/map;
- semantic blocks `OPENAPI_NORMALIZATION`, `ZOD_GENERATION`, `CLI_FAILURE`;
- function contracts минимум для normalization entrypoint и `main`;
- side effects: read OpenAPI/template, write generated artifact;
- emitted logs: none, только deterministic stdout/stderr CLI summary;
- failure policy: non-zero process exit, no partially accepted artifact.

Для atomicity предпочтительно генерировать во временный sibling path и rename в
final path только после успешной генерации/import sanity. Временный файл всегда
cleanup в `finally`.

## 6. Обязательные tests

Расширить `generated-runtime.test.ts` либо добавить focused normalizer test.

Доказать:

1. importing `_generated.zod.ts` больше не throws;
2. generated horary paragraph branch содержит literal discriminator;
3. valid HoraryAnswerRead sample с `type: "paragraph"` parses;
4. unknown horary `type` rejects;
5. missing discriminator in a discriminated parent rejects;
6. valid NatalSection sample parses;
7. TodayPayload tests исходного S1.W1 проходят;
8. unknown additive root field TodayPayload не rejected;
9. generated file по-прежнему импортирует runtime только из `zod`;
10. generated file не содержит `@zodios/core` или HTTP client.

Также выполнить import smoke напрямую, чтобы module-init error был виден вне
Vitest assertion body.

## 7. Generation/idempotence gates

```bash
pnpm contracts:generate
cp packages/contracts/_generated.zod.ts /tmp/solarsage-generated-zod-first.ts
pnpm contracts:generate
cmp /tmp/solarsage-generated-zod-first.ts packages/contracts/_generated.zod.ts
pnpm contracts:check
npx vitest run __tests__/contracts/generated-runtime.test.ts
npx tsc --noEmit
git diff HEAD --check
```

Удалить только созданный `/tmp/solarsage-generated-zod-first.ts` после compare.

## 8. Callback остаётся исходным

Вернуть `READY_S1_W1_RUNTIME_CODEGEN`, дополнительно указав:

```text
openapi31_const_normalization: PASS
discriminator_required_normalization: PASS
horary_module_import: PASS
manual_generated_ts_patch: NO
canonical_openapi_mutated_by_zod_wrapper: NO
```
