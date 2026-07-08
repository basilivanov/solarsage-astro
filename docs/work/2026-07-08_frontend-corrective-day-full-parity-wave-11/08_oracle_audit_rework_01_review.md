# Wave 11 Oracle Audit Rework 01 Review

Status: **ACCEPTED WITH ARCHITECT AMENDMENTS**

The reworked audit is reliable enough to drive implementation. It fixed the main failure from the previous audit: 3001 is now captured as the actual visual oracle instead of being evaluated through candidate-only `data-testid`s.

Accepted evidence:

- `artifacts/audit-rework-01/3001-00-full-scroll.png`
- `artifacts/audit-rework-01/candidate-00-full-scroll.png`
- `artifacts/audit-rework-01/3001-04-chart-after-click.png`
- `artifacts/audit-rework-01/candidate-04-chart-after-click.png`
- `artifacts/audit-rework-01/summary-v2.json`

## Architect Amendments

### A1. Day summary values may differ, but the presentation shell must match

The report marks the day summary card as `ALLOWED_DATA_DIFF`. That is only partially correct.

Allowed real-data differences:

- `Ровный день` vs `Поддерживающий день`
- lunar percentage/value
- top flag/planet text derived from real backend/calendar data

Not allowed:

- losing the 3001 compact structure,
- showing a different card hierarchy,
- omitting the selected weekday/date line when real date data is available,
- replacing compact facts with raw backend/debug labels.

The implementation must use the 3001 shell while preserving real data.

### A2. Day chart shell is also a presentation gap

The report marks day chart visuals as `MATCH`, but the screenshots show a visible shell difference:

- 3001 renders the wheel as an unframed oracle-style chart directly after concrete advice, with the date and `КАРТА ДНЯ` inside the wheel and a static aspect legend below.
- Candidate renders a bordered card with a top header `КАРТА ДНЯ / SOLARSAGE` and raw aspect pair labels.

This is a presentation gap. The implementation must match the 3001 visual shell more closely while still using real `payload.dayChart`.

### A3. Planet count is not a hard gap

The audit records `oracle=7` and `candidate=10` chart planets. Do **not** hide real planets just to match the mock count. Planet count is data-dependent.

Required parity is:

- same visual style,
- same interaction class,
- same Russian popover format,
- same static aspect-type legend,
- no raw English labels.

### A4. Backend contract is not required for this wave

The visible gaps can be closed on the frontend display/adapter layer:

- technical sphere keys -> 12 product-facing sphere labels,
- English sign names -> Russian sign labels,
- aspect types -> static Russian legend,
- history data -> curated educational astronomy/space card.

Do not add backend fields unless implementation proves that a frontend-only adapter cannot preserve real data. Do not fabricate astrological calculations on the frontend.

## Decision

Proceed to implementation from this audit plus the amendments above.

