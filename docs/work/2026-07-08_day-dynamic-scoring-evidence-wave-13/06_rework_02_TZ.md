# Wave 13 Rework 02 TZ

## Goal

Make Wave 13 committed HEAD self-contained and green. This is a small cleanup/recommit wave after Rework 01.

## Tasks

1. Commit the relevant uncommitted frontend/test fixture changes:
   - `__tests__/components/TodayScreen.test.tsx`
   - `__tests__/hooks/useDay.test.ts`
   - `lib/mocks/today.ts`

2. Do not commit local/generated artifacts:
   - Restore `next-env.d.ts` to HEAD unless you can prove this wave intentionally changes Next type generation.
   - Do not stage `.grace/`, `grace.db`, `skills/`, or `docs/superpowers/`.

3. Fix the self-referential SHA line in:
   - `docs/work/2026-07-08_day-dynamic-scoring-evidence-wave-13/04_rework_01_report.md`

   Use text like:
   - `Commit SHA: see callback HEAD`

   Do not amend repeatedly just to make the report contain its own final hash.

4. Add a short report:
   - `docs/work/2026-07-08_day-dynamic-scoring-evidence-wave-13/07_rework_02_report.md`

   Include:
   - changed files
   - exact verification commands/results
   - final `git status --short --branch`
   - final commit hash
   - push/deploy status

## Verification

Run:

```bash
npx vitest run __tests__/components/TodayScreen.test.tsx __tests__/hooks/useDay.test.ts __tests__/contracts/today.test.ts __tests__/lib/adapt-payload.test.ts
```

Also run:

```bash
git diff --check HEAD~1..HEAD
git status --short --branch
```

## Commit

Commit the relevant changes. Do not push/deploy.

## Callback

When done, run:

```bash
curl --max-time 10 -X POST http://127.0.0.1:18765/trigger \
  -H "Authorization: Bearer 324b0306c32ffc5f6a64e16076c8c9ac0ee12fbba925cfd3" \
  -H "Content-Type: application/json" \
  -d '{"prompt":"Wave 13 Rework 02 ready for architect review. Report: docs/work/2026-07-08_day-dynamic-scoring-evidence-wave-13/07_rework_02_report.md. Branch: main. Commit: <HEAD>. Push: NOT_ATTEMPTED"}'
```
