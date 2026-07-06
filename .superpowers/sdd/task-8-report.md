# Task 8 Report: Horary Chart Snapshot Contract And UI

Date: 2026-07-06
Branch: `codex/real-data-frontend-migration`
Base: `df3eaec56e85a06d2528fed8e95511f096b5d4e9`

## Summary

- Added nullable persisted `horary_questions.chart_snapshot_json` storage and Alembic migration `0018`.
- Added `HoraryChartSnapshot` backend schema and generated OpenAPI/TypeScript contracts.
- Persisted the real sidecar chart snapshot during `HoraryService._generate_answer_task`; reads/list deserialize stored JSON only.
- Added `HoraryChart` UI that renders persisted backend snapshot data only. No timestamp-derived pseudo chart reconstruction was ported.
- Updated horary API facade to validate responses through Zod schemas.
- Purchase UI was not touched.
- Production service on port `3002` was not touched.

## TDD Evidence

RED:

- Added backend assertions for legacy `chart: null` and generated chart persistence/detail/list return.
- Added contract assertions for OpenAPI `chart` and local Zod schema preservation.
- Added answer-view assertion for rendering a persisted chart snapshot.
- Initial focused runs failed as expected:
  - `python -m pytest tests/test_horary_endpoints.py -q`: failed on missing `chart` key and missing `chart_snapshot_json`.
  - `pnpm exec vitest run __tests__/contracts/horary.test.ts __tests__/horary/horary-answer-view.test.tsx`: failed on missing OpenAPI chart schema and missing chart UI.

GREEN:

- Implemented nullable storage, snapshot builder, schemas, API serialization, generated contracts, typed client parsing, and chart UI.
- Fixed one test assertion ambiguity by scoping duplicate `Луна` text to the chart region.
- Cleaned mocked `asyncio.create_task` in horary endpoint tests to avoid unawaited coroutine warnings.

## Verification

- `npm run contracts:generate`: passed.
- `cd apps/api && source .venv/bin/activate && python -m pytest tests/test_horary_endpoints.py -q`: passed, `17 passed`.
- `pnpm exec vitest run __tests__/contracts/horary.test.ts __tests__/horary/horary-answer-view.test.tsx __tests__/horary/horary-screen-flow.test.tsx`: passed, `23 passed`.
- `pnpm exec tsc --noEmit`: passed.
- `npm run contracts:check`: passed after staging regenerated `packages/contracts/openapi.json` and `packages/contracts/_generated.ts`; the script checks worktree diff against the index.

## Concerns

- Vitest prints the existing Vite CJS API deprecation warning. Tests pass.
- `next-env.d.ts` was dirty before this task and was not staged or committed.

## Review Fixes: 2026-07-06

Addressed Needs Fixes review findings:

- Critical: `_build_horary_chart_snapshot` now strips known `Transit_` / `Natal_` prefixes from normalized aspect signal endpoints, then keeps only aspects whose normalized endpoints both exist in the persisted chart planet set. No aspects are fabricated.
- Important: local Zod `HoraryQuestionSchema.chart` now matches generated/OpenAPI contract as required-but-nullable. A missing `chart` property fails validation; `chart: null` remains valid for legacy rows.
- Important: horary generation now resolves chart datetime through `ZoneInfo(question.client_timezone)`. Naive local times are serialized with the chart timezone offset, and aware inputs are converted to the chart timezone before sidecar calls and snapshot persistence.

Additional RED/GREEN evidence:

- Backend regression was first changed to use a non-empty transit response that generates a prefixed `Transit_Moon` aspect and to expect offset-aware `castAt`; it failed against the reviewed implementation.
- Contract regression was added to require the `chart` property; it failed while local Zod still treated `chart` as optional.
- Component regression now checks that an offset-aware `castAt` displays the intended chart-local time in `chart.timezone`.

Verification after fixes:

- `cd apps/api && source .venv/bin/activate && python -m pytest tests/test_horary_endpoints.py -q`: passed, `17 passed`.
- `pnpm exec vitest run __tests__/contracts/horary.test.ts __tests__/horary/horary-answer-view.test.tsx`: passed, `21 passed`.
