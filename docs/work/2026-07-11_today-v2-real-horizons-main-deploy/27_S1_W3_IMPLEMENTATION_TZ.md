# S1.W3 Implementation ТЗ — one-source fixture, round-trip and contract workflow

Дата: 2026-07-11

Ветка:

```text
preview/solarsage-v2-human-first-navigator-ux
```

Ожидаемый starting HEAD:

```text
5ffeebac283f3a95a11f122c7b0ef35923cefecf
```

Режим: выполнить всю волну, проверить и вернуть callback. До architect review
commit/push запрещены. S2.W1 не начинать.

Обязательно полностью прочитать:

```text
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/00_MASTER_TZ.md
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/10_STAGE_1_CONTRACT_FOUNDATION_TZ.md
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/26_S1_W3_ARCHITECTURE_AMENDMENT.md
```

## 1. Итог волны

После S1.W3 изменение контракта и fixture должно выглядеть так:

```text
edit Pydantic schema
  -> pnpm contracts:generate
  -> edit one canonical JSON fixture if needed
  -> pnpm contracts:fixture:normalize
  -> pnpm contracts:check
  -> TypeScript/runtime validators/CI show every affected consumer
```

Ручных копий одного payload в TS и JSON больше нет.

Canonical visual payload source:

```text
e2e/mock-visual/fixtures/json/day-v2-2026-07-08.json
```

Round-trip:

```text
canonical JSON
  -> strict API TodayPayload.model_validate
  -> deterministic camelCase model_dump
  -> generated TodayPayloadWireSchema
  -> frontend adaptTodayPayload
  -> visual/dev fixture consumers
```

Обязательная сохранность:

- activation IDs и все ссылки на них;
- `activeFrom/exactAt/activeUntil` values;
- concrete advice `key -> verdict` states;
- видимый human copy;
- существующие visual snapshots.

## 2. Начальный audit

Снять и записать в callback:

```bash
git status --short --branch
git rev-parse HEAD
git diff HEAD --check
```

Не трогать unrelated untracked paths:

```text
.grace/
artifacts/design/
docs/superpowers/plans/2026-07-05-fix-day-route-auth-build.md
grace.db
skills/
```

Не использовать reset/checkout для всего worktree.

## 3. Contract-only timing fields prerequisite

Строго по architecture amendment добавить в обе schemas:

```text
apps/api/app/schemas/activation.py
apps/solarsage/solarsage/schemas/activation.py
```

Порядок fields:

```py
applying: bool | None = None
active_from: str | None = None
exact_at: str | None = None
active_until: str | None = None
phase: ActivationPhase = "background"
```

Это только additive optional contract. Не писать producer/solver logic.

Запрещено в S1.W3:

- заполнять эти fields в services;
- менять calculation/activation/scoring/content versions;
- добавлять approximation по speed/orb;
- менять phase logic;
- начинать transit timing service.

### 3.1 API schema tests

В `apps/api/tests/test_activation_contracts.py`:

- minimal evidence даёт все три timing fields `None`;
- full evidence принимает `active_from/exact_at/active_until`;
- `model_dump(mode="json", by_alias=True)` выдаёт
  `activeFrom/exactAt/activeUntil` без потери values;
- invalid unknown field по-прежнему rejected через `extra="forbid"`, если такой
  proof отсутствует рядом — добавить focused case.

### 3.2 Sidecar schema tests

В `apps/solarsage/tests/test_activation_schema.py`:

- minimal evidence даёт fields `None`;
- full timing values round-trip через model dump;
- никаких calculation assertions в этой волне.

## 4. Regenerate generated contracts

После schema edit:

```bash
pnpm contracts:generate
```

Generated artifacts должны включить camelCase fields:

```text
packages/contracts/openapi.json
packages/contracts/_generated.ts
packages/contracts/_generated.zod.ts
```

Не редактировать их вручную.

Проверить:

```text
generated TS ActivationEvidence:
  activeFrom?: string | null
  exactAt?: string | null
  activeUntil?: string | null

generated Zod ActivationEvidence:
  validates all three known fields
  rejects wrong known field type
```

## 5. Backend fixture normalizer

Создать:

```text
scripts/contracts/normalize_today_fixture.py
```

Новый файл обязан иметь полноценные Python GRACE:

- `AI_HEADER`;
- named `START_MODULE_CONTRACT`;
- named `START_MODULE_MAP`;
- `START_BLOCK`;
- contracts у public/non-trivial functions.

### 5.1 CLI

Поддержать:

```bash
apps/api/.venv/bin/python scripts/contracts/normalize_today_fixture.py \
  e2e/mock-visual/fixtures/json/day-v2-2026-07-08.json

apps/api/.venv/bin/python scripts/contracts/normalize_today_fixture.py \
  e2e/mock-visual/fixtures/json/day-v2-2026-07-08.json --check
```

Path — required positional argument. `--check` не пишет.

### 5.2 Validation and serialization

Алгоритм фиксирован:

1. Прочитать UTF-8 JSON.
2. Root обязан быть JSON object.
3. Валидировать через canonical
   `apps/api/app/schemas/today.py::TodayPayload.model_validate`.
4. Dump:

   ```py
   model.model_dump(
       mode="json",
       by_alias=True,
       exclude_unset=True,
   )
   ```

5. Render:

   ```py
   json.dumps(
       normalized,
       ensure_ascii=False,
       sort_keys=True,
       indent=2,
   ) + "\n"
   ```

6. Normal mode пишет atomically через sibling temp file + `Path.replace`.
7. `--check` сравнивает exact bytes, ничего не пишет:
   - clean -> exit 0;
   - valid but non-normalized/drift -> exit 1;
   - invalid JSON/Pydantic/IO -> non-zero typed failure.

Не выводить raw payload, human copy, full ValidationError input или PII.
При Pydantic error вывести только sanitized locations и error types через
`errors(include_input=False, include_url=False)`.

Допустимо печатать:

- relative path;
- clean/drift status;
- byte count;
- SHA-256 normalized bytes.

Никаких network/LLM calls.

## 6. Portable fixture command and unified check

Создать shell wrapper:

```text
scripts/contracts/today_fixture.sh
```

Он:

- определяет repo root;
- предпочитает `apps/api/.venv/bin/python`, иначе `${PYTHON:-python3}`;
- всегда передаёт canonical JSON path;
- прозрачно forwards `--check`;
- имеет truthful GRACE header/contract/map;
- использует `set -euo pipefail`.

Создать:

```text
scripts/contracts/check.sh
```

Порядок:

```text
1. bash scripts/contracts/generate.sh
2. bash scripts/contracts/today_fixture.sh --check
3. git diff --exit-code --
     packages/contracts/openapi.json
     packages/contracts/_generated.ts
     packages/contracts/_generated.zod.ts
```

`check.sh` не нормализует fixture автоматически: drift должен падать с
инструкцией запустить explicit normalize command.

Обновить `package.json` scripts:

```json
"contracts:generate": "bash scripts/contracts/generate.sh",
"contracts:fixture:normalize": "bash scripts/contracts/today_fixture.sh",
"contracts:fixture:check": "bash scripts/contracts/today_fixture.sh --check",
"contracts:check": "bash scripts/contracts/check.sh"
```

Не добавлять dependency и не менять lockfiles без фактической причины.

## 7. Сделать JSON единственным payload object source

Canonical file:

```text
e2e/mock-visual/fixtures/json/day-v2-2026-07-08.json
```

После schema generation запустить:

```bash
pnpm contracts:fixture:normalize
pnpm contracts:fixture:normalize
```

Второй запуск обязан дать byte-identical file.

Human copy, IDs, timing и verdict values не переписывать и не генерировать.
Разрешены только deterministic format/order и Pydantic alias normalization.

JSON должен завершаться ровно одним newline.

## 8. Переписать TypeScript fixture в thin wrapper

Полностью удалить ручной payload object из:

```text
e2e/mock-visual/fixtures/day-v2-2026-07-08.ts
```

Wrapper обязан:

1. импортировать canonical JSON;
2. импортировать `TodayPayload` только из public types barrel;
3. импортировать `TodayPayloadWireSchema` только из public runtime barrel;
4. fail-loud validate JSON при module load;
5. экспортировать typed `dayPayloadV2`;
6. сохранить derived `minimalDayPayloadForDate` без второго payload source.

Целевая форма по смыслу:

```ts
import rawDayPayloadV2 from "./json/day-v2-2026-07-08.json"
import type { TodayPayload } from "../../../packages/contracts"
import { TodayPayloadWireSchema } from "../../../packages/contracts/runtime"

export const dayPayloadV2: TodayPayload =
  TodayPayloadWireSchema.parse(rawDayPayloadV2)
```

Не импортировать `_generated.ts`/`_generated.zod.ts` напрямую.
Не использовать cast, `any`, `satisfies` для обхода mismatch или второй manual
interface.

`minimalDayPayloadForDate(date)`:

- остаётся pure derived function;
- строится только из `dayPayloadV2`;
- не читает второй JSON;
- сохраняет существующую семантику соседнего дня;
- получает canonical function contract.

Обновить module contract/map wrapper: input — canonical JSON; output — validated
fixture and derived neighbour builder; failure policy — import throws on invalid
contract.

## 9. Frontend timing projection после typed contract

В `lib/presentation/today-v2.ts` больше не использовать `Reflect.get` для
timing.

Сохранить текущий consumer API `getEvidenceTimingPreview`, но превратить его в
обычную typed projection:

```ts
export function getEvidenceTimingPreview(
  evidence: ActivationEvidence | null | undefined,
): EvidenceTimingPreview {
  return {
    activeFrom: evidence?.activeFrom,
    exactAt: evidence?.exactAt,
    activeUntil: evidence?.activeUntil,
  }
}
```

Обновить module map/function contract:

- не называть helper temporary additive bridge;
- no mutation;
- invalid known types rejected раньше на generated wire boundary.

В `__tests__/lib/presentation/today-v2.test.ts`:

- сохранить string/null/undefined/no-mutation cases;
- удалить case с искусственными number/array hidden extras;
- не использовать casts.

Добавить generated runtime proof, что `activeFrom: 123` rejected.

## 10. Backend round-trip tests

Создать:

```text
apps/api/tests/test_today_fixture_contract.py
```

Полный GRACE header/contract/map обязателен.

Тесты:

1. canonical JSON проходит strict `TodayPayload.model_validate`;
2. normalized `model_dump(mode="json", by_alias=True, exclude_unset=True)`
   содержит camelCase timing;
3. raw -> normalized activation ID order и set равны;
4. timing map
   `id -> (activeFrom, exactAt, activeUntil)` равен;
5. verdict map `row.key -> row.verdict` равен;
6. normalizer `--check`/pure check function возвращает clean;
7. drifted whitespace/order copy в temp dir даёт check failure и не изменяет
   файл;
8. normalize temp copy дважды даёт byte-identical result;
9. invalid fixture error не печатает test sentinel/raw input.

Не создавать второй committed normalized artifact.

## 11. Frontend round-trip and single-source tests

Создать:

```text
__tests__/contracts/today-fixture-roundtrip.test.ts
```

Полный GRACE header/contract/map обязателен.

Tests:

1. raw JSON проходит `TodayPayloadWireSchema`;
2. wrapper `dayPayloadV2` равен generated parsed JSON result;
3. activation IDs сохраняются;
4. timing map сохраняется;
5. concrete advice verdict map сохраняется;
6. every referenced activation ID существует в evidence set для:
   - `activationSummary.topActivatedTargets[].activationIds`;
   - `whyToday[].activationIds`;
   - `concreteAdvice.rows[].evidence[].activationId`, когда присутствует;
   - score contributions с `source === "activation"`;
7. wrong known timing type rejected generated Zod;
8. `adaptTodayPayload(dayPayloadV2).payload.v2 === dayPayloadV2.v2`;
9. source guard доказывает:
   - wrapper импортирует exact JSON path;
   - wrapper вызывает `TodayPayloadWireSchema.parse`;
   - wrapper не содержит `HERO_HEADLINE`, `previewTiming` или manual
     `dayPayloadV2 = { ... }`;
   - only one committed visual payload JSON source exists for this fixture.

No `any`, double casts или suppression directives.

## 12. Dev route isolation guard — исправить точно, не ослаблять

Текущий full Vitest baseline:

```text
94 files total
92 passed / 2 failed files
971 passed / 3 failed tests
```

Один failure:

```text
__tests__/guardrails/preview-isolation.test.ts
```

Причина: старый blanket scanner запрещает даже намеренный guarded dynamic import
в единственном dev-only route.

Существенно переписать этот test file с GRACE header/contract/map.

Правила нового guard:

1. Во всех product paths fixture imports запрещены.
2. Единственное исключение:

   ```text
   app/api/dev-fixtures/three-horizon-timing/route.ts
   -> ../../../../e2e/mock-visual/fixtures/day-v2-2026-07-08
   ```

3. Исключение разрешено только как dynamic `await import(...)`, не static
   import/from/require.
4. Source ordering test доказывает, что import находится после проверок:
   - `NODE_ENV === development`;
   - `isLocalDevHost`;
   - `hasUnsafeProxyOriginHeaders`;
   - guard branch с 404 return.
5. Любой второй route/path/import снова является violation.
6. Existing `__tests__/api/dev-timing-fixture-route.test.ts` остаётся зелёным и
   local dev response содержит typed timing values.

Не добавлять широкий regex skip для `app/api` или `dev-fixtures` directory.

## 13. Исправить два baseline day-page tests

Два остальных full-suite failures находятся в:

```text
__tests__/app/day-page.test.tsx
```

Причина: после accepted preview page использует `useSearchParams`, а test mock
не экспортирует его.

Добавить только корректный mock:

```ts
useSearchParams: () => new URLSearchParams(),
```

Не менять production page и assertions этих tests.

## 14. CI contract gate

Обновить:

```text
.github/workflows/ci.yml
```

Добавить отдельный job `contract-tests`, а не смешивать toolchains с уже
существующими jobs.

Job:

```text
checkout
setup-python 3.11
setup-node 20
npm ci
python -m pip install -e ./apps/api
npm run contracts:check
npx vitest run
  __tests__/contracts/generated-runtime.test.ts
  __tests__/contracts/today-fixture-roundtrip.test.ts
```

Обновить workflow module contract/map dependencies/semantic blocks.

CI не нормализует и не commits fixture; он только проверяет drift.

## 15. Contract developer documentation

Обновить устаревший:

```text
packages/contracts/README.md
```

README обязан отражать текущий pipeline:

```text
Pydantic
 -> openapi.json
 -> _generated.ts
 -> _generated.zod.ts
 -> types/runtime public barrels
 -> single validated JSON fixture
```

Обязательные sections:

1. `Pydantic is the only wire SoT`.
2. `Do not edit generated artifacts`.
3. `Do not redeclare raw wire Zod in frontend`.
4. `How to add/change a field`:

   ```text
   edit Pydantic
   pnpm contracts:generate
   fix compile/runtime consumers
   pnpm contracts:check
   ```

5. `How to edit visual fixture`:

   ```text
   edit one JSON
   pnpm contracts:fixture:normalize
   pnpm contracts:check
   ```

6. Explain `contracts:fixture:check` and CI.
7. Explain production fetch validates once; adapter does not reparse.
8. Explain additive consumer-first fields vs breaking version bump.

Не редактировать superseded historical `docs/05...` как wire source.

## 16. Expected changed files

Ожидаемый allowlist:

```text
.github/workflows/ci.yml
package.json
packages/contracts/README.md
packages/contracts/openapi.json
packages/contracts/_generated.ts
packages/contracts/_generated.zod.ts
apps/api/app/schemas/activation.py
apps/solarsage/solarsage/schemas/activation.py
apps/api/tests/test_activation_contracts.py
apps/api/tests/test_today_fixture_contract.py
apps/solarsage/tests/test_activation_schema.py
scripts/contracts/normalize_today_fixture.py
scripts/contracts/today_fixture.sh
scripts/contracts/check.sh
e2e/mock-visual/fixtures/json/day-v2-2026-07-08.json
e2e/mock-visual/fixtures/day-v2-2026-07-08.ts
lib/presentation/today-v2.ts
__tests__/lib/presentation/today-v2.test.ts
__tests__/contracts/generated-runtime.test.ts
__tests__/contracts/today-fixture-roundtrip.test.ts
__tests__/guardrails/preview-isolation.test.ts
__tests__/api/dev-timing-fixture-route.test.ts
__tests__/app/day-page.test.tsx
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/26_S1_W3_ARCHITECTURE_AMENDMENT.md
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/27_S1_W3_IMPLEMENTATION_TZ.md
```

Если нужен другой tracked file, остановиться и обосновать его в callback; не
расширять scope молча.

Forbidden/unrelated paths не stage.

## 17. Gates — выполнить все

### 17.1 Schema and normalizer

```bash
cd apps/api && .venv/bin/python -m pytest \
  tests/test_activation_contracts.py \
  tests/test_today_fixture_contract.py -q

cd apps/solarsage && python -m pytest tests/test_activation_schema.py -q
```

### 17.2 Determinism

Из repo root:

```bash
pnpm contracts:generate
pnpm contracts:fixture:normalize
sha256sum e2e/mock-visual/fixtures/json/day-v2-2026-07-08.json
pnpm contracts:fixture:normalize
sha256sum e2e/mock-visual/fixtures/json/day-v2-2026-07-08.json
pnpm contracts:fixture:check
pnpm contracts:check
```

Два SHA должны совпасть.

### 17.3 Frontend

```bash
npx vitest run
npx tsc --noEmit
git diff HEAD --check
```

Full Vitest обязан исправить baseline 3 failures; не принимать результат с
known failures.

### 17.4 Browser

```bash
E2E_BASE_URL=http://127.0.0.1:3003 \
  npx playwright test \
    e2e/mock-visual/day-v2.spec.ts \
    e2e/dev-timing-fixture.spec.ts \
    --project=mobile \
    --update-snapshots=none
```

Snapshots не обновлять. Любой visual diff — остановиться и вернуть artifact,
не принимать автоматически.

### 17.5 Production proof build

```bash
NEXT_DIST_DIR=.next-s1w3-proof pnpm build
```

После build:

- удалить только `.next-s1w3-proof`;
- восстановить `next-env.d.ts`/`tsconfig.json` byte-for-byte, если Next их
  автоматически изменил;
- не удалять чужие build dirs.

### 17.6 Final scans

```bash
rg -n '\bas any\b|as unknown as|@ts-ignore|@ts-expect-error' \
  scripts/contracts/normalize_today_fixture.py \
  e2e/mock-visual/fixtures/day-v2-2026-07-08.ts \
  __tests__/contracts/today-fixture-roundtrip.test.ts \
  lib/presentation/today-v2.ts \
  __tests__/lib/presentation/today-v2.test.ts

rg -n 'from .*_generated|import .*_generated' \
  e2e/mock-visual/fixtures/day-v2-2026-07-08.ts

git status --short
git diff HEAD --stat
git diff HEAD --check
```

## 18. Callback

Вернуть без commit/push:

```text
READY_STAGE_1_CONTRACT_FOUNDATION
head: <sha>
commits:
  S1.W0: 5de571a783969f5f26a1cde25c0378e98242388b
  S1.W1: 93c64660593f2cfbd5bc719ea3b7eb2696f4d930
  S1.W2: 5ffeebac283f3a95a11f122c7b0ef35923cefecf
timing_contract_promoted_additively: YES
timing_calculation_implemented: NO
versions_changed: NO
pydantic_source_of_truth: YES
generated_ts: PASS
generated_zod: PASS
runtime_boundary_migrated: YES
single_fixture_source: YES
ts_wrapper_payload_copy: NO
fixture_normalizer_check: PASS
fixture_sha_first: <sha>
fixture_sha_second: <same sha>
activation_ids_preserved: PASS
timing_preserved: PASS
verdicts_preserved: PASS
dev_route_guard: PASS
production_import_before_guard: NO
full_frontend_tests: <files/tests counts>
api_tests: <count>
sidecar_schema_tests: <count>
visual_e2e: <count>
build: PASS
contracts_check: PASS
tsc: PASS
diff_check: PASS
changed_files: <exact list>
forbidden_paths_staged: NO
commit: NOT_YET_FOR_W3
push: NOT_YET_FOR_W3
```

Suggested commit после architect acceptance:

```text
test(contracts): prove today v2 fixture round trip
```
