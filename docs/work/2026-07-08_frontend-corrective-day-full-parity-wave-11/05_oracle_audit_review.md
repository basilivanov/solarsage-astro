# Wave 11 Oracle Audit Review

Status: **REJECTED**

The audit report is not reliable enough to drive implementation. It concludes that the candidate already has full parity with the 3001 oracle, but the attached screenshots and `summary.json` contradict that conclusion.

## Blocking Findings

### P1. 3001 oracle chart was not actually captured

`artifacts/audit/summary.json` reports:

- `oracle.sectionOrder`: only `["week-strip"]`
- `oracle.planetCount`: `0`
- `oracle.popoverText`: empty
- `oracle.hashes.chartBefore` equals `oracle.hashes.top`
- `oracle.hashes.chartAfter` equals `oracle.hashes.top`

The screenshot `artifacts/audit/3001-chart-before.png` is the top viewport, not the chart section. The capture script searches for `[data-testid="day-chart"]`, which is a candidate/main implementation detail and is not present in the 3001 oracle. As a result, the audit did not prove the 3001 chart structure or interaction.

The matrix row saying the 3001 chart has no aspect legend is also contradicted by `artifacts/audit/3001-middle.png`, where the oracle visibly has a legend: `соединение`, `оппозиция`, `тригон`, `квадратура`, `секстиль`.

### P1. Report marks raw/debug strings clean while screenshots show leaks

`summary.json` says all `rawDebugStringsFound` flags are `false`, but `artifacts/audit/candidate-top.png` visibly contains backend/internal sphere labels:

- `Crisis Transformation Control`
- `Inner Background Unconscious`

This means the raw/debug string check is not evidence-based. The report cannot claim clean presentation while visible screenshots contain non-product labels.

### P1. Top-of-page parity is false

`artifacts/audit/3001-top.png` and `artifacts/audit/candidate-top.png` are materially different:

- 3001 oracle summary card: `Ровный день`, short Russian lines, moon phase, ruler, hour, void moon.
- Candidate summary card: `Поддерживающий день`, different structure, different iconography, fewer compact facts.
- 3001 concrete advice uses short Russian sphere labels such as `Работа`, `Деньги`, `Документы`, `Отношения`.
- Candidate still renders raw/backend-like labels and different advice text.

This is not an allowed real-data difference. Real data may change content values, but the presentation contract and product labels must match the 3001 UI.

### P1. Bottom/history parity is false

`artifacts/audit/3001-bottom.png` and `artifacts/audit/candidate-bottom.png` show different history widgets:

- 3001 oracle: heading `Ближайшие дни`, one curated card with large year and category label.
- Candidate: heading/content `В этот день`, multiple compact list rows, duplicated `1997 · миссия`.

The report row saying the history widget is the same is incorrect.

### P1. Interaction evidence is missing

`summary.json` has `candidate.popoverText: ""` and `oracle.popoverText: ""`. `candidate-chart-after-click.png` does not show a selected-planet popover. The report claims planet click/tap parity, but the evidence does not prove it.

For this wave, interactive chart parity must include:

- a screenshot before click,
- a screenshot after click,
- the captured visible text/state after click,
- confirmation that the same class of interaction exists in 3001 and candidate.

### P2. Matrix contains unsupported claims

Examples:

- Trial/access banner row says 3001 has none, but `3001-top.png` shows the trial banner.
- Today-only check-in row says same, but `/day/2026-07-05` is not today's date and this conditional state was not audited.
- Tests are reported as passing with a caveat about an unrelated permission error. That is not useful for an audit gate and should not be used as acceptance evidence here.

## Required Next Step

Do not proceed to implementation from this audit. Do not commit current WIP.

Run an audit rework that:

1. Captures 3001 using text/visual anchors, not candidate-only `data-testid`s.
2. Produces a section-by-section visual inventory of 3001.
3. Produces a candidate gap matrix with real gaps preserved.
4. Separates allowed data differences from presentation contract differences.
5. Captures interaction evidence for the day chart.

