# Eval task — Observability event registration v1

## Packet

- Phase / Wave: `EVAL-GRACE-PROCESS-V1`
- Modules: observability canon, `M-OBSERVABILITY-EVENTS`,
  `M-COMPONENTS-CHECKIN-STATISTICS`
- Goal: add a new structured business event end to end, following the
  repository's canonical event-registration process.

Work autonomously in the provided repository. Do not use subagents or delegate
the task. Do not commit, push, install system packages, access secrets, or modify
files outside the exact write scope. Run the targeted checks before reporting.

## Required behavior

Introduce a new business event `checkin.metrics_viewed` and emit it from the
Profile check-in statistics flow:

- Fire exactly once per successful `getCheckinMetrics` load in
  `components/profile/checkin-statistics.tsx`, via the repository's typed
  frontend logging API (`logEvent` from `lib/log`), with exact
  `slice` / `module` / `block` meta for this component.
- Do not fire while loading, on error, or when the loaded metrics are empty
  (`totalCheckins === 0`).
- Payload: `{ "total_checkins": <number>, "range_days": 30 }` — aggregate
  counts only. The payload must not contain raw identifiers, initData,
  dates of birth, or any personal data.
- Register the event canonically so the whole logging spine stays consistent:
  the event name and its payload schema must keep the canon
  (`grace/canon/observability.xml`) and both derived registries
  (`apps/api/app/core/logging_events.py`, `lib/log/events.gen.ts`) free of
  drift, and the frontend type-level registry must know the name (an
  unregistered `logEvent("checkin.metrics_viewed", ...)` call must not be
  needed to type-check around). Follow the repository's own conventions for
  how the registries are maintained — do not leave the canon and its derived
  files inconsistent. Note: the repo-wide guardrail script
  `scripts/check_logging_guardrails.py` currently fails on pre-existing
  violations unrelated to this task; do not fix or silence them — only the
  registry drift check below is in scope.

All existing rendering, loading, error and empty behavior of
`CheckinStatistics` must remain unchanged.

## Exact write scope

- `grace/canon/observability.xml`
- `apps/api/app/core/logging_events.py`
- `lib/log/events.gen.ts`
- `components/profile/checkin-statistics.tsx`
- `__tests__/components/CheckinStatistics.test.tsx`
- `grace/verification-matrix.md`

## Required evidence

- A new frontend test file covering: event emitted once on successful load
  with the exact payload; not emitted on fetch error; not emitted for empty
  metrics; existing rendered content still present.
- The logging guardrail script passes (registry drift check included).
- GRACE contracts/maps kept accurate in every touched source file and the
  verification matrix updated for the new behavior.
- A final report listing changed files and the exact commands/results run.

## Frozen / out of scope

- Any other component, service, or logging call site.
- Backend emission of this event (it is frontend-only).
- Changing the logging transport, redactor, or guardrail script itself.
- New dependencies, styling redesign, production configuration and deploys.

## Verification

Run at least:

```bash
python3 -c "import sys; sys.path.insert(0,'scripts'); import check_logging_guardrails as g; sys.exit(0 if g.check_registry_drift() else 1)"
npx vitest run __tests__/components/CheckinStatistics.test.tsx --passWithNoTests
npx tsc --noEmit
python3 scripts/grace_lint.py apps/api/app
git diff --check
```

If correct implementation requires a file outside the exact write scope, stop
and report the missing scope instead of changing that file.
