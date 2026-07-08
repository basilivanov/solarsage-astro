# Wave 16 Calendar Final Visual Parity Review

Date: 2026-07-08
Reviewed commits: `879d897`, `c89a4e8`, `6940169`
Decision: ACCEPTED

## Summary

Wave 16 completed the final calendar visual-parity pass against the `3001` oracle while preserving real backend data and real access states.

Accepted changes:

- segmented control now uses the oracle-style sliding `framer-motion` pill;
- day-mode `MoodIcon` markers now match the oracle emoji badge style;
- lunar strip detail card now has the oracle-style expanded layout and animation;
- lunar legend includes the missing `±1 день` item;
- moon-mode selected ring, VoC dot placement, out-of-month opacity, and summary metadata match the oracle more closely;
- real access differences, such as Basil's `2026-07-12` lock after referral access ends, are preserved.

## Architect Verification

```bash
git status --short --branch && git diff --check HEAD~1..HEAD
```

Result: exit 0. Tracked tree clean except the review/report docs update before this review commit; unrelated local untracked files remain.

```bash
pnpm exec tsc --noEmit --pretty false
```

Result: exit 0.

```bash
cd apps/api && source .venv/bin/activate && python -m pytest tests/test_calendar_endpoints.py -q
```

Result: exit 0, `12 passed in 1.42s`.

```bash
npx vitest run __tests__/components/CalendarScreen.test.tsx __tests__/hooks/useCalendar.test.ts __tests__/contracts/calendar.test.ts __tests__/api/calendar.test.ts __tests__/components/TodayScreen.test.tsx __tests__/app/day-page.test.tsx __tests__/guardrails/no-runtime-mocks.test.ts
```

Result: exit 0, 7 files passed, `62 passed`.

```bash
E2E_BASE_URL=http://localhost:3002 npx playwright test e2e/calendar.spec.ts
```

Result: exit 0, `2 passed`.

```bash
E2E_BASE_URL=http://localhost:3002 npx playwright test e2e/mock-visual/calendar.spec.ts
```

Result: exit 0, `12 passed`.

## Runtime Check

Live `basil_ivanov` screenshot after Wave 16 deploy at `390x844` shows the footer/date/CTA rendered correctly above bottom nav. The apparent crop in the committed high-DPR artifact is not reproduced in the live DPR1 check.

## Push Correction

The tmux agent could not push because its `astro` user did not resolve the custom SSH alias `github.com-solarsage`. Architect pushed from the root context successfully:

```bash
git push origin main
```

Result: exit 0 for commits through `c89a4e8`. This review/report correction commit should be pushed by the architect after this file is committed.
