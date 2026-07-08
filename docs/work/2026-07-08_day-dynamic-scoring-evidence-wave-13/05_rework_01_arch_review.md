# Wave 13 Rework 01 Architect Review

Status: REWORK REQUIRED

Reviewed commit: `70cc05f`

## Findings

### P0 — Commit is not self-contained green

After the agent callback, the tracked working tree contains required frontend/test fixture changes that are not in `70cc05f`:

- `__tests__/components/TodayScreen.test.tsx` removes an import of non-existing `buildConcreteAdviceRows`.
- `__tests__/hooks/useDay.test.ts` adds required `daySummary` and `concreteAdvice` fields to a `TodayPayload` fixture.
- `lib/mocks/today.ts` adds required `daySummary` and `concreteAdvice` fields to `AdaptedTodayPayload` mock data.

Impact:
- The architect's successful Vitest run was against the dirty working tree, not the committed HEAD.
- `main` cannot be considered green until these relevant changes are committed or intentionally rejected with passing verification from clean HEAD.

Required fix:
- Include the relevant fixture/test changes in the Wave 13 commit/rework.
- Run targeted Vitest for:
  - `__tests__/components/TodayScreen.test.tsx`
  - `__tests__/hooks/useDay.test.ts`
  - `__tests__/contracts/today.test.ts`
  - `__tests__/lib/adapt-payload.test.ts`

### P1 — Do not commit generated local Next type target

The working tree also contains:

- `next-env.d.ts`: `.next/types/routes.d.ts` changed to `.next-prod/types/routes.d.ts`.

Impact:
- This appears to be a local build artifact from the current production build directory, not a Wave 13 source change.
- Committing it can break other dev/test environments that use the normal `.next` directory.

Required fix:
- Restore `next-env.d.ts` to committed state unless there is a deliberate, documented build-system change in this wave.

### P2 — Report SHA is stale/self-referential

`04_rework_01_report.md` contains a stale commit SHA because amending the report changes the commit hash.

Required fix:
- Do not chase a self-referential SHA inside the same commit.
- Replace the report SHA line with a non-self-referential value such as `Commit SHA: see callback HEAD`.
- The callback must include the actual final `HEAD`.

## Architect Verification Already Completed

The architect independently verified:

- Backend targeted tests: `37 passed`.
- Vitest targeted contracts/adapters: `38 passed`.
- Vitest TodayScreen/sphere-labels on dirty tree: `22 passed`.
- Basil production-style direct calculation:
  - `tg_user_id=833478509` username is `basil_ivanov`.
  - Access is full through `2026-07-11`.
  - `2026-07-12` computes successfully but is locked because access ends `2026-07-11`.
  - Direct scoring and calendar scoring match for `2026-07-08`, `2026-07-11`, `2026-07-12`.
