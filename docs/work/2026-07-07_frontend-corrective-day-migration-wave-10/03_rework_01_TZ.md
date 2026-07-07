# Rework 01 TZ: Wave 10 — Full `/day/[date]` Oracle Composition

Date: 2026-07-07
Branch: `main`
Role: coding executor
Goal: make main `/day/[date]` match the 3001 mock-preview day UI as a full scrollable screen, while using real main data contracts only.

## Non-Negotiables

- Do not import runtime mocks into production code.
- Do not import from `/opt/solarsage-astro-mock-preview`.
- Do not copy local static astrology logic from mock-preview into main:
  - no `computeMoonPhase`
  - no `getAllRetrogrades`
  - no `getVoidOfCourse`
  - no demo `NATAL_*`
- Keep `/day/[date]` data flow through `useDay`, `adaptTodayPayload`, calendar/access contracts, and real API responses.
- Do not overwrite Wave 09 evidence artifacts.
- Do not commit generated `next-env.d.ts` changes.

## Required Product Changes

### 1. Match 3001 section order

Rework `components/today/today-screen.tsx` so accessible `/day/[date]` follows this order:

1. `DateHeader`
2. access/trial card
3. evening/check-in reminder block
4. compact `DaySummaryCard`
5. concrete advice section in 3001 style
6. chart section only when real `payload.dayChart` is available, otherwise omit or show a graceful empty state that does not look like mock data
7. day reading
8. why expanded
9. week strip
10. history/disclaimer/bottom area

Remove the standalone `payload.headline` block from the top visible flow.
If the headline is still needed, fold it into the reading/summary area in a way that does not change the 3001 top layout.

### 2. Port the 3001 concrete advice presentation without mock astrology

Create or rework a main component for the 3001 "Конкретно сегодня" section.
It should visually follow `/opt/solarsage-astro-mock-preview/components/today/concrete-day-advice.tsx`:

- divider title
- good/caution counters
- "все 12 сфер" / expand control
- rows with icon, sphere label, advice text, verdict dot
- compact first 6 rows, expandable remaining rows if available

But build rows from real main data:

- Primary: `payload.sphereScores`, sorted by `rank`
- Enrichment: `payload.topFlags` and `payload.notes`
- Labels: `getSphereLabel`
- Advice text: deterministic UI copy derived from contract fields, not fabricated ephemeris calculations

If fewer than 12 real sphere rows are available, render only real rows plus a deterministic "данные появятся после расчёта" graceful row if needed. Do not invent missing astrology.

### 3. Check-in reminder

Use the 3001 evening/check-in visual pattern for the block under the trial card.

Architecture constraint:

- If real check-in status/echo data is available, wire it.
- If not available, render a deterministic CTA/reminder state for today's date only.
- Do not rely on mock API or static fixture data.

### 4. Chart

The oracle includes a chart section below concrete advice when chart data exists.
Main already has `payload.dayChart` contract.

Required:

- Render chart only from `payload.dayChart`.
- If `dayChart` is null, omit the chart or show a clearly graceful unavailable state.
- Do not derive chart from static natal demo constants.

### 5. Clean contracts and imports

- Update the GRACE/module contract comments in touched files.
- Remove stale imports and unused helpers.
- Keep `data-testid` attributes stable for e2e:
  - `today-screen`
  - `day-header`
  - `access-card`
  - `evening-checkin-reminder` or `yesterday-echo-cta`
  - `day-summary-card`
  - `concrete-day-advice`
  - `day-chart` or `day-chart-unavailable`
  - `day-reading`
  - `why-expanded`
  - `week-strip`

## Required Tests

Update and run:

```bash
npx vitest run __tests__/lib/adapt-payload.test.ts __tests__/components/TodayScreen.test.tsx __tests__/guardrails/no-runtime-mocks.test.ts
npx tsc --noEmit --pretty false
E2E_BASE_URL=http://localhost:4444 npx playwright test e2e/mock-visual/day.spec.ts --project=mobile
```

The e2e spec must verify:

- accessible `/day/2026-07-05` reaches ready state
- top section order matches the required order
- internal scroll height exists
- concrete advice is present below the first viewport
- reading/why/week/bottom are reachable after internal scroll
- no missing API fixtures

## Required Visual Evidence

Create Wave 10-specific evidence under:

```text
docs/work/2026-07-07_frontend-corrective-day-migration-wave-10/artifacts/rework-01/
```

Do not write into Wave 09 artifact folders.

Capture at least:

- `3001-day-2026-07-05-top.png`
- `3001-day-2026-07-05-middle.png`
- `3001-day-2026-07-05-bottom.png`
- `main-day-2026-07-05-top.png`
- `main-day-2026-07-05-middle.png`
- `main-day-2026-07-05-bottom.png`
- `summary.json`

`summary.json` must include:

- route
- base URLs
- viewport
- section order detected by `data-testid`
- scroll positions used
- screenshot paths
- SHA256 hashes for each screenshot

Use 3001 as oracle and main preview as candidate. If you use port 4444 for main preview, state that in the report.

## Report

Update `docs/work/2026-07-07_frontend-corrective-day-migration-wave-10/01_agent_report.md`:

- remove stale "Known Gaps"
- list exact product files changed
- list tests run with real results
- list evidence artifacts and hashes
- state whether 3002 was restarted or only 4444 preview was used

## Commit And Callback

Commit only intentional files. Do not include `next-env.d.ts` unless explicitly justified in the report.

After commit, run:

```bash
curl --max-time 10 -X POST http://127.0.0.1:18765/trigger \
  -H "Authorization: Bearer 324b0306c32ffc5f6a64e16076c8c9ac0ee12fbba925cfd3" \
  -H "Content-Type: application/json" \
  -d '{"prompt":"Wave 10 Rework 01 ready for architect review. Report: docs/work/2026-07-07_frontend-corrective-day-migration-wave-10/01_agent_report.md. Review: docs/work/2026-07-07_frontend-corrective-day-migration-wave-10/02_arch_review.md. Rework TZ: docs/work/2026-07-07_frontend-corrective-day-migration-wave-10/03_rework_01_TZ.md. Branch: main. Commit: <commit-hash>."}'
```
