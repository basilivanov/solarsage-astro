# Rework 01 Review: Frontend Migration Wave 01

Date: 2026-07-07
Reviewer: architect
Branch reviewed: `wave-01-day-visual-migration`
Commit reviewed: `6e1e719`
Status: `REWORK_REQUIRED`

## Summary

Rework 01 fixed the branch handoff problem and improved the sphere-label mapping, but the mock-visual e2e gate is still not acceptable.

The official required e2e command fails against the current branch. Also, the missing-fixture tracker is still asserted too early in some scenarios, so late API calls can be missed.

## Findings

### 1. Blocking: ready-state fixture overwrites the main day payload

Evidence:

- `e2e/mock-visual/day.spec.ts` first sets:
  - `"/api/day/2026-07-05": { body: dayPayload }`
- Then the `WEEK_STRIP_DATES` loop includes `2026-07-05` and overwrites the same fixture key with:
  - `{ body: { dayStatus: status } }`
- The screen then receives a minimal object for the main day request, not a `TodayPayload`.

Fresh reviewer command:

```bash
E2E_BASE_URL=http://localhost:3000 pnpm exec playwright test e2e/mock-visual --project=mobile
```

Result:

```text
1 failed, 2 passed

Expected data-state="ready"
Received data-state="locked"
```

Location:

- `e2e/mock-visual/day.spec.ts:51-69`

Required fix:

Do not let week-strip fixtures overwrite the main `/api/day/2026-07-05` payload. Use either:

- a route fixture factory that returns the full `TodayPayload` for the page request and a minimal day-status payload only for week-strip requests if they can be distinguished; or
- use a different selected route/date for the page and week strip if the current route cannot be distinguished; or
- make the minimal status endpoint fixture contract-compatible enough that it cannot break the main route.

The simplest acceptable fix is to skip overwriting `/api/day/2026-07-05` in the week fixture loop and keep the full `dayPayload` there.

### 2. Blocking: missing-fixture assertion can still run before late API calls

Evidence:

The locked-state test passes even though `buildLockedFixtures()` does not provide week-strip day fixtures.

Ad-hoc late check after waiting for the locked screen showed these unmocked requests:

```text
/api/referral
/api/day/2026-06-28
/api/day/2026-06-29
/api/day/2026-06-30
/api/day/2026-07-01
/api/day/2026-07-02
/api/day/2026-07-03
/api/day/2026-07-04
```

They appeared twice in the run.

Why this matters:

The original blocker was that mock-visual tests could pass while product code swallowed 501 fixture errors. Rework 01 added a tracker, but assertions must be placed after late effects have had a chance to fire. Otherwise the same class of issue remains.

Locations:

- `e2e/mock-visual/day.spec.ts:130-152`
- `components/today/week-strip.tsx:57-83`
- `lib/hooks/use-share-invite.ts:33`

Required fix:

- Fixture-cover `/api/referral` if it is part of the rendered route.
- Fixture-cover the actual week-strip dates produced by the route, currently including `2026-06-28` through `2026-07-04` in the reviewer run.
- Move the `tracker.count === 0` assertion to the end of each test, after the screen assertions and after a small deterministic wait/quiet period, or add a helper that waits for late API activity before asserting.

### 3. Accepted: raw sphere keys are no longer directly rendered

Evidence:

- `lib/display/sphere-labels.ts` maps known technical keys.
- `DayOverviewCard` and `TodayPracticalList` use `getSphereLabel()`.
- Fixture now uses technical keys such as `home_family`, `creativity_self_expression`, `communication_learning`, `work_status_achievement`.

This finding is only partially resolved after independent review. The new components no longer render those keys directly, but the existing `DayEnergyMeter` still receives `sphereScores` and renders `item.key` as the row label. Since `TodayScreen` still renders `DayEnergyMeter`, raw sphere keys can remain visible below the first viewport.

Required follow-up is included in `06_rework_02_TZ.md`.

### 4. Important: mock fixture keys still do not represent current canon keys

Evidence:

- Backend emits `SphereScore(key=key, ...)` directly from scoring output.
- Current canon contains keys such as `thinking_speech_learning`, `money_security_resources`, and `home_family_roots`.
- The rework fixture uses `home_family` and `communication_learning`, which are friendly-looking but not representative of current live canon keys.

Why this matters:

The fixture should catch raw-key leakage from real-shaped backend data. If it uses simplified keys that are not current canon keys, it gives weaker coverage.

Required follow-up is included in `06_rework_02_TZ.md`.

### 5. Accepted: branch is now handoff-safe

Evidence:

- Commit exists: `6e1e719 wave-01: rework /day/[date] screen visual migration`.
- Unrelated `.grace/`, `grace.db`, `skills/`, and old plan file are not in the commit.

This finding from `02_arch_review.md` is resolved.

## Verification Run By Reviewer

Commands:

```bash
git diff --check main..HEAD
pnpm exec tsc --noEmit --pretty false
E2E_BASE_URL=http://localhost:3000 pnpm exec playwright test e2e/mock-visual --project=mobile
```

Results:

- `git diff --check main..HEAD`: passed.
- TypeScript: passed.
- Mock visual e2e: failed, `1 failed, 2 passed`.

I did not rerun the full unit suite after the e2e failure because the wave cannot be accepted while the required e2e gate is red.

## Decision

`REWORK_REQUIRED`

Apply `06_rework_02_TZ.md`.
