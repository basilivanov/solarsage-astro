# Oracle Audit TZ: Wave 11 — Full `/day` 3001 vs Main Parity Map

Date: 2026-07-08
Branch: `main`
Role: coding executor / auditor in `tmux astro:0.0`
Architect: current Codex

## Why This Audit Exists

Stop implementation before continuing Wave 11 Rework 01. The previous attempts changed individual components without a complete oracle inventory. We need a full section-by-section and interaction-by-interaction map first.

Do not commit any code in this audit step.
Do not discard existing uncommitted WIP.
Do not continue implementation changes until architect reviews this audit.

## Current State

There are uncommitted WIP changes from Wave 11 Rework 01. Keep them, but treat them as provisional.

Audit targets:

1. Oracle visual source:
   - URL: `http://127.0.0.1:3001/day/2026-07-05`
   - Source tree: `/opt/solarsage-astro-mock-preview`
2. Current candidate:
   - If WIP server is running, use a candidate preview port and state it.
   - Also record whether live `http://127.0.0.1:3002/day/2026-07-05` is pre-WIP or post-restart.
3. Target:
   - main `/day/[date]` should match 3001 frontend presentation and interactions, but use real API/auth/data contracts.

## Audit Deliverables

Write report:

```text
docs/work/2026-07-08_frontend-corrective-day-full-parity-wave-11/04_oracle_audit_report.md
```

Create artifacts:

```text
docs/work/2026-07-08_frontend-corrective-day-full-parity-wave-11/artifacts/audit/
```

Capture at minimum:

- `3001-top.png`
- `3001-middle.png`
- `3001-bottom.png`
- `candidate-top.png`
- `candidate-middle.png`
- `candidate-bottom.png`
- `3001-chart-before.png`
- `3001-chart-after-click.png`
- `candidate-chart-before.png`
- `candidate-chart-after-click.png`
- `summary.json`

## Required Audit Matrix

In the report, include a markdown table with these columns:

```text
Section / Behavior | 3001 Oracle | Current Main/Candidate | Target Decision | Gap | Required Implementation
```

Rows must cover at least:

1. App shell / scroll container / tabbar
2. Date header
3. Trial/access banner
4. Today-only evening/check-in block
5. Day summary/status card
6. `Конкретно сегодня` heading, counts, rows, expand/collapse
7. Day chart visual shell
8. Day chart planet click/tap interaction
9. Day chart popover content
10. Day chart aspect legend
11. Static raw planet list under chart
12. `Сегодня важно`
13. Day reading typography and position
14. `Глубже / Почему так у меня`
15. Week strip
16. `В этот день` / `Ближайшие дни` history block
17. Disclaimer
18. Mobile overflow and text wrapping
19. Data differences allowed because 3002 uses real backend data
20. Data differences not allowed because they are raw/debug presentation leakage

## Required DOM / Interaction Facts

`summary.json` must include:

- base URLs used
- viewport
- scroll positions
- section order for oracle and candidate
- text sample for each section
- whether `today-important-accordion` exists
- whether `astro-history-widget` exists
- visible raw/debug strings found:
  - `Crisis Transformation Control`
  - `Inner Background Unconscious`
  - `Sun ·`
  - `Moon ·`
  - score-looking row suffixes such as `5.5`, `4.4`, `4.2`
- chart interactive planet count for oracle and candidate
- chart popover text after click for oracle and candidate
- screenshot SHA256 hashes

## Target Decisions To Apply In The Audit

Use these decisions; do not reopen them:

1. `Сегодня важно` is hidden on `/day/[date]` for this pass.
2. The chart must be interactive like 3001.
3. The chart must use real `payload.dayChart`, not mock constants.
4. `Конкретно сегодня` must use short product sphere labels and no visible numeric scores.
5. History widget is educational astronomy/space-history content, not astrology snippets.
6. Real-data text may differ from 3001 text, but layout, interaction affordances, and product tone must match.
7. Raw backend/domain labels are defects, not acceptable real-data differences.

## Verification During Audit

Run only lightweight checks needed to produce evidence. Do not run full gates unless already done.

Useful commands:

```bash
curl -sS -o /dev/null -w '3001=%{http_code}\n' http://127.0.0.1:3001/day/2026-07-05
curl -sS -o /dev/null -w '3002=%{http_code}\n' http://127.0.0.1:3002/day/2026-07-05
```

If a preview port is used for candidate, include its URL and HTTP status in the report.

## Callback

After writing the audit report and artifacts, run:

```bash
curl --max-time 10 -X POST http://127.0.0.1:18765/trigger \
  -H "Authorization: Bearer 324b0306c32ffc5f6a64e16076c8c9ac0ee12fbba925cfd3" \
  -H "Content-Type: application/json" \
  -d '{"prompt":"Wave 11 Oracle Audit ready for architect review. Report: docs/work/2026-07-08_frontend-corrective-day-full-parity-wave-11/04_oracle_audit_report.md. Artifacts: docs/work/2026-07-08_frontend-corrective-day-full-parity-wave-11/artifacts/audit/. Branch: main. No commit."}'
```
