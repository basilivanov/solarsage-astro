# Wave 11 Oracle Audit Rework 01 TZ

You are the coder/auditor agent. Do **not** implement product changes in this step. Do **not** commit. Preserve current WIP. This is an audit gate only.

## Objective

Produce a trustworthy visual and interaction audit for `/day/2026-07-05` comparing:

- Oracle: `http://127.0.0.1:3001/day/2026-07-05`
- Candidate: current main/WIP preview, preferably `http://127.0.0.1:7777/day/2026-07-05` if already running

The output must be good enough for the architect to write the next implementation TZ without guessing.

## Why Rework Is Required

The previous audit is rejected in `05_oracle_audit_review.md`.

Main problems:

- The 3001 chart was not captured because the script relied on candidate-only `data-testid="day-chart"`.
- The report claims no gaps while screenshots show major visual differences.
- Raw/debug string detection says clean while candidate screenshots visibly show labels such as `Crisis Transformation Control`.
- Chart click/tap interaction is not proven.
- Bottom/history section parity is incorrectly marked as complete.

## Scope

Primary date: `/day/2026-07-05`.

If a section is today-only and not visible for this date, record that explicitly. Do not claim parity for today-only states unless you also capture the current-date route separately.

## Audit Method

Use both automation and manual visual inspection.

Important: 3001 is the oracle and may not have the same `data-testid`s as candidate/main. For 3001, anchor by visible Russian text and layout:

- `ДЕНЬ`, `5 июля`
- `14 дней бесплатного доступа`
- `Ровный день`
- `КОНКРЕТНО СЕГОДНЯ`
- `КАРТА ДНЯ`
- chart legend texts: `соединение`, `оппозиция`, `тригон`, `квадратура`, `секстиль`
- `РАЗБОР ДНЯ`
- `Почему так у меня`
- `Неделя`
- `Ближайшие дни`

Do not use candidate-only test ids to decide what exists in 3001.

## Required Artifacts

Create a new artifact folder:

`docs/work/2026-07-08_frontend-corrective-day-full-parity-wave-11/artifacts/audit-rework-01/`

Capture at minimum:

- `3001-00-full-scroll.png` or a stitched equivalent of the scroll container.
- `candidate-00-full-scroll.png` or a stitched equivalent.
- `3001-01-top.png` and `candidate-01-top.png`.
- `3001-02-concrete-today.png` and `candidate-02-concrete-today.png`.
- `3001-03-chart-before.png` and `candidate-03-chart-before.png`.
- `3001-04-chart-after-click.png` and `candidate-04-chart-after-click.png`.
- `3001-05-reading-why-week-history.png` and `candidate-05-reading-why-week-history.png`.
- `summary-v2.json`.

`summary-v2.json` must include actual observed values, not hardcoded booleans:

```json
{
  "date": "2026-07-05",
  "oracle": {
    "sections": [],
    "visibleTextSamples": [],
    "chart": {
      "found": true,
      "legendTexts": [],
      "clickTargetCount": 0,
      "afterClickVisibleText": ""
    },
    "rawDebugStrings": []
  },
  "candidate": {
    "sections": [],
    "visibleTextSamples": [],
    "chart": {
      "found": true,
      "legendTexts": [],
      "clickTargetCount": 0,
      "afterClickVisibleText": ""
    },
    "rawDebugStrings": []
  },
  "gaps": []
}
```

## Required Report

Write:

`docs/work/2026-07-08_frontend-corrective-day-full-parity-wave-11/07_oracle_audit_rework_01_report.md`

The report must contain:

1. **Audit Decision**: whether the audit is reliable enough to implement from.
2. **3001 Oracle Inventory**: exact section order, layout notes, visible text samples, interactions.
3. **Candidate Inventory**: same structure.
4. **Gap Matrix** with one of these statuses per row:
   - `MATCH`
   - `ALLOWED_DATA_DIFF`
   - `PRESENTATION_GAP`
   - `INTERACTION_GAP`
   - `NEEDS_BACKEND_CONTRACT`
5. **Implementation Contract Draft**:
   - what frontend components must change,
   - what adapters/label maps are needed,
   - whether any backend/API contract extension is required,
   - what must be hidden/removed.
6. **Evidence Links** to the screenshots and `summary-v2.json`.

## Specific Things To Verify

### Top and summary

Compare:

- date header styling,
- trial/access banner,
- day summary card title and compact facts,
- whether real-data values can be substituted while keeping 3001 presentation.

### Concrete today

Compare:

- heading,
- count row,
- sphere filter label,
- row density,
- icons,
- short Russian sphere labels,
- expand/collapse behavior,
- absence of raw score/debug suffixes.

Raw labels such as `Crisis Transformation Control` and `Inner Background Unconscious` are presentation gaps. They must be captured as gaps if still visible.

### Day chart

Compare:

- wheel frame,
- zodiac signs,
- houses,
- planet markers,
- aspect lines,
- legend labels and colors,
- selected/clicked state,
- visible details after click/tap.

If 3001 interaction cannot be automated, use manual coordinates plus screenshots and record exactly what was clicked.

### Reading / why / week / history

Compare:

- `РАЗБОР ДНЯ` typography and drop-cap behavior,
- `Почему так у меня` accordion/card,
- week strip structure and icons,
- history block title and card layout.

The 3001 history block currently appears as `Ближайшие дни` with a large year card. If candidate shows `В этот день` with multiple compact rows, mark it as a presentation gap.

## Validation Rules

- No product implementation changes in this step.
- No commit.
- Do not claim tests are green unless you actually ran them and include exact command/output summary. Full tests are not required for this audit gate.
- If a capture fails, say it failed and why. Do not infer parity from missing evidence.
- Keep the current WIP intact.

## Callback

When done, run:

```bash
curl -X POST http://127.0.0.1:18765/trigger \
  -H "Authorization: Bearer 324b0306c32ffc5f6a64e16076c8c9ac0ee12fbba925cfd3" \
  -H "Content-Type: application/json" \
  -d '{"prompt":"Wave 11 Oracle Audit Rework 01 ready for architect review. Report: docs/work/2026-07-08_frontend-corrective-day-full-parity-wave-11/07_oracle_audit_rework_01_report.md. Artifacts: docs/work/2026-07-08_frontend-corrective-day-full-parity-wave-11/artifacts/audit-rework-01/. Branch: main. No commit."}'
```

