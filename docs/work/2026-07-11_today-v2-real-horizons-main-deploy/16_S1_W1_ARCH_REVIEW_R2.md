# S1.W1 Architect Review R2 — final edge-case cleanup

Дата: 2026-07-11

Вердикт: `REWORK_REQUIRED_S1_W1_R3`

Не выполнять S1.W2. Не commit и не push. Runtime architecture не менять.

## Принято в R2

- generator settings теперь реально вложены в `options`;
- return-string mode явный;
- unsupported discriminator branches fail-loud;
- generated artifact имеет ровно один import из `zod` и не содержит client
  code;
- public normalizer/main exports и GRACE markers исправлены;
- `as any` для malformed payload/evidence удалён;
- runtime barrel проверяет Today V2 block.

## Blocking 1 — `const` обязан всегда стать singleton enum

Сейчас Pass A при согласованном:

```json
{ "const": "a", "enum": ["a", "b"] }
```

оставляет multi-enum без изменения. Pass B затем пропускает property только
потому, что присутствует `const`. Но `openapi-zod-client` игнорирует `const` и
сгенерирует `z.enum(["a", "b"])`, то есть discriminator снова не literal.

Исправить:

```text
если const есть:
  если enum есть и это не array -> throw
  если enum есть и не содержит const -> throw
  затем всегда enum = [const]
```

Pass B не должен считать само наличие `const` достаточным. После Pass A
требовать:

```text
Array.isArray(propSchema.enum)
propSchema.enum.length === 1
если const есть: propSchema.enum[0] === propSchema.const
```

Добавить test для `const=a + enum=[a,b]`: normalizer выдаёт только `[a]`.

## Blocking 2 — нет positive test discriminator required

Добавить synthetic valid parent/child document и доказать после normalization:

```text
Child.required includes "type" exactly once
Child.properties.type.enum equals [literal]
```

Запустить normalizer второй раз на том же doc и доказать, что duplicate required
не появляется.

## Blocking 3 — убрать последний `any`

В test осталось:

```ts
const typeSchema: any = ...
```

Использовать узкий structural type либо assertion непосредственно по typed
path. `any` и double cast не нужны.

## Blocking 4 — untracked whitespace не попал в git diff gate

`git diff HEAD --check` не видит untracked file. Независимое ревью нашло trailing
spaces в:

```text
__tests__/contracts/generated-runtime.test.ts:136
__tests__/contracts/generated-runtime.test.ts:150
```

Удалить весь trailing whitespace во всех новых S1.W1 files и проверить:

```bash
rg -n '[ \t]+$' \
  scripts/contracts/generate-zod.cjs \
  scripts/contracts/templates/zod-schemas.hbs \
  packages/contracts/runtime.ts \
  __tests__/contracts/generated-runtime.test.ts \
  docs/work/2026-07-11_today-v2-real-horizons-main-deploy/14_S1_W1_DISCRIMINATOR_GUIDANCE.md \
  docs/work/2026-07-11_today-v2-real-horizons-main-deploy/15_S1_W1_ARCH_REVIEW.md \
  docs/work/2026-07-11_today-v2-real-horizons-main-deploy/16_S1_W1_ARCH_REVIEW_R2.md
```

Ожидается zero matches / exit 1.

## Blocking 5 — template map completeness

В `zod-schemas.hbs` module map добавить:

```text
owned_tests:
  - __tests__/contracts/generated-runtime.test.ts
```

Generated artifact обновится только через generator.

## Дополнительный regression proof

В test сравнить all-schema export:

```text
Object.keys(generated schemas map)
```

с component schema names canonical OpenAPI после допустимого stable sorting.
Это доказывает, что `shouldExportAllSchemas: true` не станет снова silently
ignored. Если generator санитизирует конкретное collision name, явно
зафиксировать deterministic mapping; не ослаблять до проверки только count.

## Gates

```bash
pnpm contracts:generate
pnpm contracts:generate
pnpm contracts:check
npx vitest run __tests__/contracts/generated-runtime.test.ts
npx tsc --noEmit
git diff HEAD --check
```

И отдельный trailing-whitespace `rg` выше.

## Callback

```text
READY_S1_W1_RUNTIME_CODEGEN_R3
const_multi_enum_narrowing: PASS
discriminator_required_positive_test: PASS
normalizer_second_pass_idempotence: PASS
all_schema_export_set: PASS <count>
any_in_s1_w1_code_or_tests: NO
untracked_whitespace_scan: PASS
template_owned_tests: PASS
contracts_check: PASS
vitest: <count/PASS>
tsc: PASS
commit: NOT_YET
push: NOT_YET
```
