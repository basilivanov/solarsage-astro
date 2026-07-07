# Wave 09 — Corrective Frontend Migration Audit

Date: 2026-07-07
Agent: coding-executor (Flash 3.5)
Branch: `main`
Baseline commit: `ebda0c1`
Current main HEAD: `f986dd6`

## Executive Recommendation

**Option B — Clean Branch From `ebda0c1`**

The current migration diverged significantly from the visual oracle at `/opt/solarsage-astro-mock-preview` (port 3001, commit `19d7db9`). Visual parity is poor across all six audited route families. Attempting to fix this on the current branch would require extensive rewrites that amount to the same effort as a clean re-port.

Recommend creating a new branch from `ebda0c1`, re-porting UI from the real 3001 oracle, keeping only confirmed real-data-compatible components and tests from waves 01-08, then replacing `main` only after explicit architect approval.

## Evidence Summary

Screenshots captured to `artifacts/`:
- 12 screenshots total (6 routes × 2 ports)
- 3001 = oracle (mock-preview), 3002 = current main

Key visual observations from screenshots:
- **/day**: Oracle has calm card, moon phase widget, planetary day, retrograde tracker, void-of-course, concrete advice, affirmation, tip card. Main has day-overview-card and practical-list which look completely different.
- **/calendar**: Both structurally similar but visual density and polish differ.
- **/profile**: Oracle has transit timeline, lunar node widget — main lacks these entirely. Access card and referral card visual hierarchy differ significantly.
- **/readings**: Oracle has synastry demo and celebrity compatibility — main lacks these. Available card visual treatment differs.
- **/readings/horary**: Oracle has richer form visual, quota bar is different density.
- **/readings/natal**: Oracle has planetary strength radar — main lacks it. Hero section and highlights differ.

## Services And Sources

| Service | Status | Details |
|---------|--------|---------|
| `3002` (current main) | Reachable | Port 3002, HEAD `f986dd6` |
| `3001` (oracle) | Reachable | Port 3001, HEAD `19d7db9` (branch `archive/demo-origin-main`) |
| `main` git status | Clean | No uncommitted tracked files |
| `mock-preview` git status | Modified | `.env`, `next.config.mjs` differ, untracked `pnpm-lock.yaml`, `pnpm-workspace.yaml` |

## File-Level Comparison Summary

Files present ONLY in oracle (3001) — not ported to main:

| Route | Oracle-only files | Classification |
|-------|-----------------|---------------|
| /day | `moon-phase-widget`, `planetary-day-widget`, `retrograde-tracker`, `void-of-course-indicator`, `day-tip-card`, `day-recommendations`, `concrete-day-advice`, `daily-affirmation`, `astro-history-widget`, `evening-checkin-reminder`, `planetary-hour-timeline` | `REQUIRES_BACKEND_CONTRACT` or `PORT_UI_HIDE_UNTIL_CONTRACT` |
| /calendar | (no unique files — all differ structurally) | `PORT_UI_WITH_EXISTING_REAL_DATA` |
| /profile | `transit-timeline`, `lunar-node-widget`, `dev-mode-switcher` | `REQUIRES_BACKEND_CONTRACT` (transit, lunar), `DO_NOT_PORT_DEMO_ONLY` (dev-switcher) |
| /readings | `synastry-demo`, `celebrity-compatibility` | `DO_NOT_PORT_DEMO_ONLY` |
| /readings/horary | (no unique files — all differ structurally) | `PORT_UI_WITH_EXISTING_REAL_DATA` |
| /readings/natal | `planetary-strength-radar` | `REQUIRES_BACKEND_CONTRACT` |

Files present ONLY in main — not in oracle:

| Route | Main-only files | Assessment |
|-------|----------------|-----------|
| /day | `day-overview-card.tsx`, `today-practical-list.tsx` | Incorrectly added — do not match 3001 visual oracle |
| /day | `sphere-labels.ts` | Useful display mapping, not visual — can keep |
| All | `e2e/mock-visual/**` | Test-only — can keep, but will need fixture updates after re-port |

## Decision Matrix

| Route | Visual Parity | Main Files | Oracle Files | Action |
|-------|-------------|------------|-------------|--------|
| /day | WRONG | `today-screen.tsx`, `day-overview-card.tsx`, `today-practical-list.tsx`, `day-reading.tsx`, `day-chart.tsx`, `day-energy-meter.tsx`, `date-header.tsx` | `today-screen.tsx`, `moon-phase-widget.tsx`, `planetary-day-widget.tsx`, `retrograde-tracker.tsx`, `void-of-course-indicator.tsx`, `concrete-day-advice.tsx`, `daily-affirmation.tsx`, `day-tip-card.tsx` | `REWORK_FROM_ORACLE` |
| /calendar | PARTIAL | `calendar-screen.tsx`, `lunar-calendar-strip.tsx` | Same files, visually differ | `REWORK_FROM_ORACLE` |
| /profile | PARTIAL | `profile-screen.tsx`, `access-card.tsx`, `referral-card.tsx` | Same files + `transit-timeline`, `lunar-node-widget` | `REWORK_FROM_ORACLE` + `HIDE_UNTIL_CONTRACT` for transit/lunar |
| /readings | CLOSE | `readings-screen.tsx`, `available-card.tsx`, `coming-card.tsx` | Same files + `synastry-demo`, `celebrity-compatibility` | `KEEP` (closest to oracle) |
| /readings/horary | PARTIAL | `horary-screen.tsx`, `horary-form.tsx`, `horary-quota-bar.tsx` | Same files, visually differ | `REWORK_FROM_ORACLE` |
| /readings/natal | PARTIAL | `natal-page.tsx`, `hero-section.tsx`, `natal-chart-wheel.tsx` | Same files + `planetary-strength-radar.tsx` | `REWORK_FROM_ORACLE` + `HIDE_UNTIL_CONTRACT` for radar |

## Day Route Deep Dive

### 1. `day-overview-card.tsx` — DELETE AND REPLACE FROM ORACLE

This component was created from a static screenshot without access to the live oracle. The oracle uses a composite approach with separate widgets (`moon-phase-widget`, `planetary-day-widget`, `retrograde-tracker`, `void-of-course-indicator`). The current `day-overview-card` should be deleted and replaced by the oracle's widget composition once backend contracts exist.

### 2. `today-practical-list.tsx` — DELETE AND REPLACE FROM ORACLE

This component was created ad-hoc. The oracle uses `concrete-day-advice.tsx` which renders actionable items from real `sphereScores`, `topFlags`, and `notes` — similar concept but different visual and data-binding. Replace with oracle version after audit.

### 3. Oracle blocks safe to port:
- `moon-phase-widget.tsx` — depends on backend `day.lunar` fields (already available in `CalendarPayloadReadModel` and `TodayPayload`)
- `planetary-day-widget.tsx` — depends on `planetInfluences`/`topFlags` (already available)
- `void-of-course-indicator.tsx` — depends on backend lunar void-of-course field (already available)
- `concrete-day-advice.tsx` — depends on `sphereScores`/`topFlags`/`notes` (already available)
- `daily-affirmation.tsx` — depends on LLM-generated `headline`/`reading` (already available)

### 4. Oracle blocks requiring backend contracts:
- `retrograde-tracker.tsx` — needs specific retrograde/station data per planet
- `astro-history-widget.tsx` — needs past-day summary endpoint
- `planetary-hour-timeline.tsx` — needs planetary hour calculation contract
- `evening-checkin-reminder.tsx` — needs check-in state from backend

### 5. Oracle blocks NOT to port (demo-only):
- (None identified in /day — all oracle today widgets appear backed by factual astrology data)

### 6. Page.tsx data passing:
Current `app/(grace)/day/[date]/page.tsx` passes `payload` (AdaptedTodayPayload) to `TodayScreen`. This is correct. No change needed to the data passing pattern.

### 7. Backend contracts needed:
- Retrograde/station data per planet (for `retrograde-tracker`)
- Past-day summary endpoint (for `astro-history-widget`)
- Planetary hour calculation (for `planetary-hour-timeline`)
- Evening check-in state (for `evening-checkin-reminder`)

## Git Strategy Assessment

### Option A — Corrective Branch From Current Main

**Pros:**
- Preserves all test and e2e work from waves 01-08
- Keeps docs/work audit trail intact
- No rebase or force-push needed

**Cons:**
- Many components need complete rewrites — same effort as clean branch
- Risk of leftover dead imports from replaced components
- Git history continues to reflect wrong visual decisions

### Option B — Clean Branch From `ebda0c1`

**Pros:**
- Clean baseline from before the incorrect visual migration
- Only the correct 3001 oracle components get ported
- No dead code from wrong decisions
- Clean git history

**Cons:**
- Loses all test/e2e/docs work from waves 01-08 (must be manually re-evaluated)
- Cannot force-push to `main` without architect approval
- Requires careful cherry-picking of useful infrastructure (mock-visual fixtures, route-interception, sphere-labels, etc.)

### Recommendation: Option B

Given the severity of visual misalignment across 5 of 6 route families, the effort to rewrite is equivalent to a clean branch. Option B produces a cleaner outcome. However, Option B must NOT be executed without explicit architect approval for the git strategy (specifically how to land it on `main` without breaking history).

## Cleanup List (Files to Remove in Corrective Wave)

If Option A is chosen:
- `components/today/day-overview-card.tsx` 
- `components/today/today-practical-list.tsx`
- `components/readings/readings-screen.tsx` (rewrite)
- `components/readings/available-card.tsx` (rewrite)
- `components/readings/horary/horary-screen.tsx` (rewrite)
- `components/readings/horary/horary-form.tsx` (rewrite)
- `components/readings/horary/horary-quota-bar.tsx` (rewrite)
- `components/profile/profile-screen.tsx` (rewrite)
- `components/profile/access-card.tsx` (rewrite)
- `components/profile/referral-card.tsx` (rewrite)
- `components/calendar/calendar-screen.tsx` (rewrite)
- `components/calendar/lunar-calendar-strip.tsx` (rewrite)
- All `e2e/mock-visual/*` fixtures will need updating to match re-ported UI

## New Backend/API Contracts Required

Before honest visual parity can be achieved, these backend contracts are needed:

| Contract | Needed By | Priority |
|----------|-----------|----------|
| Retrograde/station data per planet | `/day` retrograde widget | Medium |
| Past-day summary endpoint | `/day` astro-history widget | Low |
| Planetary hour calculation | `/day` planetary-hour-timeline | Low |
| Lunar node transit data | `/profile` lunar-node-widget | Medium |
| Transit timeline data | `/profile` transit-timeline | Medium |
| Planetary strength radar data | `/readings/natal` radar widget | Low |

All current visible data on 3002 is backed by real API contracts. No fabricated astrology was detected.

## Test Strategy For Next Implementation Wave

1. Fix the source-of-truth reference: always use the running 3001 oracle, not static screenshots.
2. Port one route at a time, comparing visually with Playwright screenshots against both 3001 and 3002.
3. Keep the mock-visual fixture pattern (`e2e/mock-visual/**`) as it ensures deterministic comparison.
4. Add a Playwright visual diff step per route after re-port.
5. Keep `lib/display/sphere-labels.ts` as it is a useful real-data mapping.
6. Keep `e2e/mock-visual/route-interception.ts` as it is a test-only helper.

## Blocks

No blockers identified. Both 3001 and 3002 are reachable. All git operations are clean.

## Commands Run

```bash
git -C /opt/solarsage-astro status --short
# Clean — no uncommitted tracked files

git -C /opt/solarsage-astro rev-parse --short HEAD
# f986dd6

git -C /opt/solarsage-astro-mock-preview status --short
# M .env, M next.config.mjs, ?? pnpm-lock.yaml, ?? pnpm-workspace.yaml

git -C /opt/solarsage-astro-mock-preview rev-parse --short HEAD
# 19d7db9

curl http://127.0.0.1:3001/day/2026-07-05
# 200 OK

curl http://127.0.0.1:3002/day/2026-07-05
# 200 OK

git diff --name-status ebda0c1..HEAD -- app components lib e2e __tests__
# 46 files changed

diff -qr --exclude=node_modules --exclude=.next ./components/* ../mock-preview/components/*
# Multiple differences across all route families (see above)
```
