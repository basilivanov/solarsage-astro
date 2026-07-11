# Стадия 1 ТЗ — единый контракт, generated runtime schemas и baseline

Master:

```text
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/00_MASTER_TZ.md
```

Режим: выполнять волны строго последовательно. После каждой волны callback без
commit/push; commit разрешает архитектор после review.

## S1.W0 — Preserve accepted preview baseline

### Цель

Сохранить уже принятый human-first frontend/dev fixture результат в чистом
feature-branch checkpoint до начала contract/backend изменений.

### Текущее состояние

- `main` является предком текущей preview-ветки;
- preview branch уже содержит 16 committed changes поверх main;
- worktree содержит принятые, но незакоммиченные timing/status/dev-fixture edits;
- рядом есть unrelated untracked paths, которые нельзя stage.

### Обязательная работа

1. Полностью прочитать master и это ТЗ.
2. Снять `git status --short`, `git diff HEAD --stat`, `git diff HEAD --check`.
3. Не reset/checkout существующий worktree.
4. Проверить новые code files на GRACE:
   - `e2e/dev-timing-fixture.spec.ts`;
   - `e2e/dev-visible-sphere-status.spec.ts`;
   - route/hook dev fixture files;
   - любые другие новые `.ts/.tsx/.py` этого preview diff.
5. Для новых E2E files добавить полноценные:
   - `AI_HEADER`;
   - `START_MODULE_CONTRACT`;
   - `START_MODULE_MAP`;
   - реальные side effects (browser navigation, screenshot writes);
   - owned tests/artifacts.
6. Не менять уже принятую UI copy/верстку без обнаруженной регрессии.
7. Убедиться, что test-only fixture не активируется без exact dev path/query.
8. Проверить, что `next-env.d.ts`, `tsconfig.json`, build dirs не содержат
   generated noise.

### Stage allowlist

Разрешено stage только файлы, относящиеся к принятому preview и этой программе:

```text
__tests__/components/TodayScreen.v2-downstream.test.tsx
__tests__/api/dev-timing-fixture-route.test.ts
app/(grace)/day/[date]/page.tsx
app/(grace)/layout.tsx
app/api/dev-fixtures/three-horizon-timing/route.ts
components/today/concrete-day-advice.tsx
components/today/today-screen.tsx
components/today/week-strip.tsx
components/today/why-time-horizon-card.tsx
lib/contracts/today.ts
lib/dev-fixtures/use-three-horizon-timing-fixture.ts
e2e/dev-timing-fixture.spec.ts
e2e/dev-visible-sphere-status.spec.ts
e2e/mock-visual/fixtures/day-v2-2026-07-08.ts
e2e/mock-visual/fixtures/json/day-v2-2026-07-08.json
e2e/mock-visual/day-v2.spec.ts-snapshots/*three-horizons*
docs/work/2026-07-11_solarsage-v2-three-horizon-why-preview/**
docs/work/2026-07-11_dev-only-three-horizon-timing-fixture-preview/**
docs/work/2026-07-11_preview-visible-sphere-status-labels/**
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/**
```

Explicitly forbidden:

```text
.grace/
artifacts/design/
docs/superpowers/plans/2026-07-05-fix-day-route-auth-build.md
grace.db
skills/
```

### Gates

```bash
npx vitest run \
  __tests__/api/dev-timing-fixture-route.test.ts \
  __tests__/components/TodayScreen.v2-downstream.test.tsx \
  __tests__/guardrails/no-runtime-mocks.test.ts
npx tsc --noEmit
git diff HEAD --check
E2E_BASE_URL=http://127.0.0.1:3003 \
  npx playwright test \
    e2e/dev-timing-fixture.spec.ts \
    e2e/dev-visible-sphere-status.spec.ts \
    --project=mobile
NEXT_DIST_DIR=.next-s1w0-proof pnpm build
```

После build восстановить generated `next-env.d.ts`/`tsconfig.json` byte-for-byte
и удалить только `.next-s1w0-proof`.

### Callback

```text
READY_S1_W0_BASELINE
head: <sha>
allowlist_diff: <files>
forbidden_paths_staged: NO
tests: <results>
build: <result>
preview_3003: <result>
commit: NOT_YET
push: NOT_YET
```

После `ACCEPTED_S1_W0` архитектор разрешит commit:

```text
feat(today): preserve human-first v2 horizon preview baseline
```

и push текущей preview branch.

---

## S1.W1 — Generated runtime Zod schemas

### Цель

Расширить существующий Pydantic → OpenAPI → TypeScript pipeline так, чтобы
runtime wire validators тоже генерировались, а не описывались вручную.

### Tool decision

Использовать pinned:

```text
openapi-zod-client 1.18.3
```

Добавить как `devDependency`, обновить `pnpm-lock.yaml`.

Использовать schemas-only custom Handlebars template, основанный на официальном
schemas-only режиме. Не генерировать и не подключать Zodios API client.

### Files

Ожидаемые новые/изменённые files:

```text
scripts/contracts/generate.sh
scripts/contracts/templates/zod-schemas.hbs
packages/contracts/_generated.zod.ts
packages/contracts/runtime.ts
package.json
pnpm-lock.yaml
__tests__/contracts/generated-runtime.test.ts
```

### Generation contract

`scripts/contracts/generate.sh` выполняет:

```text
1. Pydantic -> openapi.json
2. openapi.json -> _generated.ts
3. openapi.json -> _generated.zod.ts
4. deterministic banners/formatting
```

Pinned command по смыслу:

```bash
openapi-zod-client@1.18.3 \
  packages/contracts/openapi.json \
  --output packages/contracts/_generated.zod.ts \
  --template scripts/contracts/templates/zod-schemas.hbs \
  --export-schemas
```

Точный CLI wrapper может быть `pnpm exec`, но версия обязана фиксироваться
lockfile/devDependency, не `latest`.

### Generated artifact invariants

`_generated.zod.ts`:

- autogenerated banner;
- imports only `zod` for runtime schema output;
- no `@zodios/core` runtime import;
- no HTTP client/endpoints;
- exports component schemas by stable names or through a stable `schemas` map;
- contains `TodayPayload`, `TodayV2Block`, `ActivationEvidence` runtime schemas;
- idempotent byte-for-byte;
- not manually edited.

`packages/contracts/runtime.ts` is handwritten stable barrel and exports:

```ts
TodayPayloadWireSchema
TodayV2BlockWireSchema
ActivationEvidenceWireSchema
```

The existing `packages/contracts/index.ts` stays types-only. Do not mix runtime
values into that barrel.

### Forward compatibility

Generated object schemas must not reject unknown additive fields from a newer
backend during rolling deployment. Do not enable global strict-object rejection.
Required known fields still validate.

### Drift gate

Update scripts:

```text
contracts:generate
contracts:check
```

`contracts:check` must diff:

```text
packages/contracts/openapi.json
packages/contracts/_generated.ts
packages/contracts/_generated.zod.ts
```

Run generator twice and prove second run has zero diff.

### Tests

`generated-runtime.test.ts` must prove:

- generated TodayPayload schema parses a canonical valid API payload;
- missing required root field is rejected;
- V2 nested activation fields are validated;
- an unknown additive field does not reject the payload;
- generated runtime schema output exists in contract drift allowlist.

### Gates

```bash
pnpm contracts:generate
pnpm contracts:generate
git diff HEAD --check
pnpm contracts:check
npx vitest run __tests__/contracts/generated-runtime.test.ts
npx tsc --noEmit
```

### Callback

```text
READY_S1_W1_RUNTIME_CODEGEN
generator_version: 1.18.3
generated_exports: <list>
zodios_runtime_dependency: NO
idempotence: PASS
contracts_check: PASS
tests: <results>
commit: NOT_YET
push: NOT_YET
```

Suggested commit after acceptance:

```text
feat(contracts): generate runtime zod schemas from openapi
```

---

## S1.W2 — Migrate raw Today V2 validation to generated wire schemas

### Цель

Удалить ручное повторение raw API V2 shape из frontend contract layer.

### Boundary rule

Raw API payload validates exactly once at the API client/adapter boundary with
`TodayPayloadWireSchema`.

After validation:

- generated TypeScript wire types describe raw payload;
- adapter transforms it into UI-only `AdaptedTodayPayload`;
- UI components never receive `unknown` raw JSON.

### Required changes

1. Find canonical day fetch boundary in `lib/grace/api/client.ts` / adapter path.
2. Parse raw response using generated `TodayPayloadWireSchema` before returning
   a typed wire payload.
3. Define a typed contract error with safe logging and no payload/PII dump.
4. In `lib/contracts/today.ts` remove raw-wire duplicates for:
   - `TodayV2Block`;
   - `TodayV2ActivatedTarget`;
   - `TodayV2ActivationSummary`;
   - `TodayV2WhyTodayItem`;
   - `TodayV2Audit`;
   - `ActivationEvidence`;
   - `SphereScoreV2`, when it is a raw wire duplicate.
5. Import generated wire types instead.
6. Keep Zod only for genuinely adapted UI structures (`TodayNote`, transformed
   why sections, UI-only defaults) if needed.
7. `adaptTodayPayload` must be a typed pure transform, not a second raw wire
   validator.
8. No `as any`, double casts or silently swallowed schema errors.

### Compatibility

The accepted current payload and visual fixtures must continue to render.

### Tests

- raw valid API payload passes generated validator;
- malformed V2 nested payload fails at fetch/adapter boundary;
- adapted payload maintains current rendering;
- no manual raw V2 schema declaration remains;
- guard test rejects future raw V2 redeclaration in `lib/contracts/today.ts`.

### Gates

```bash
pnpm contracts:check
npx vitest run \
  __tests__/contracts/generated-runtime.test.ts \
  __tests__/contracts/today.test.ts \
  __tests__/components/TodayScreen.v2-downstream.test.tsx \
  __tests__/guardrails/no-runtime-mocks.test.ts
npx tsc --noEmit
git diff HEAD --check
```

### Callback

```text
READY_S1_W2_WIRE_MIGRATION
raw_validation_boundary: <file:function>
manual_v2_wire_duplicates: 0
adapter_type: <type>
tests: <results>
commit: NOT_YET
push: NOT_YET
```

Suggested commit after acceptance:

```text
refactor(today): consume generated v2 wire contracts
```

---

## S1.W3 — One-source contract fixtures and round-trip proof

### Цель

Fixture data остаётся тестовым инструментом, но больше не поддерживается вручную
одновременно в TS и JSON.

### Required design

1. Канонический visual fixture content живёт в одном JSON file.
2. TS wrapper не содержит копию объекта; он импортирует JSON и validates it with
   generated `TodayPayloadWireSchema`.
3. Добавить backend script, который может:
   - load JSON;
   - validate through Pydantic `TodayPayload.model_validate`;
   - emit normalized camelCase JSON deterministically.
4. Добавить `--check` mode, который не пишет и возвращает non-zero on drift.
5. Do not generate human visual copy from random/live LLM.
6. Dev endpoint may serve this test oracle only after existing dev/local guards.
7. Production runtime never imports fixture data before dev guard.

### Round-trip invariant

```text
JSON visual fixture
  -> Pydantic TodayPayload validation
  -> deterministic model dump by_alias=True
  -> generated Zod TodayPayload validation
  -> frontend adapter
```

No data loss for V2 IDs, timing or verdict states.

### Tests

- Pydantic validates fixture;
- generated Zod validates the same fixture;
- round-trip activation ID sets are equal;
- there is only one payload object source;
- existing visual specs pass without update after migration;
- dev route/local guards pass.

### Gates

```bash
apps/api/.venv/bin/python scripts/contracts/normalize_today_fixture.py \
  e2e/mock-visual/fixtures/json/day-v2-2026-07-08.json --check
pnpm contracts:check
npx vitest run
E2E_BASE_URL=http://127.0.0.1:3003 \
  npx playwright test e2e/mock-visual/day-v2.spec.ts --project=mobile
npx tsc --noEmit
git diff HEAD --check
```

### Stage 1 acceptance callback

```text
READY_STAGE_1_CONTRACT_FOUNDATION
commits: <wave SHAs>
pydantic_source_of_truth: YES
generated_ts: PASS
generated_zod: PASS
runtime_boundary_migrated: YES
single_fixture_source: YES
contracts_check: PASS
full_frontend_tests: <result>
build: <result>
commit: NOT_YET_FOR_W3
push: NOT_YET_FOR_W3
```

Suggested W3 commit after acceptance:

```text
test(contracts): prove today v2 fixture round trip
```
