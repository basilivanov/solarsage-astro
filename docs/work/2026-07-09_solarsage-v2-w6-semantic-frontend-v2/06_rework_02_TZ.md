# W6 Rework 02 TZ — Tighten V2 Adapter Boundary

Owner: coder in `tmux astro:0.0`
Architect/review: current Codex thread
Branch: `main`
Push/deploy: do not push or deploy.

## Inputs

Read:

```text
docs/work/2026-07-09_solarsage-v2-w6-semantic-frontend-v2/05_rework_01_review.md
```

Use prior W6 TZ/reports only as context. Fix only the adapter boundary finding.

## Goal

Make the frontend V2 adapter strict and contract-driven:

- frontend must not fabricate backend-owned V2 evidence;
- V2 payload defaults should come from the Zod schema, not ad hoc empty strings;
- no `any`, no broad casts, no `ts-ignore`;
- old V1 payload behavior must stay unchanged.

## Required Changes

Modify primarily:

```text
lib/adapters/today-payload.ts
__tests__/lib/adapt-payload.test.ts
```

Expected implementation direction:

- Import and use `TodayV2BlockSchema` from `lib/contracts/today`.
- For `api.v2 === null/undefined`, return `null`.
- For present V2, validate/normalize it through the schema.
- Let schema defaults apply to optional/defaulted fields such as `active`, `phase`, `polarity`, and `debug`.
- Do not replace missing required fields (`id`, `targetKey`, `label`, `evidence`, etc.) with `""` or `0`.
- Remove `Record<string, any>` and enum `as ...` casts from `buildV2Block`.

If TypeScript needs local types, use concrete inferred types from `AdaptedTodayPayload` or exported contract types, not `any`.

## Required Tests

Add/adjust adapter tests proving:

- old payload without `v2` adapts with `payload.v2 === null`;
- valid V2 payload preserves data;
- V2 activation missing optional/defaulted fields is normalized with schema defaults;
- malformed V2 missing a required backend-owned field is not silently fabricated into an empty string. It should throw or fail validation according to the existing adapter failure policy.

## Required Verification

Run and report exact commands/results:

```bash
pnpm typecheck
```

```bash
npx vitest run __tests__/lib/adapt-payload.test.ts __tests__/contracts/today.test.ts
```

```bash
git show --check HEAD
git diff 2f9173fbe9a9e20e97891e9789db6de57a2afaef..HEAD --check
git status --short --branch
```

If you touch generated contracts, also run:

```bash
pnpm contracts:generate
```

Do not rerun Playwright/backend unless your changes unexpectedly affect those paths.

## Required Report

Write:

```text
docs/work/2026-07-09_solarsage-v2-w6-semantic-frontend-v2/07_rework_02_report.md
```

Include:

- files changed;
- how the adapter no longer fabricates V2 evidence;
- exact verification outputs;
- push/deploy status: `NOT_ATTEMPTED`;
- current commit SHA may be only in callback.

Commit implementation and report. Do not push/deploy.

## Callback

After implementation, verification, report, and commit:

```bash
HEAD_SHA="$(git rev-parse --short HEAD)"
curl -X POST http://127.0.0.1:18765/trigger \
  -H "Authorization: Bearer 324b0306c32ffc5f6a64e16076c8c9ac0ee12fbba925cfd3" \
  -H "Content-Type: application/json" \
  -d "{\"prompt\":\"Wave W6 Rework 02 ready for architect review. Report: docs/work/2026-07-09_solarsage-v2-w6-semantic-frontend-v2/07_rework_02_report.md. Review: docs/work/2026-07-09_solarsage-v2-w6-semantic-frontend-v2/05_rework_01_review.md. Rework TZ: docs/work/2026-07-09_solarsage-v2-w6-semantic-frontend-v2/06_rework_02_TZ.md. Branch: main. Commit: ${HEAD_SHA}. Push: NOT_ATTEMPTED\"}"
```

