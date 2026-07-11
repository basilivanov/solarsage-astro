# S1.W2 Architecture Guidance — generated type barrel and single validation

Дата: 2026-07-11

Статус: обязательное уточнение после первого TypeScript pass. Не commit/push,
S1.W3 не начинать.

## 1. Причина текущих TypeScript errors

`packages/contracts/_generated.ts` содержит component schemas, но public
types-only barrel `packages/contracts/index.ts` пока экспортирует не все V2
aliases. Импортировать component names напрямую как named exports нельзя.

Правильное решение — расширить существующий types-only barrel, не создавать
ручные interfaces и не импортировать `_generated.ts` из product consumers.

## 2. Расширить types-only barrel

В `packages/contracts/index.ts` добавить только type aliases:

```ts
export type TodayV2Block = components["schemas"]["TodayV2Block"]
export type TodayV2ActivatedTarget = components["schemas"]["TodayV2ActivatedTarget"]
export type TodayV2ActivationSummary = components["schemas"]["TodayV2ActivationSummary"]
export type TodayV2WhyTodayItem = components["schemas"]["TodayV2WhyTodayItem"]
export type TodayV2Audit = components["schemas"]["TodayV2Audit"]
export type ActivationEvidence = components["schemas"]["ActivationEvidence"]
export type SphereScoreV2 = components["schemas"]["SphereScoreV2"]
```

Если реально нужен `SphereContribution`, экспортировать таким же alias, но не
добавлять неиспользуемый API ради полноты.

Обновить module contract/map output/public entrypoints. Barrel остаётся
types-only и не импортирует runtime values.

## 3. Fetch boundary

В `fetchDay`:

```ts
const rawJson: unknown = await res.json()
const parsed = TodayPayloadWireSchema.safeParse(rawJson)
```

При success вернуть `parsed.data` без cast. Он должен быть структурно assignable
generated `TodayPayload`. Если compile parity не проходит, остановиться с
точным field mismatch; не использовать `as TodayPayload`, `as any` или double
cast.

### Typed contract error

Добавить отдельный exported subclass:

```text
ApiContractError extends ApiError
name: ApiContractError
status: 502
code: SCHEMA_VALIDATION_ERROR
message: generic, no payload/Zod issues/PII
```

Не использовать HTTP response status 200 для contract failure.

`useDay` уже логирует только `String(err)`: generic error message остаётся
безопасным. Не логировать `rawJson`, `parsed.error.issues`, birth/profile data.

Обновить public re-export в `lib/grace/index.ts`, если error входит в public API.

## 4. Adapter не валидирует wire второй раз

Текущий черновик всё ещё делает:

```ts
TodayV2BlockSchema.parse(apiV2)
```

Это запрещено S1.W2. Raw payload уже validated в `fetchDay`.

`buildV2Block` должен быть pure pass-through/shape-only:

```ts
function buildV2Block(apiV2: TodayPayload["v2"]): TodayV2Block | null {
  return apiV2 ?? null
}
```

Если return type конфликтует из-за Zod defaults, не возвращать parse в adapter.
Вместо этого разделить UI schema inference и public adapted type:

```text
ParsedAdaptedTodayPayload = z.infer<typeof TodayPayloadSchema>
AdaptedTodayPayload = Omit<ParsedAdaptedTodayPayload, "v2"> & {
  v2?: TodayV2Block | null
}
```

`validateAdaptedTodayPayload` может продолжать использовать UI
`TodayPayloadSchema` в test/mock validation и возвращать parsed result: Zod
output с заполненными defaults assignable более широкому generated wire type.

Допустимо alias:

```ts
export const TodayV2BlockSchema = TodayV2BlockWireSchema
```

потому что это не ручное shape declaration. Но production adapter не вызывает
его parse/safeParse.

## 5. `lib/contracts/today.ts`

Удалить ручные raw-wire declarations полностью, включая nested
`SphereContributionSchema`, если он существовал только для raw V2.

Разрешено оставить:

- UI schemas для notes/why/top flags/day summary/adapted layout;
- generated runtime schema alias без `z.object` redeclaration;
- generated type aliases из public types-only barrel.

Не оставлять комментарий «manual schemas removed» вместо contract. Написать
точно, что V2 wire schema/value идёт из generated runtime barrel.

Обновить module contract/map: это UI-adapted contract module, не wire SoT.

## 6. Type fallout in components

Сначала добавить barrel aliases и исправить adapted type. После этого повторить
`tsc`.

Только если ошибки остаются:

- `dev-audit-drawer.tsx`: никогда не рендерить `unknown` как ReactNode;
  добавить локальный safe formatter/type guard для string/number/boolean/null,
  object отображать безопасным summary/JSON без PII dump;
- `why-expanded.tsx`: callbacks должны получить конкретный generated
  `ActivationEvidence` type, не implicit `any`.

Не ослаблять component props до `unknown`, `Record<string, any>` или `any[]`.

## 7. Tests

### Grace client boundary

Обновить `__tests__/api/grace-client.test.ts`:

- success использует contract-valid canonical Today payload, а не объект из
  трёх полей;
- malformed nested V2 response throws `ApiContractError`;
- error status=502, code=`SCHEMA_VALIDATION_ERROR`;
- error message не содержит test sentinel из raw payload и не содержит Zod
  issue paths;
- HTTP error behavior 401/404/422 сохраняется.

### Adapter purity

Добавить proof:

```text
adapted.payload.v2 === input.v2
```

для уже contract-valid input, то есть adapter не reparses/rebuilds wire V2.

### Redeclaration guard

Добавить focused guard test, читающий `lib/contracts/today.ts`, который запрещает
следующие manual declarations через `z.object`:

```text
ActivationEvidenceSchema
SphereContributionSchema
SphereScoreV2Schema
TodayV2ActivatedTargetSchema
TodayV2ActivationSummarySchema
TodayV2WhyTodayItemSchema
TodayV2AuditSchema
TodayV2BlockSchema
```

`TodayV2BlockSchema = TodayV2BlockWireSchema` разрешён. Guard не должен
зависеть от CSS/LLM text.

## 8. GRACE

Существенно изменённые:

```text
packages/contracts/index.ts
lib/grace/api/client.ts
lib/contracts/today.ts
lib/adapters/today-payload.ts
```

должны иметь truthful named module contracts/maps; для `fetchDay`,
`ApiContractError` constructor/public class, `adaptTodayPayload` — function/class
contracts по repository convention. Реальные logs/events, никаких generic
`n/a/log and raise`, если поведение иное.

## 9. Gates

```bash
pnpm contracts:check
npx vitest run \
  __tests__/api/grace-client.test.ts \
  __tests__/lib/adapt-payload.test.ts \
  __tests__/contracts/generated-runtime.test.ts \
  __tests__/contracts/today.test.ts \
  __tests__/components/TodayScreen.v2-downstream.test.tsx \
  __tests__/guardrails/no-runtime-mocks.test.ts \
  <new manual-v2-redeclaration guard test>
npx tsc --noEmit
rg -n '\bas any\b|as unknown as|@ts-ignore|@ts-expect-error' \
  packages/contracts/index.ts \
  lib/grace/api/client.ts \
  lib/contracts/today.ts \
  lib/adapters/today-payload.ts \
  <new/changed tests>
git diff HEAD --check
```

## 10. Callback

Исходный callback `READY_S1_W2_WIRE_MIGRATION`, дополнительно:

```text
typed_contract_error: ApiContractError/502/SCHEMA_VALIDATION_ERROR
fetch_return_casts: 0
adapter_v2_parse_calls: 0
adapter_v2_identity_test: PASS
types_only_barrel_v2_aliases: <list>
manual_redeclaration_guard: PASS
```
