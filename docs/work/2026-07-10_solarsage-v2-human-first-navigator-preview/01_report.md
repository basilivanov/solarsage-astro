# Human-first V2 sphere navigator — report

## Architecture

The V2 Today flow is now human-first: compact backend-owned day summary, personal story, always-visible 12-sphere navigator, then an optional Why explanation before chart and reading. `TodayScreen` owns the selected sphere and controlled Why state; callbacks scroll and focus only after React commits. No client-side astrology, ranking, score calculation, or fixture imports were added to product runtime.

`ActivationEvidenceCard` is deliberately migrated from an evidence disclosure to a V2 personal story. It renders the backend V2 headline, the minimum-rank concrete advice row, and at most three mapped sphere links. `ConcreteDayAdvice` is a controlled two-column navigator with one full-width detail panel after the selected pair. `WhyExpanded` keeps human explanation separate from the nested, opt-in technical calculation.

The follow-up hardening pass makes human surfaces reject Unicode technical forms (including Russian inflections) and use only a safe explicitly supplied backend fallback headline. Evidence selection falls back to active backend order if primary IDs resolve to nothing; the grouped long background is restricted to `period` evidence. Hero and navigator callbacks are mandatory, and repeated hero/Why actions repeat their scroll/focus behavior.

## Changed files

- `components/today/day-summary-card.tsx` — V2 compact human-first presentation while retaining legacy facts.
- `components/today/activation-evidence-card.tsx` — personal story hero and callbacks.
- `components/today/concrete-day-advice.tsx` — 12 visible controlled sphere tiles and non-technical details.
- `components/today/why-expanded.tsx` — controlled Why, safe human items, and nested technical calculation.
- `components/today/today-screen.tsx` — V2 ordering, selection/Why state, scroll/focus wiring, date reset.
- `lib/presentation/today-v2.ts` — pure labels, banned-vocabulary guard, safe Why copy, verdict text, technical evidence selection.
- component/unit tests and `e2e/mock-visual/day-v2.spec.ts` — public contract, interaction, visual and fixture guard coverage.
- `e2e/mock-visual/day-v2.spec.ts-snapshots/` — replaced obsolete evidence-card baselines with the four navigator states.

## Public DOM/test contract

- `activation-evidence-card`: `data-state="ready"`, `aria-label="Личный сюжет дня"`; sphere buttons use `personal-story-sphere-link`, and the Why CTA uses `personal-story-why-cta`.
- `concrete-day-advice`: `aria-label="Быстрый навигатор по 12 сферам"`; every row uses `concrete-day-advice-row` plus `data-sphere-key`, `data-status`, `data-selected`, `aria-expanded`, and `aria-controls`.
- Selected panel uses `concrete-day-advice-details`, `role="region"`, `data-sphere-key`, and `aria-labelledby`.
- `why-expanded` is controlled-capable and supports `?why=1` plus `?why=1&astro=1`; nested technical disclosure uses `astrology-calculation` and `astrology-calculation-toggle`.

## Test-id migration

`concrete-day-advice-evidence` was removed in favour of `concrete-day-advice-details`: the old name described leaked evidence, while the new full-width panel is a human-first sphere detail panel. All affected unit and Playwright tests now use the new public selector. Old V2 card snapshots were replaced because their expansion no longer exists in this UX.

## Verification

- Targeted Vitest: 6 files, 42 tests passed.
- Full Vitest: 91 files, 937 tests passed.
- TypeScript: `npx tsc --noEmit` passed.
- Production build: `pnpm build` passed.
- Playwright baseline update: mobile V2 spec, 1 passed.
- Playwright verification: mobile V2 spec, 1 passed.
- HTTP checks: preview `3003/day/2026-07-08` returned 200; production `3002/` returned 200.
- Listener check: preview Next is on `0.0.0.0:3003`, test-only mock API is on `127.0.0.1:18092`, production remains on `3002`.
- Visual self-review: all four assets were inspected for clipping, target size, navigator panel placement, horizontal overflow, contrast, and separation of human/technical copy.

## Screenshots

- `docs/work/2026-07-10_solarsage-v2-human-first-navigator-preview/assets/01-human-first-overview-mobile.png`
- `docs/work/2026-07-10_solarsage-v2-human-first-navigator-preview/assets/02-work-sphere-expanded-mobile.png`
- `docs/work/2026-07-10_solarsage-v2-human-first-navigator-preview/assets/03-why-human-and-astro-expanded-mobile.png`
- `docs/work/2026-07-10_solarsage-v2-human-first-navigator-preview/assets/04-full-day-human-first-mobile.png`

## Commit and scope

- Implementation commit: `09f8878d15f321ee49a7f2fc3de0b5ebf9ee68b4`.
- Follow-up implementation hardening: `5581604ba4fb7336b66b536fbbf9166b190b830c`.
- Report commit SHA is self-referential and is recorded in the final handoff after this file is committed.
- `main`, production frontend `3002`, API `8000`, sidecar `18091`, nginx, flags, and systemd units were not changed or restarted.
- User-owned untracked `.grace/`, `artifacts/design/`, `docs/superpowers/plans/2026-07-05-fix-day-route-auth-build.md`, `grace.db`, and `skills/` were not staged.
- Known limitations: Day chart remains unavailable in the isolated fixture when no chart payload is supplied; the navigator does not fabricate it.
