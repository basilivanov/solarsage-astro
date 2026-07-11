# S1.W2 Architecture Review R1 — generated Today wire boundary

Дата: 2026-07-11

Вердикт: **REWORK REQUIRED**. Commit/push запрещены. S1.W3 не начинать.

Исходные обязательные документы:

```text
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/10_STAGE_1_CONTRACT_FOUNDATION_TZ.md
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/19_S1_W2_TYPE_BOUNDARY_GUIDANCE.md
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/20_S1_W2_PREVIEW_TIMING_BRIDGE.md
```

## 1. Что уже принято по направлению

Следующие решения правильные и должны сохраниться:

1. `packages/contracts/index.ts` остаётся types-only barrel и экспортирует V2
   aliases через `components["schemas"][...]`.
2. `fetchDay` читает `res.json()` как `unknown`, вызывает
   `TodayPayloadWireSchema.safeParse` и возвращает `parsed.data` без cast.
3. Contract failure представлен отдельным `ApiContractError` со следующими
   публичными значениями:

   ```text
   name: ApiContractError
   status: 502
   code: SCHEMA_VALIDATION_ERROR
   ```

4. `adaptTodayPayload` больше не вызывает V2 `parse/safeParse`; V2 проходит
   через адаптер по identity.
5. Ручные V2 `z.object` declarations удалены из `lib/contracts/today.ts`, а
   `TodayV2BlockSchema = TodayV2BlockWireSchema` допустим.
6. Timing compatibility находится только в presentation helper и не расширяет
   canonical wire types до S2.W1.
7. Redeclaration guard по смыслу правильный.

Эти решения не откатывать.

## 2. Blocking finding A — удалено существующее регрессионное покрытие

Текущий diff заменил:

```text
__tests__/lib/adapt-payload.test.ts
  HEAD: 26 tests
  current: 1 test
  diff: +34 / -523

__tests__/lib/presentation/today-v2.test.ts
  HEAD: 18 tests
  current: 4 tests
  diff: +75 / -370
```

Контрактная миграция не имеет права удалять доказательства access mapping,
fallbacks, legacy payload, human copy, horizon ranking, thresholds, durations,
education copy и sanitization.

### 2.1 Adapter suite

Восстановить из `HEAD` все прежние неустаревшие adapter tests и добавить
identity proof. Не использовать destructive checkout/reset; `git show
HEAD:<path>` допустим только как read-only reference.

Должны остаться доказанными как минимум:

- все 6 access mapping cases;
- notes real/fallback cases;
- headline/dayStatus/topFlags preservation;
- day chart, planet influences, sphere scores preservation;
- missing topFlags fallback;
- why paragraphs/bullets/empty mapping;
- reading and keyInsight fallbacks;
- adapted UI schema validation;
- legacy payload без V2 не фабрикует V2;
- contract-valid V2 проходит по identity:
  `adapted.payload.v2 === input.v2`.

Два старых теста должны быть не просто удалены, а заменены на новом правильном
слое:

1. «adapter заполняет generated defaults» больше не относится к адаптеру —
   defaults доказываются generated runtime/fetch boundary tests;
2. «malformed V2 throws in adapter» больше не относится к адаптеру — это уже
   обязанность `fetchDay` и `ApiContractError` test.

Ожидаемый adapter suite после миграции: не менее **24 содержательных tests**.

### 2.2 Presentation suite

Восстановить все 18 прежних presentation tests и поверх них добавить timing
bridge tests. Должны остаться проверки:

- technique/planet/aspect/phase/sphere localization;
- `Transit_` / `Natal_` cleanup и русские падежи;
- suppression raw English contribution text;
- technique deduplication и evidence selection;
- human navigator labels и safe why copy;
- long/medium/fast classification, ranking, thresholds и limits;
- duration/stage labels;
- definitions для всех известных techniques/planets;
- weak/unrelated evidence exclusion.

Поверх baseline добавить 4 timing bridge cases. Ожидаемый presentation suite:
не менее **22 tests**.

## 3. Blocking finding B — `as any` в новых timing tests

Сейчас `__tests__/lib/presentation/today-v2.test.ts` содержит четыре
`mockEvidence as any`. Это прямо запрещено guidance.

Использовать contract-typed evidence из canonical fixture:

```ts
const evidence = dayPayloadV2.v2?.activationEvidence.find(
  (item) => item.id === "act-pluto-trine-saturn",
)
expect(evidence).toBeDefined()
if (!evidence) throw new Error("fixture evidence is missing")
```

Для invalid additive fields создать новый объект без cast, например:

```ts
const invalidTiming = Object.assign(structuredClone(evidence), {
  activeFrom: 123,
  activeUntil: ["2026-07-18"],
})
```

Он структурно совместим с `ActivationEvidence`, а дополнительные поля reader
получает через `Reflect.get`.

Не тестировать invalid numeric `exactAt`: это canonical typed property, а не
preview extension. Для `exactAt` доказать string/null/undefined preservation.
Invalid-type filtering относится только к `activeFrom/activeUntil`.

После исправления в изменённых S1.W2 tests не должно быть `as any`, double
casts, `@ts-ignore`, `@ts-expect-error`.

## 4. Client boundary tests — сделать typed и доказать safe error

### 4.1 Valid payload

Не использовать `JSON.parse(JSON.stringify(...))`: он превращает fixture в
implicit `any` и требует ручного удаления полей.

Для contract-valid expected fixture допустимо один раз в test setup получить
generated result:

```ts
const contractPayload = TodayPayloadWireSchema.parse(dayPayloadV2)
```

После этого mock возвращает `contractPayload`, а `fetchDay` возвращает тот же
contract-valid shape. Test-side parse не является production boundary и не
нарушает правило «production validates once».

### 4.2 Malformed nested V2 and sentinel

Malformed payload должен содержать уникальный marker, например:

```text
RAW_PAYLOAD_SENTINEL_DO_NOT_LEAK
```

Проверить через `rejects.toBeInstanceOf` / `rejects.toMatchObject`, без cast,
что error:

```text
instanceof ApiContractError
name = ApiContractError
status = 502
code = SCHEMA_VALIDATION_ERROR
message = exact generic message
```

И отдельно доказать, что `message` не содержит:

- sentinel;
- `activationEvidence`;
- Zod issue path/details.

Существующие HTTP behavior tests 401/404/422/network/statusText сохранить.

## 5. Убрать type-noise из product diff

После перехода на aliases generated TypeScript types уже описывают массивы и
records. Не размазывать ручные callback annotations по UI.

### 5.1 `components/today/why-expanded.tsx`

Убрать inline annotations вида:

```ts
(item: import("@/packages/contracts").ActivationEvidence) => ...
```

Сначала проверить обычный inference. Если конкретная аннотация действительно
необходима, использовать один top-level `import type`, но не inline import в
трёх callbacks.

### 5.2 `lib/presentation/today-v2.ts`

Убрать добавленные только ради подавления inference annotations у `.map`,
`.filter`, `.some`, `.sort`, `.flatMap`, если `tsc` проходит без них. Оставлять
явный тип допустимо только там, где он реально уточняет boundary/type guard.

Не добавлять casts для компенсации ошибки. Если после чистого generated import
остаётся compile mismatch — остановиться и вернуть точный TypeScript error с
типами source/target.

### 5.3 `components/today/dev-audit-drawer.tsx`

С generated `TodayV2Audit.canonVersions` value имеет тип `string`. Если после
чистых imports `tsc` проходит, полностью убрать текущий unrelated safeVal diff.
Если ошибка реально остаётся, оформить отдельный named pure formatter с
правдивым контрактом; не рендерить unknown и не печатать raw object/PII.

## 6. Timing bridge implementation

Текущий helper по направлению правильный. Сохранить следующие invariants:

- `exactAt` читается typed;
- `activeFrom/activeUntil` читаются только через `Reflect.get`;
- string/null сохраняются;
- invalid additive values становятся `undefined`;
- input не мутируется;
- consumer использует один helper;
- никаких timing additions в `packages/contracts/index.ts`,
  `packages/contracts/runtime.ts`, `lib/contracts/today.ts`;
- bridge помечен как temporary until S2.W1.

Уточнить function contract: invalid-type behavior относится к additive preview
fields, а не к typed `exactAt`.

## 7. GRACE correctness

### 7.1 `lib/grace/api/client.ts`

Текущий module contract утверждает:

```text
emitted_logs: day.payload_built, system.error
failure_policy: log and raise
```

Но модуль эти события не пишет. Сделать правдиво:

```text
emitted_logs: none
failure_policy: throws ApiError for HTTP failures and ApiContractError for
contract mismatches; network/JSON errors propagate
```

Добавить contract для public `ApiContractError`/constructor по repository GRACE
convention. Не придумывать лог-события и не логировать raw payload/Zod issues.

### 7.2 `lib/contracts/today.ts`

Удалить placeholder-комментарий:

```text
Manual V2 schemas removed - imported ...
```

Вместо него оформить named block/contract comment для generated wire schema
alias. Module map уже заявляет `WIRE_SCHEMAS_IMPORT`, код должен соответствовать
карте.

### 7.3 Tests

Test module contracts не должны утверждать, что весь adapter/presentation
behavior покрыт, если suite фактически свёрнут. После восстановления перечислить
реальные semantic blocks/invariants.

## 8. Независимые gates перед callback R2

Запустить:

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

rg -n 'TodayV2BlockSchema\.(parse|safeParse)' lib/adapters/today-payload.ts
```

Ожидания:

```text
contracts_check: PASS
focused tests: PASS
adapter tests: >=24
presentation tests: >=22
tsc: PASS
diff_check: PASS
forbidden cast scan: 0
adapter V2 parse scan: 0
commit: NOT_YET
push: NOT_YET
```

## 9. Callback

Вернуть:

```text
READY_S1_W2_WIRE_MIGRATION_R2
adapter_test_count: <n>
presentation_test_count: <n>
restored_regression_coverage: YES
typed_contract_error: ApiContractError/502/SCHEMA_VALIDATION_ERROR
raw_payload_sentinel_leak: NO
fetch_return_casts: 0
adapter_v2_parse_calls: 0
adapter_v2_identity_test: PASS
preview_timing_bridge: presentation-only
manual_wire_timing_extension: NO
manual_v2_wire_duplicates: 0
forbidden_cast_scan: 0
contracts_check: PASS
tsc: PASS
commit: NOT_YET
push: NOT_YET```