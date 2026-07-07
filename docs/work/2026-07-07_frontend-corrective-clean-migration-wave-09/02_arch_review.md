# Wave 09 Architect Review — Rework Required

Status: **REJECTED / REWORK REQUIRED**

Reviewed commit: `679acfb`
Report: `docs/work/2026-07-07_frontend-corrective-clean-migration-wave-09/01_agent_report.md`

## Summary

The audit cannot be accepted as the gate for corrective migration.

The coder can collect screenshots, DOM snapshots, diffs, and code evidence, but must not make subjective visual-parity claims without a valid visual review path. The current artifacts do not show the target screens; they are stuck on auth/loading. Therefore the report's visual conclusions are not supported by its own evidence.

## Findings

### P0 — Screenshot artifacts are auth/loading screens, not route evidence

Evidence:

- `artifacts/3001-day-2026-07-05.png` shows only `Авторизация...`.
- `artifacts/3002-day-2026-07-05.png` shows only `Авторизация...`.
- `artifacts/3001-calendar.png` shows only `Авторизация...`.

This contradicts the report's claim that screenshots support visual observations:

- `01_agent_report.md:17-29` says 12 screenshots were captured and then lists route-specific visual observations.
- `01_agent_report.md:181` says no blockers were identified.

This is a hard gate failure. A screenshot is valid only if it passes a route-specific DOM sentinel that proves the page is not auth/loading/error.

### P0 — Visual conclusions were made without valid visual evidence

The report says `/day`, `/calendar`, `/profile`, `/readings`, `/horary`, and `/natal` have specific visual parity statuses in `01_agent_report.md:61-70`.

Because the captured artifacts are not the actual pages, these statuses are unsupported. The rework must separate:

- mechanical file-level comparison,
- DOM-sentinel evidence,
- valid screenshot paths,
- architect visual review pending.

The implementing coder should not write "CLOSE", "PARTIAL", or route-level visual recommendations from screenshots it cannot inspect.

### P0 — Demo/static astrology was misclassified as safe to port

The report says several `/day` widgets are safe to port and backed by real data:

- `01_agent_report.md:82-87`
- `01_agent_report.md:95-96`

But the 3001 source shows local demo/approximate calculations:

- `/opt/solarsage-astro-mock-preview/components/today/moon-phase-widget.tsx:11-14` explicitly says the calculation is a simplified demo approximation and real SolarSage should use Swiss Ephemeris.
- `/opt/solarsage-astro-mock-preview/components/today/moon-phase-widget.tsx:64-89` computes Moon phase/sign locally.
- `/opt/solarsage-astro-mock-preview/components/today/concrete-day-advice.tsx:56-60` calls local `computeMoonPhase`, `getLunarDay`, `getVoidOfCourse`, `getAllRetrogrades`.
- `/opt/solarsage-astro-mock-preview/components/today/today-screen.tsx:321-340` uses static `NATAL_HOUSES` and `NATAL_PLANETS` from demo data.

Those are not production-safe runtime data contracts. The correct classification must distinguish:

- presentation shell safe to port,
- data/calculation logic not safe to port,
- needs backend/sidecar contract,
- hide until contract.

### P1 — `page.tsx` raw data passing conclusion is likely wrong or incomplete

`01_agent_report.md:98-99` says no change is needed because `page.tsx` passes `payload`.

But the 3001 `TodayScreen` accepts `rawData?: TodayPayload | null` and derives chart/energy from raw API payload. In current main, this must be rechecked against the actual `app/(grace)/day/[date]/page.tsx` implementation and the real backend contract.

The audit must answer this from code, not from assumption:

- Is `rawData` currently passed?
- If yes, where?
- If no, should it be passed, or should chart/energy be adapted in a pure adapter?

### P1 — Report header has stale HEAD

`01_agent_report.md:7` says current main HEAD is `f986dd6`, but the submitted report commit is `679acfb`. This is not a product defect, but it weakens traceability. Rework should include both "audit started at" and "report commit".

## Required Rework

Create `03_rework_01_TZ.md` and send it to the coder. The rework must:

- regenerate route screenshots with real auth/session handling;
- prove each screenshot with DOM sentinels before capture;
- replace subjective visual conclusions with "visual review pending architect" unless a route is proven by DOM/file evidence only;
- correct data-safety classifications for every 3001 component;
- update the report in place or append a `01_agent_report.md` rework section;
- commit only Wave 09 docs/artifacts.

## Review Decision

Rejected. Do not use this audit to choose Option A/Option B yet.
