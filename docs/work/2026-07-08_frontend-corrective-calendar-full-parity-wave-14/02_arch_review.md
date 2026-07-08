# Wave 14 Calendar Oracle Audit — Architect Review

Status: REWORK REQUIRED
Reviewed artifact commit: `9ee612e`
Report: `docs/work/2026-07-08_frontend-corrective-calendar-full-parity-wave-14/01_oracle_audit_report.md`

## Findings

### P0 — Report is too shallow for the approved "full calendar parity" audit

The TZ required a complete audit of `/calendar`, including header, month navigation, day cells, today/selected/out-of-month/locked states, lunar mode, selected-day summary, bottom navigation, loading/error states, mobile constraints, semantic test contract, and all 13 direct questions in section 9.

The current report has only:

- 4 visual matrix rows;
- 3 interaction matrix rows;
- a short data matrix;
- no complete answer list for the 13 required questions.

It omits or under-specifies several visible surfaces from the captured artifacts, so it cannot be used as the implementation source of truth.

Required fix:

- Expand the audit report into a complete route-level inventory.
- Add rows for every visible calendar surface and state requested in `00_TZ.md`.
- Answer all 13 questions from `00_TZ.md` section 9 explicitly.
- Use artifact filenames as evidence for every visual finding.

### P1 — Report misses visible 3001/3002 differences shown in its own screenshots

Examples from the committed artifacts:

- `3001-*-calendar-top.png` shows Russian month title `Июль 2026`; `3002-*-calendar-top.png` shows English `July 2026`.
- `3001-tall-calendar-top.png` shows the selected-day summary footer: `Сегодня`, `8 июля 2026`, status, and `Открыть день`; `3002-tall-calendar-top.png` does not show the selected-day summary at all.
- `3001-*-calendar-top.png` has a rich lunar calendar card with tags, phase strip, percentages, and legend; `3002-*-calendar-top.png` has only the unavailable fallback card.
- `3001-*-calendar-lunar.png` uses phase glyphs and lunar day numbers; `3002-*-calendar-lunar.png` uses static moon icons and missing-value dashes.
- The grid density, opacity of unavailable cells, lock markers, and selected-state treatment visibly differ, but the report does not enumerate them.

Required fix:

- Add these differences to the visual and interaction matrices.
- Do not classify the selected-day summary as matching until the screenshots and behavior prove it.
- Include month title localization as a required P1 fix.

### P1 — Backend contract proposal is underspecified and risks putting domain logic in the wrong place

The report says to "implement lightweight phase/illumination/lunar day calculation inside `calendar_service.py`". That is not a sufficient architecture decision.

The calendar UI needs backend-owned lunar facts, but the implementation should not bury reusable lunar calculation in a route service. The audit must propose a reusable backend contract and source-of-truth helper/service that can serve both `/api/calendar` and `/api/day` where needed.

Required fix:

- Propose exact JSON fields, types, nullability, and frontend adapter mapping.
- Clarify whether `lunar.phase` is a display label, stable enum/key, or phase index. Prefer stable semantic data plus localized display mapping over backend-returned emoji-only display.
- Specify the backend source of truth: SolarSage/Sun-Moon longitudes, shared API helper, sidecar extension, or a consciously accepted simplified algorithm.
- Specify cache/versioning implications for calendar and day payloads.
- Specify backend tests and frontend contract tests.

### P1 — File deletion recommendations are unsafe and not supported by the audit

The report recommends deleting:

- `components/grace/CalendarGrid.tsx`
- `lib/mocks/calendar.ts`

This is out of scope for a parity implementation unless the audit proves there are no imports, no tests, and no docs/work dependencies that matter. `lib/mocks/calendar.ts` is not imported by production code, but that does not mean it should be deleted; it can remain test-only.

Required fix:

- Reclassify production-unused files separately from "delete now".
- For `lib/mocks/calendar.ts`, recommend `KEEP_TEST_ONLY` unless there is a concrete test cleanup plan.
- Do not put cleanup deletions into the implementation wave unless they are required for parity or safety.

### P2 — Verification evidence is asserted but not traceable

The report states that calendar/day scoring is "100% consistent" and Basil access is correct, but it does not include the exact commands, endpoints, SQL, or summarized outputs used to verify those claims.

Required fix:

- Add a concise evidence block for scoring/access checks.
- State whether screenshot auth used a synthetic user and whether Basil checks were direct read-only checks.
- Include the temporary Playwright screenshot spec result and explicitly state that the temporary spec was removed and not committed.

## Required Rework Output

Create:

- `docs/work/2026-07-08_frontend-corrective-calendar-full-parity-wave-14/04_rework_01_report.md`

Optional if more artifacts are needed:

- `docs/work/2026-07-08_frontend-corrective-calendar-full-parity-wave-14/artifacts/audit-rework-01/`

Do not edit product source files.
