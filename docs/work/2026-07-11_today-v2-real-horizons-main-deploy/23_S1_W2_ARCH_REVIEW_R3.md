# S1.W2 Architecture Review R3 — final literal gate cleanup

Дата: 2026-07-11

Вердикт: **REWORK REQUIRED — four literal cleanup items only**.
Commit/push запрещены. S1.W3 не начинать.

Сохранить весь текущий working implementation и восстановленное покрытие.

## 1. Forbidden scan должен реально вернуть no matches

Сейчас scan находит:

```text
__tests__/lib/adapt-payload.test.ts:17://   - No as any, ts-ignore, ts-expect-error
```

Заменить invariant на строку без запрещённых tokens:

```text
No unsafe casts or TypeScript suppression directives.
```

После этого exact scan из R2 должен вернуть no output.

## 2. Module map и START_BLOCK должны совпадать

В `lib/contracts/today.ts` сейчас:

```text
module map: WIRE_SCHEMAS_IMPORT
actual block: GENERATED_V2_WIRE_SCHEMA_ALIAS
```

Изменить module map entry на:

```text
GENERATED_V2_WIRE_SCHEMA_ALIAS: aliases generated V2 wire validation without
redeclaring its shape.
```

## 3. Constructor contract поставить внутрь class

В `lib/grace/api/client.ts` contract
`F-M-WEB-API-CLIENT.ApiContractError.constructor` сейчас стоит перед class.
Переместить его внутрь `ApiContractError` непосредственно перед `constructor()`:

```ts
export class ApiContractError extends ApiError {
  // START_FUNCTION_CONTRACT: ...
  // ...
  // END_FUNCTION_CONTRACT: ...
  constructor() {
    ...
  }
}
```

Поведение класса не менять.

## 4. Исправить Markdown/whitespace review docs

### R1

Финал `21_S1_W2_ARCH_REVIEW_R1.md` сейчас повреждён:

```text
push: NOT_YET```
```

Сделать корректно:

```text
push: NOT_YET
```

где закрывающий Markdown fence находится на отдельной следующей строке.

### R2

Убрать только лишнюю пустую строку в EOF
`22_S1_W2_ARCH_REVIEW_R2.md`, сохранив нормальный завершающий newline и
корректный closing fence.

## 5. Gates

```bash
rg -n '\bas any\b|as unknown as|@ts-ignore|@ts-expect-error' \
  packages/contracts/index.ts \
  lib/grace/api/client.ts \
  lib/contracts/today.ts \
  lib/adapters/today-payload.ts \
  lib/presentation/today-v2.ts \
  __tests__/api/grace-client.test.ts \
  __tests__/lib/adapt-payload.test.ts \
  __tests__/lib/presentation/today-v2.test.ts \
  __tests__/contracts/today-redeclaration-guard.test.ts

git diff HEAD --check
npx tsc --noEmit
```

Expected:

```text
forbidden scan: no output
diff check: no output
tsc: PASS
commit: NOT_YET
push: NOT_YET
```

## 6. Callback

```text
READY_S1_W2_WIRE_MIGRATION_R4
forbidden_cast_scan_matches: 0
v2_alias_map_block_aligned: YES
constructor_contract_position: INSIDE_CLASS
review_docs_markdown: VALID
diff_check: PASS
tsc: PASS
commit: NOT_YET
push: NOT_YET
```
