# S1.W2 Architecture Review R2 — exact remaining fixes

Дата: 2026-07-11

Вердикт: **REWORK REQUIRED**. Commit/push запрещены. S1.W3 не начинать.

Прочитать вместе с:

```text
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/21_S1_W2_ARCH_REVIEW_R1.md
```

R2 восстановил основное regression coverage:

```text
adapter: 24 tests
presentation: 28 executed tests, включая it.each expansion
```

Это сохранить. Ниже только оставшиеся точечные блокеры.

## 1. Фактический forbidden cast scan не равен нулю

Сейчас реально остаются:

```text
__tests__/lib/adapt-payload.test.ts:466       v2Block as any
__tests__/lib/presentation/today-v2.test.ts:137  } as any
__tests__/lib/presentation/today-v2.test.ts:156  } as any
```

Также scan находит текст `No as any` в module contract. Не писать запрещённый
token даже в декларативном комментарии; заменить invariant на:

```text
No unsafe casts or TypeScript suppression directives.
```

### 1.1 Adapter identity test

Не собирать V2 object вручную. Импортировать canonical fixture и использовать
его уже typed block:

```ts
import { dayPayloadV2 } from "@/e2e/mock-visual/fixtures/day-v2-2026-07-08"

const v2Block = dayPayloadV2.v2
expect(v2Block).toBeDefined()
if (!v2Block) throw new Error("fixture v2 block is missing")

const api = createBaseApi({ v2: v2Block })
const { payload } = adaptTodayPayload(api, TODAY)
expect(payload.v2).toBe(v2Block)
```

Удалить весь текущий вручную собранный `v2Block` из identity test.

### 1.2 Presentation title tests

В этом же файле уже есть typed helper:

```ts
evidenceFromFixture(id, overrides): ActivationEvidence
```

Оба title tests должны вызывать его, например:

```ts
const title = formatActivationEvidenceTitle(
  evidenceFromFixture("dative-title", {
    sourcePlanet: "Transit_Moon",
    targetPlanet: "Natal_Pluto",
    aspect: "opposition",
  }),
)
```

И аналогично для второго case. Не создавать incomplete evidence literal и не
cast-ить его.

## 2. Grace client test всё ещё использует JSON round-trip и не имеет sentinel

Фактический файл всё ещё содержит:

```text
JSON.parse(JSON.stringify(dayPayloadV2))
manual delete activeFrom/activeUntil
catch + err as ApiContractError
no RAW_PAYLOAD_SENTINEL_DO_NOT_LEAK
```

Это не соответствует R1.

### 2.1 Success case — точная замена

Добавить import:

```ts
import { TodayPayloadWireSchema } from "@/packages/contracts/runtime"
```

В success test:

```ts
const contractPayload = TodayPayloadWireSchema.parse(dayPayloadV2)

global.fetch = vi.fn().mockResolvedValue({
  ok: true,
  json: async () => contractPayload,
})

const result = await fetchDay("2026-07-08")
expect(result).toEqual(contractPayload)
```

Полностью удалить JSON clone и manual deletes.

### 2.2 Malformed case — точная замена assertions

Добавить unique value в malformed raw object:

```ts
const sentinel = "RAW_PAYLOAD_SENTINEL_DO_NOT_LEAK"
```

Поместить sentinel, например, в `evidence` malformed nested item. Item всё равно
должен не иметь обязательного `id`, чтобы generated schema отвергла payload.

После настройки fetch:

```ts
const request = fetchDay("2026-07-08")

await expect(request).rejects.toBeInstanceOf(ApiContractError)
await expect(request).rejects.toMatchObject({
  name: "ApiContractError",
  status: 502,
  code: "SCHEMA_VALIDATION_ERROR",
  message: "Invalid Today payload format from backend",
})
await expect(request).rejects.toMatchObject({
  message: expect.not.stringContaining(sentinel),
})
await expect(request).rejects.toMatchObject({
  message: expect.not.stringContaining("activationEvidence"),
})
```

Удалить `try/catch`, `expect.fail` и `err as ApiContractError` только из этого
new contract-error test. Старые обычные `as ApiError` в legacy HTTP tests не
относятся к этому blocker.

## 3. Product type-noise из R1 не убран

### 3.1 `components/today/dev-audit-drawer.tsx`

Полностью убрать текущий diff файла. Generated `TodayV2Audit.canonVersions`
имеет `Record<string, string>`; прежний render корректен. Файл не должен входить
в S1.W2 final diff.

### 3.2 `components/today/why-expanded.tsx`

Убрать три inline callback annotations:

```ts
item: import("@/packages/contracts").ActivationEvidence
```

Вернуть обычные inferred callbacks. Файл не должен входить в S1.W2 final diff,
если больше изменений в нём нет.

### 3.3 `lib/presentation/today-v2.ts`

Сохранить:

- generated type imports;
- timing bridge;
- module map/function contract timing additions.

Удалить добавленные redundant callback annotations у `.some`, `.map`,
`.filter`, `.flatMap`, `.sort`, если inference проходит. В частности убрать
ручные `: string`, `: ActivationEvidence`, `: SphereScoreV2`, `: RankedEvidence`,
`: number` из callbacks, которые до migration были inferred.

Допустимо оставить настоящий type predicate, если он необходим для narrowing:

```ts
(item): item is ActivationEvidence => ...
```

но parameter type должен выводиться из collection, а не дублироваться без
необходимости.

Если после удаления annotations `tsc` не проходит, вернуть точный error с
source type; не добавлять их обратно молча.

## 4. GRACE R1 всё ещё не выполнен

### 4.1 `lib/grace/api/client.ts`

Заменить module contract:

```text
emitted_logs: none.
failure_policy: Throws ApiError for HTTP failures and ApiContractError for
contract mismatches; network and JSON parsing errors propagate.
```

Не утверждать `day.payload_built`, `system.error`, `log and raise`: таких log
calls в модуле нет.

Перед `ApiContractError` constructor добавить:

```ts
// START_FUNCTION_CONTRACT: F-M-WEB-API-CLIENT.ApiContractError.constructor
// purpose: Construct a safe public error for an invalid Today API payload.
// inputs: none.
// returns: ApiContractError with fixed name/status/code/message.
// side_effects: none.
// emitted_logs: none.
// error_behavior: none.
// END_FUNCTION_CONTRACT: F-M-WEB-API-CLIENT.ApiContractError.constructor
```

### 4.2 `lib/contracts/today.ts`

Текущий placeholder всё ещё присутствует:

```text
Manual V2 schemas removed - imported ...
```

Заменить на named block:

```ts
// START_BLOCK: GENERATED_V2_WIRE_SCHEMA_ALIAS
// Today V2 wire validation is generated from Pydantic/OpenAPI and re-exported
// through the stable runtime barrel; this UI module does not redeclare its shape.
export const TodayV2BlockSchema = TodayV2BlockWireSchema
// END_BLOCK: GENERATED_V2_WIRE_SCHEMA_ALIAS
```

Module map semantic block назвать точно так же либо согласовать name без
расхождения.

### 4.3 Timing helper contract

Уточнить:

```text
error_behavior: invalid activeFrom/activeUntil preview values become undefined;
exactAt remains the generated typed value.
```

## 5. Обязательные gates R3

```bash
pnpm contracts:check

npx vitest run \
  __tests__/api/grace-client.test.ts \
  __tests__/lib/adapt-payload.test.ts \
  __tests__/lib/presentation/today-v2.test.ts \
  __tests__/contracts/generated-runtime.test.ts \
  __tests__/contracts/today.test.ts \
  __tests__/contracts/today-redeclaration-guard.test.ts \
  __tests__/components/TodayScreen.v2-downstream.test.tsx \
  __tests__/guardrails/no-runtime-mocks.test.ts

npx tsc --noEmit
git diff HEAD --check

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

git diff HEAD -- components/today/dev-audit-drawer.tsx
git diff HEAD -- components/today/why-expanded.tsx
rg -n 'TodayV2BlockSchema\.(parse|safeParse)' lib/adapters/today-payload.ts
```

Ожидания:

```text
forbidden scan: no output, exit 1 from rg is expected
dev-audit diff: empty
why-expanded diff: empty
adapter V2 parse scan: no output
all tests/contracts/tsc/diff-check: PASS
```

## 6. Callback

```text
READY_S1_W2_WIRE_MIGRATION_R3
adapter_test_count: <vitest executed count>
presentation_test_count: <vitest executed count>
client_success_fixture: generated runtime parsed
raw_payload_sentinel_leak: NO
forbidden_cast_scan_matches: 0
dev_audit_diff: EMPTY
why_expanded_diff: EMPTY
redundant_callback_annotations_removed: YES
client_grace_contract_truthful: YES
v2_alias_named_block: YES
adapter_v2_parse_calls: 0
contracts_check: PASS
tsc: PASS
commit: NOT_YET
push: NOT_YET```