# Wave 11 Day Oracle Parity Implementation Review

Status: **REJECTED — REWORK REQUIRED**

Reviewed commits:

- Product/docs/evidence commit: `1d3f290fbc6997e26848d55a3f18f75299fdbe89`
- Report commit / current HEAD: `4cf0e162184e1559a879d5a9546c65f4eeee7e17`

Verification run by architect:

```bash
npx vitest run __tests__/lib/display/sphere-labels.test.ts
# 6 passed

npx vitest run __tests__/components/TodayScreen.test.tsx
# 14 passed

E2E_BASE_URL=http://127.0.0.1:7777 npx playwright test e2e/mock-visual/day.spec.ts
# 8 passed
```

Tests are green, but the implementation still violates the architectural/visual contract.

## Blocking Findings

### P1. Day summary card still does not match the 3001 oracle shell

File: `components/today/day-summary-card.tsx`

Current implementation renders:

- selected date line outside the card (`lines 75-79`);
- a large standalone status emoji (`line 83`);
- status title below that emoji (`lines 86-87`).

This is visible in:

- `artifacts/implementation-01/candidate-01-top.png`

The 3001 oracle renders the date/weekday and day status in the compact card header:

- left: `5 ИЮЛ · ВОСКРЕСЕНЬЕ`
- right: status label such as `🌊 Ровный день`
- below: one-line day advice and compact fact rows

The TZ explicitly required the 3001 shell, and the current UI still has a different hierarchy. This is exactly the class of top-screen mismatch the user called out.

### P1. Concrete advice can invent neutral advice for missing real sphere data

File: `components/today/concrete-day-advice.tsx`

When a canonical product bucket has no matching backend score, `buildAdviceRows()` creates a neutral row with `score: 5.0` and product advice text (`lines 210-220`). That makes the UI look data-backed even when the backend did not provide that sphere.

This violates the rule: frontend may translate/aggregate real data, but must not fabricate astrology/advice as if it came from real scoring.

Required behavior:

- if a product bucket has real mapped scores, derive verdict/text from those scores;
- if a product bucket has no real mapped score, render a visibly safe unavailable/low-confidence text such as `Нет отдельного сигнала на эту сферу`, with `verdict: unavailable`;
- counts (`N благоприятно`, `N осторожно`) must count only real scored buckets, not unavailable filler rows.

### P1. Some backend keys map outside the canonical 12 rows and are silently ignored

File: `lib/display/sphere-labels.ts`

`home_family_roots` and `home_family` currently map to `Семья` (`lines 166-168`), but `ConcreteDayAdvice` only keeps rows whose mapped label equals one of the canonical 12 labels (`components/today/concrete-day-advice.tsx`, `lines 188-193`).

Result: real backend data for those keys is dropped and replaced by neutral fabricated filler. The TZ required every known backend key to map into the 12 product buckets.

Required behavior:

- define a `ProductSphereKey` / canonical product bucket contract;
- map every known backend key to one of those 12 bucket keys, not by comparing display labels;
- never keep a mapping to a label outside the canonical 12 for `ConcreteDayAdvice`.

### P1. Unknown sphere fallback still leaks English-looking labels

File: `lib/display/sphere-labels.ts`

`getSphereLabel("some_unknown_key")` returns `Some Unknown Key` (`lines 70-84`), and the unit test asserts that behavior (`__tests__/lib/display/sphere-labels.test.ts`, `lines 30-34`).

This contradicts the implementation TZ:

> Unknown keys must map to a safe product bucket or a safe generic label such as `Сфера`, never `Some English Key` and never snake_case.

Required behavior:

- unknown user-facing label fallback must be safe Russian text, e.g. `Сфера` or `Другая сфера`;
- update tests to assert no title-cased English fallback.

## Important Findings

### P2. Day chart semantic labels still contain raw English sign names

File: `components/today/day-chart.tsx`

Visible popover text is fixed, but `aria-label` still uses `planet.sign` raw (`line 169`), so the semantic/test contract can expose `Cancer`, `Libra`, etc.

Required behavior:

- use the same Russian sign formatter for visible text and accessibility labels.

### P2. Evidence artifact for bottom/history is wrong

File:

- `artifacts/implementation-01/candidate-05-reading-why-week-history.png`

The file shows the top viewport, not reading/why/week/history. `candidate-00-full-scroll.png` does show the bottom, so this is an evidence/capture issue rather than a product UI issue.

Required behavior:

- fix the capture script/scroll target;
- regenerate `candidate-05-reading-why-week-history.png` so it actually shows the bottom section.

### P2. Report SHA is inconsistent

The callback says `Commit: 4cf0e16`, while the implementation report body says `1d3f290`.

Required behavior:

- next report should list both if there are two commits:
  - implementation commit,
  - report/evidence commit / HEAD.

## Acceptance Criteria For Rework

The next review can accept when:

1. Day summary card visually matches the 3001 compact header/card structure.
2. Concrete advice never displays product advice for unscored/missing buckets as if it were real data.
3. Every known backend sphere key maps into one of the canonical 12 product buckets.
4. Unknown sphere fallback is safe Russian generic text.
5. Day chart accessibility labels use Russian sign labels.
6. Bottom/history evidence screenshot is correct.
7. Required tests still pass.

