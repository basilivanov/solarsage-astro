# packages/contracts

Единые контракты frontend ↔ backend.

## Source of truth — Option B (W-1.1B)

В этом репозитории **Pydantic-схемы из `apps/api/app/schemas/*` являются единственным источником правды для API-контрактов**. Pipeline:

```
apps/api/app/schemas/*.py   (Pydantic, BaseModel(extra="forbid", camelCase))
        |
        v  scripts/contracts/export_openapi.py
packages/contracts/openapi.json     (committed snapshot, deterministic)
        |
        +-->  npx openapi-typescript
        |       |
        |       v
        |     packages/contracts/_generated.ts    (types barrel)
        |
        +-->  scripts/contracts/generate-zod.cjs
                |
                v
              packages/contracts/_generated.zod.ts  (runtime validation barrel)
```

## Pydantic is the only wire SoT

Do not edit generated artifacts (`openapi.json`, `_generated.ts`, `_generated.zod.ts`). Do not redeclare raw wire Zod in frontend.

## How to add/change a field

1. Edit Pydantic schema in `apps/api/app/schemas/*`.
2. Run `pnpm contracts:generate`.
3. Fix compile/runtime consumers on frontend.
4. Run `pnpm contracts:check` to ensure no drift.

## How to edit visual fixture

1. Edit the single JSON visual fixture at `e2e/mock-visual/fixtures/json/day-v2-2026-07-08.json`.
2. Run `pnpm contracts:fixture:normalize`.
3. Run `pnpm contracts:check` to ensure no drift.

## Contracts check and CI

`pnpm contracts:check` runs unified script `scripts/contracts/check.sh` which:
1. Runs `generate.sh` to regenerate openapi schemas.
2. Runs `today_fixture.sh --check` to verify that visual JSON fixture has no drift.
3. Performs `git diff --exit-code` on `openapi.json`, `_generated.ts`, and `_generated.zod.ts`.

CI workflow runs this check automatically.

## Fetch boundary validation

Production fetch validates the payload once at the fetch boundary (`lib/grace/api/client.ts:fetchDay`); the frontend adapter `adaptTodayPayload` does not reparse/revalidate. Responses are parsed against `TodayPayloadWireSchema` to ensure correctness at the API client layer.

## Additive consumer-first fields vs breaking version bump

Timing fields (`activeFrom`, `activeUntil`, `exactAt`) are introduced as additive optional fields.
- additive optional field: consumer-first rollout, version bump не нужен;
- последующее заполнение этого optional field producer'ом само по себе не требует version bump;
- version bump нужен только при реально breaking shape/semantic change;
- generated artifacts коммитятся вместе с Pydantic change;
- frontend не объявляет wire type/runtime schema вручную.

## Invariants

- wire JSON содержит только JSON primitives/ISO strings, не `Date`, icons или React values;
- generated artifacts коммитятся вместе с Pydantic change;
- breaking shape/semantics требует contract version discipline и обновления canonical API docs;
- frontend импортирует public barrels и не объявляет wire schemas вручную;
- `contracts:check` реально выполняет generate → fixture check → generated diff.
