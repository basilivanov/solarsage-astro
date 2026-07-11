# Three-horizon Why preview — final report

## Delivery

- Branch: `preview/solarsage-v2-human-first-navigator-ux`
- Baseline: `386d211bfef6148fa3d3207d280771de91c42ae3`
- Implementation commit: `c5570f1f3f220872789d8bb675c945ef8f19a060`

## Product model

The expanded Why block now turns backend-owned activation evidence into one personal
story at three visible speeds, in a fixed order:

1. **Большой сюжет** — long horizon, `1 год → несколько лет`.
2. **Активная волна** — medium horizon, `2–6 месяцев вокруг пика`.
3. **Триггер сегодня** — fast horizon, `несколько часов → 2 суток`.

The human narrative is shown before the optional calculation disclosure. The
disclosure groups the selected evidence by horizon and explains techniques,
planets, aspects, stages, and orbs without raw backend IDs or debug fields.

Representative selection:

- long: annual profection + firdar major;
- medium: Pluto trine Saturn + Neptune opposition Saturn;
- fast: Moon opposition Pluto.

## Safety and fallbacks

- A complete V2 block with selected horizons renders the three-horizon story and
  the optional technical disclosure.
- Standalone safe `whyToday`, or V2 `whyToday` whose evidence does not pass the
  horizon thresholds, renders a human-only numbered list without technical UI.
- Empty V2 data without safe why items or legacy sections renders no Why block.
- Legacy sections keep their existing flow.
- The technical glossary covers every supported technique and all ten known
  planets. Transit and natal-card explanations are fully Russian.
- Annual profection descriptions are target-type safe: they localize planets and
  known spheres and never expose a raw `targetKey`.

## Changed files

- `components/today/why-time-horizon-card.tsx`
- `components/today/why-expanded.tsx`
- `lib/presentation/today-v2.ts`
- `__tests__/lib/presentation/today-v2.test.ts`
- `__tests__/components/TodayScreen.v2-downstream.test.tsx`
- `e2e/mock-visual/day-v2.spec.ts`
- `e2e/mock-visual/fixtures/day-v2-2026-07-08.ts`
- `e2e/mock-visual/fixtures/json/day-v2-2026-07-08.json`
- six `three-horizons` Playwright snapshots in
  `e2e/mock-visual/day-v2.spec.ts-snapshots/`
- task specification, architecture reviews, finalization instructions, and the
  three review assets in this work directory.

## Review assets

- `assets/01-why-three-horizons-mobile.png`
- `assets/02-why-three-horizons-calculation-mobile.png`
- `assets/03-full-day-three-horizons-mobile.png`

## Verification

- Scoped Vitest: 2 files / 33 tests passed.
- Full Vitest reviewer gate: 91 files / 954 tests passed.
- `npx tsc --noEmit` passed.
- `git diff --check` passed.
- Mobile Playwright update and no-update verification passed.
- Preview `http://127.0.0.1:3003/day/2026-07-08?why=1` returned `200`.

## Boundaries preserved

- Production was untouched.
- `main` and merge state were untouched.
- Known unrelated untracked paths were left untouched.
