# S1.W1 Architect Review R1 — REWORK_REQUIRED

Дата: 2026-07-11

Вердикт: `REWORK_REQUIRED_S1_W1_R2`

Не выполнять S1.W2. Не commit и не push.

## Принято

- pinned `openapi-zod-client@1.18.3` добавлен как devDependency;
- выбран правильный programmatic compatibility wrapper;
- canonical OpenAPI не изменяется wrapper-ом на диске;
- const/discriminator runtime crash локально устранён;
- generated artifact schemas-only, без generated Zodios client;
- runtime barrel отделён от types-only barrel;
- generator дважды выдаёт идентичный artifact по callback.

## Blocking finding 1 — generator options сейчас игнорируются

Фактическая сигнатура `generateZodClientFromOpenAPI` принимает настройки внутри
поля `options`.

Сейчас в `generate-zod.cjs` передано ошибочно:

```js
generateZodClientFromOpenAPI({
  openApiDoc,
  templatePath,
  shouldExportAllSchemas: true,
  strictObjects: false,
})
```

Оба последних поля игнорируются destructuring-ом package API.

Исправить точно:

```js
generateZodClientFromOpenAPI({
  openApiDoc: clonedDoc,
  templatePath,
  disableWriteToFile: true,
  options: {
    shouldExportAllSchemas: true,
    strictObjects: false,
  },
})
```

`disableWriteToFile: true` явно фиксирует ожидаемый return-string mode вместо
неявного поведения без `distPath`.

Перед записью проверить:

```text
typeof generatedCode === "string"
generatedCode.trim().length > 0
```

иначе fail before rename.

## Blocking finding 2 — Pass B молча пропускает unsupported branch

Guidance требует fail-loud для inline/external/invalid branch. Сейчас код:

```text
if (branch && branch.$ref) { ... }
```

молча игнорирует branch без `$ref`.

Для каждого `oneOf` branch обязательно:

1. branch — non-null object;
2. присутствует string `$ref`;
3. ref начинается `#/components/schemas/`;
4. component существует;
5. discriminator property существует;
6. после Pass A property имеет singleton enum, согласованный с const;
7. discriminator добавлен в required ровно один раз.

Любое нарушение throws с JSON traversal path/schema ref. Не продолжать
generation частично.

Также явно проверить:

- `discriminator.propertyName` — non-empty string;
- `oneOf` — non-empty array;
- existing `enum` при const — array и содержит const;
- singleton literal после Pass A действительно имеет `enum.length === 1`.

## Blocking finding 3 — tests не доказывают заявленный guardrail

### Убрать `as any`

В test fixture mutations не использовать `as any`.

Допустимый паттерн:

```ts
const malformed: Record<string, unknown> = { ...dayPayloadV2 }
delete malformed.date
```

Аналогично evidence.

### Проверить TodayV2Block barrel export

Добавить positive parse:

```text
TodayV2BlockWireSchema parses dayPayloadV2.v2
```

### Реально проверить only-zod import/no-client

Не ограничиваться `contains`.

1. Собрать все top-level import lines generated file.
2. Доказать, что их ровно одна и это import from `zod`.
3. Доказать отсутствие минимум:

```text
@zodios/core
Zodios
zodios
axios
createApiClient
fetch(
endpoints
```

Проверка `endpoints` должна быть word-aware, чтобы не ловить случайное слово в
comment; generated template вообще не должен содержать endpoint section.

### Протестировать normalizer fail-loud

Экспортировать из CJS для test, не меняя CLI behavior:

```js
module.exports = { normalizeOpenAPIDocument, main }
```

Module map обновить двумя public entrypoints.

В focused tests доказать:

- const становится singleton enum;
- discriminator property становится required;
- contradictory const/enum throws;
- inline oneOf branch throws;
- external ref throws;
- missing discriminator property throws.

Test передаёт deep-cloned synthetic document и не пишет files.

## Blocking finding 4 — GRACE template/markers неполны

### `generate-zod.cjs`

Function markers сейчас спрятаны как строки внутри JSDoc (`* START_...`).
Привести к обычным comment markers по repository convention:

```text
// START_FUNCTION_CONTRACT: ...
// ...
// END_FUNCTION_CONTRACT: ...
```

Сохранить парные `START_BLOCK/END_BLOCK`.

После export module contract/module map должны честно называть
`normalizeOpenAPIDocument` и `main`.

### `zod-schemas.hbs`

Добавить `START_MODULE_MAP/END_MODULE_MAP`.

Заменить неточные:

```text
invariants: none
failure_policy: none
```

на реальные:

- output imports runtime only from zod;
- output exports every schemas context entry plus stable `schemas` map;
- template/render failure aborts generator and final artifact is not replaced.

Generated file получит эти comments автоматически; вручную его не править.

### Test module map

Добавить `owned_tests` с путём самого test file.

## Dependency wording

`openapi-zod-client` содержит transitive dev dependencies
`@zodios/core/axios`. Это допустимо только как generator toolchain dependency.

Callback должен различать:

```text
generated_or_app_runtime_imports_zodios: NO
toolchain_transitive_dev_dependency_zodios: YES (package-owned)
```

Не заявлять, что пакет вообще отсутствует из lockfile.

## R2 gates

```bash
pnpm contracts:generate
cp packages/contracts/_generated.zod.ts /tmp/solarsage-generated-zod-r2.ts
pnpm contracts:generate
cmp /tmp/solarsage-generated-zod-r2.ts packages/contracts/_generated.zod.ts
rm /tmp/solarsage-generated-zod-r2.ts
pnpm contracts:check
npx vitest run __tests__/contracts/generated-runtime.test.ts
npx tsc --noEmit
git diff HEAD --check
```

Дополнительно:

```bash
rg -n '@zodios|Zodios|axios|createApiClient|fetch\(|\bendpoints\b' \
  packages/contracts/_generated.zod.ts packages/contracts/runtime.ts
```

Ожидаемый exit для `rg`: 1, zero matches.

## Callback

```text
READY_S1_W1_RUNTIME_CODEGEN_R2
generator_options_nested: PASS
explicit_return_string_mode: PASS
normalizer_fail_loud_tests: <count/PASS>
generated_imports: <exact list>
generated_or_app_runtime_imports_zodios: NO
toolchain_transitive_dev_dependency_zodios: YES
manual_generated_ts_patch: NO
canonical_openapi_mutated_by_zod_wrapper: NO
idempotence: PASS
contracts_check: PASS
vitest: <count/PASS>
tsc: PASS
git_diff_head_check: PASS
commit: NOT_YET
push: NOT_YET
```
