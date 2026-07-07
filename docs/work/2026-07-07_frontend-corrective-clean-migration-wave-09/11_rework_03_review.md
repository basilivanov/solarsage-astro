# Wave 09 Rework 03 Architect Review — Rework Required

Status: **REJECTED / REWORK REQUIRED**

Reviewed commit: `49a07c7`
Report: `docs/work/2026-07-07_frontend-corrective-clean-migration-wave-09/10_rework_03_report.md`

## Summary

Rework 03 is materially better than Rework 02 because it uses an authenticated Playwright page and no longer captures only `Авторизация...`.

It still cannot be accepted as the visual evidence gate. The key requirement from the user was explicit: first-screen evidence is not enough; we need the information below the fold. The current `fullPage` artifacts do not satisfy that requirement.

## Findings

### P0 — `fullPage` artifacts are not full-page evidence

Every committed PNG in `artifacts/rework-03/` has the same dimensions: `430x932`.

That includes files named `*-fullpage.png`, for example:

- `3001-day-2026-07-05-fullpage.png` — `430x932`
- `3002-day-2026-07-05-fullpage.png` — `430x932`
- `3002-profile-fullpage.png` — `430x932`

This means Playwright `fullPage: true` captured only the fixed viewport. The app appears to scroll inside an internal container, not the document body. As a result, the artifacts still do not prove below-the-fold parity.

Example: `3001-day-2026-07-05-fullpage.png` stops in the middle of the practical advice list, with bottom navigation visible. It does not show the rest of the route content.

This is the same class of evidence gap the user objected to.

### P0 — Required routes are still missing full-page/scroll evidence

The TZ required viewport and full-page evidence for every route and every port.

Actual counts:

- viewport PNGs: `12`
- fullPage PNGs: `10`

Missing full-page artifacts:

- `3001-calendar-fullpage.png`
- `3001-profile-fullpage.png`

The report says those routes were blocked by `no_sentinel`, but `capture-results.json` contains body text proving the expected content is present:

- `/calendar`: body text includes `КАЛЕНДАРЬ` and `Июль 2026`
- `/profile`: body text includes `ПРОФИЛЬ`, `ДОСТУП`, and `Доступ активен`

So this is a sentinel implementation bug, not a real blocker.

### P0 — JSON and artifact files are inconsistent for blocked routes

For `3001 /calendar` and `3001 /profile`, `capture-results.json` says:

- `"viewportArtifact": null`
- `"fullPageArtifact": null`

But viewport PNG files exist:

- `3001-calendar-viewport.png`
- `3001-profile-viewport.png`

The report also says viewport screenshots were captured for those blocked routes. JSON, report, and files must agree.

### P1 — The report claims 24 PNG files, but only 22 exist

The report states:

`24 PNG files + capture-results.json + capture-stdout.txt`

Actual files:

- `12` viewport PNGs
- `10` fullPage PNGs
- total `22` PNGs

This must be corrected.

### P1 — Commit introduced unrelated executable mode changes

Commit `49a07c7` changed many existing docs and PNG artifacts from `100644` to `100755`.

Examples:

- `00_TZ.md`
- `01_agent_report.md`
- previous `artifacts/*.png`
- previous `artifacts/rework-02/*.png`
- `artifacts/rework-02/capture-results.json`

This is unrelated metadata churn caused by `chmod -R 755`. It must be cleaned up. Markdown, JSON, TXT, and PNG artifacts should not be executable.

Only an actual script may be executable, and even that is optional for a Node script invoked as `node path/to/script`.

### P2 — API preflight checks the wrong endpoint

The report lists API port `8000` as `HTTP 404 (expected — no root route)`.

For this project, the useful health preflight is:

`http://127.0.0.1:8000/api/health`

The root 404 is not a meaningful API availability check.

## Required Rework

Create `12_rework_04_TZ.md` and send it to the coder.

Rework 04 must:

- restore accidental file modes to non-executable;
- fix 3001 calendar/profile sentinels;
- capture below-the-fold content through internal scroll-container screenshots when Playwright `fullPage` is only viewport-sized;
- produce consistent JSON/report/artifact paths;
- commit only docs/work Wave 09 evidence and cleanup.

## Review Decision

Rejected. Do not use Rework 03 as the visual gate for implementation.
