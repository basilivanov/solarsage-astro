# S1.W2 Acceptance — generated Today V2 wire boundary

Дата: 2026-07-11

Статус: **ACCEPTED_S1_W2**.

Разрешён один scoped commit и push текущей preview branch. S1.W3 до callback о
commit/push не начинать.

## Принятая архитектура

1. Canonical raw contract остаётся Pydantic/OpenAPI.
2. `packages/contracts/index.ts` предоставляет generated TypeScript aliases.
3. `packages/contracts/runtime.ts` предоставляет generated runtime Zod schema.
4. `fetchDay` принимает raw JSON как `unknown` и валидирует его ровно один раз
   через `TodayPayloadWireSchema.safeParse`.
5. Contract mismatch возвращается как безопасный
   `ApiContractError/502/SCHEMA_VALIDATION_ERROR` без raw payload, Zod issues и
   PII.
6. `adaptTodayPayload` является чистым shape adapter; V2 block проходит по
   identity и повторно не парсится.
7. `lib/contracts/today.ts` не содержит manual raw V2 `z.object` declarations.
8. Preview-only timing bridge изолирован в presentation layer до S2.W1.
9. Runtime production path не импортирует fixtures/mocks.

## Независимая проверка архитектора

```text
pnpm contracts:check: PASS
focused Vitest files: 8/8 PASS
focused Vitest tests: 102/102 PASS
npx tsc --noEmit: PASS
git diff HEAD --check: PASS
forbidden cast/suppression scan: 0 matches
adapter V2 parse/safeParse calls: 0
fetch raw validation boundaries: 1
manual V2 redeclaration guard: PASS
canonical fetch function markers: 2
canonical adapter function markers: 1
```

Preview compatibility:

```text
GET http://127.0.0.1:3003/day/2026-07-08?fixture=three-horizon-timing&why=1
HTTP: 200
e2e/dev-timing-fixture.spec.ts --project=mobile: 1/1 PASS
```

## Commit allowlist

Stage только:

```text
__tests__/api/grace-client.test.ts
__tests__/contracts/today-redeclaration-guard.test.ts
__tests__/lib/adapt-payload.test.ts
__tests__/lib/presentation/today-v2.test.ts
components/today/why-time-horizon-card.tsx
lib/adapters/today-payload.ts
lib/contracts/today.ts
lib/grace/api/client.ts
lib/grace/index.ts
lib/presentation/today-v2.ts
packages/contracts/index.ts
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/19_S1_W2_TYPE_BOUNDARY_GUIDANCE.md
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/20_S1_W2_PREVIEW_TIMING_BRIDGE.md
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/21_S1_W2_ARCH_REVIEW_R1.md
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/22_S1_W2_ARCH_REVIEW_R2.md
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/23_S1_W2_ARCH_REVIEW_R3.md
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/24_S1_W2_ARCH_REVIEW_R4.md
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/25_S1_W2_ACCEPTANCE.md
```

Не stage и не менять:

```text
.grace/
artifacts/design/
docs/superpowers/plans/2026-07-05-fix-day-route-auth-build.md
grace.db
skills/
```

Перед commit:

```bash
git diff --cached --name-only
git diff --cached --check
```

Сверить staged paths буквально с allowlist.

## Разрешённый commit/push

Commit subject:

```text
refactor(today): consume generated v2 wire contracts
```

Push только:

```text
origin preview/solarsage-v2-human-first-navigator-ux
```

Не merge/rebase main, не force push, не начинать S1.W3 до callback.

## Callback

```text
COMMITTED_S1_W2
commit: <sha>
subject: refactor(today): consume generated v2 wire contracts
staged_paths: <exact list>
forbidden_paths_staged: NO
push: PASS
remote_sha: <sha>
worktree_unrelated_paths: UNTOUCHED
```
