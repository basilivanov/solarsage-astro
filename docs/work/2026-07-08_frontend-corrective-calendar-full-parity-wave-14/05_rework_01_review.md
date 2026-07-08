# Wave 14 Calendar Oracle Audit Rework 01 — Architect Review

Status: ACCEPTED
Reviewed report: `docs/work/2026-07-08_frontend-corrective-calendar-full-parity-wave-14/04_rework_01_report.md`
Reviewed commit: `ebe882f`

## Acceptance

The reworked audit is accepted as the implementation source of truth for the calendar parity wave.

It now covers:

- full visual route inventory with screenshot evidence;
- interaction parity gaps;
- backend/frontend contract matrix;
- safe file decisions;
- explicit answers to all 13 questions from `00_TZ.md`;
- backend-owned lunar architecture direction;
- known verification evidence gaps to close during implementation.

## Binding Decisions For Implementation

- `3001` remains the visual/interaction oracle.
- `3002/main` must keep real API, Telegram auth, backend access, and backend-owned scoring.
- Lunar facts must be produced by backend/shared service, not frontend astrology calculations.
- `lib/mocks/calendar.ts` remains test-only and must not be imported in production runtime.
- `components/grace/*` cleanup is out of scope for parity unless a separate cleanup proves it is necessary.
- Calendar day tap selects locally. Only footer CTA navigates to `/day/YYYY-MM-DD`.
- Visible month title must be Russian (`Июль 2026` style), not backend English `July 2026`.
- The selected-day footer must be visible above bottom nav like the oracle.
