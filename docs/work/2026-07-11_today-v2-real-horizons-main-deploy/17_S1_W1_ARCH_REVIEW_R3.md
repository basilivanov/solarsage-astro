# S1.W1 Architect Review R3 — final contract truth cleanup

Дата: 2026-07-11

Вердикт: `REWORK_REQUIRED_S1_W1_R4`

Не выполнять S1.W2. Не commit и не push.

## 1. Убрать double casts

В test остались три конструкции вида:

```ts
(value as unknown) as SomeType
```

Это противоречит no-double-cast правилу.

Для synthetic test documents можно проверять динамически без cast:

```ts
expect(Reflect.get(typeObject, "enum")).toEqual(["paragraph"])
```

Для child:

```ts
const required = Reflect.get(childObject, "required")
const properties = Reflect.get(childObject, "properties")
const typeProperty = Reflect.get(properties, "type")
```

Сначала доказать `Array.isArray(required)` / object shape там, где это нужно,
затем assertions. Не добавлять `any`, `unknown as`, `@ts-ignore` или
`@ts-expect-error`.

## 2. Discriminator без oneOf обязан fail-loud

Сейчас:

```js
if (obj.discriminator && obj.oneOf) {
```

Из-за этого object с `discriminator`, но без `oneOf`, полностью пропускает
validation.

Исправить:

```js
if (obj.discriminator) {
  // validate propertyName
  // validate that oneOf is a non-empty array
  // validate every branch
}
```

Добавить test:

```text
discriminator present + oneOf missing -> throws
```

## 3. Formatting/whitespace

Прогнать formatter только по handwritten TS test, если repository formatter
доступен, либо вручную привести добавленные synthetic object literals к
существующему стилю с trailing commas. Generated artifact вручную не
форматировать.

Повторить zero-match scan:

```bash
rg -n '\bas any\b|as unknown as|@ts-ignore|@ts-expect-error|[ \t]+$' \
  scripts/contracts/generate-zod.cjs \
  scripts/contracts/templates/zod-schemas.hbs \
  packages/contracts/runtime.ts \
  __tests__/contracts/generated-runtime.test.ts
```

Ожидается zero matches.

## Gates

```bash
pnpm contracts:generate
pnpm contracts:generate
pnpm contracts:check
npx vitest run __tests__/contracts/generated-runtime.test.ts
npx tsc --noEmit
git diff HEAD --check
```

## Callback

```text
READY_S1_W1_RUNTIME_CODEGEN_R4
double_casts: 0
discriminator_without_oneof_test: PASS
handwritten_formatting: PASS
forbidden_pattern_scan: PASS
contracts_check: PASS
vitest: <count/PASS>
tsc: PASS
commit: NOT_YET
push: NOT_YET
```
