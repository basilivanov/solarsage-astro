# Architect Review: Wave 10 Rework 01

Date: 2026-07-07
Branch: `main`
Reviewed commit: `59506ba`
Status: REJECTED

## Summary

Rework 01 is materially closer to the 3001 oracle than the previous attempt:

- the large standalone headline was removed from the top flow;
- the compact summary and concrete advice section now follow the oracle style;
- runtime mock astrology helpers were not copied;
- top/middle/bottom evidence exists.

It is still not acceptable because the evidence screenshots show two visible composition mismatches on the reviewed route `/day/2026-07-05`.

## Findings

### P1 — Non-today route incorrectly renders the check-in card

File: `components/today/today-screen.tsx`
Lines: 171-173, 259-277

For `/day/2026-07-05` the main screenshot shows a visible card:

```text
Вечерний чек-ин
Отметка доступна в актуальный день.
```

The 3001 oracle screenshot for the same route does not show this card. This also violates the previous TZ:

```text
If not available, render a deterministic CTA/reminder state for today's date only.
```

Required behavior:

- For `isToday === true`, render the real existing check-in/echo loader or a today-only deterministic CTA if no data is available.
- For `isToday === false`, omit the entire check-in section. Do not render a placeholder card.
- Update unit/e2e tests so `/day/2026-07-05` asserts that the check-in section is absent when the selected date is not today.

### P1 — Bottom history section from the 3001 oracle is missing

File: `components/today/today-screen.tsx`

The 3001 bottom evidence includes:

```text
БЛИЖАЙШИЕ ДНИ
1997 · миссия
«Марс Пасфайндер» на Марсе
```

The main bottom evidence goes from `WeekStrip` directly to the disclaimer. This is a visible below-fold mismatch.

The 3001 source component is `/opt/solarsage-astro-mock-preview/components/today/astro-history-widget.tsx`.
It is static curated educational astronomy/history content, not runtime mock astrology, so it can be ported if documented as static content.

Required behavior:

- Add a main `AstroHistoryWidget` or equivalent curated-content component.
- Render it after `WeekStrip` and before `today-bottom-disclaimer`.
- Add `data-testid="astro-history-widget"`.
- Keep it deterministic by `selectedDate` and not dependent on mock APIs.
- Keep the curated static list clearly scoped to educational display content, not as a fake backend response.

### P2 — Evidence should be regenerated after the composition fixes

Current evidence is useful but captures the rejected state.

Regenerate Wave 10-specific evidence in:

```text
docs/work/2026-07-07_frontend-corrective-day-migration-wave-10/artifacts/rework-02/
```

Do not overwrite `rework-01` or Wave 09 artifacts.

Required visible checks:

- `main-day-2026-07-05-top.png` has no non-today check-in card.
- `main-day-2026-07-05-bottom.png` includes the history section before disclaimer.
- `summary.json` includes `astro-history-widget` in main section order.

### P2 — Generated `next-env.d.ts` remains dirty

File: `next-env.d.ts`

The working tree still contains a generated side effect:

```diff
-import "./.next/types/routes.d.ts";
+import "./.next/dev/types/routes.d.ts";
```

Do not commit this. Restore the file content to the tracked canonical import before final rework commit unless a separate architecture decision is made.

## Decision

Reject Rework 01. Implement `05_rework_02_TZ.md`.
