# Architect Review: Wave 04 `/readings` Overview

Date: 2026-07-07
Status: REWORK_REQUIRED
Reviewed branch: `wave-04-readings-visual-migration`
Reviewed commit: `1353b21`
Base commit: `5963618`
TZ: `docs/work/2026-07-07_frontend-migration-wave-04-readings/00_TZ.md`
Agent report: `docs/work/2026-07-07_frontend-migration-wave-04-readings/01_agent_report.md`

## Verdict

Rework is required before Wave 04 can be accepted.

The implementation correctly keeps `/readings` as a real product catalog, preserves navigation to `/readings/horary` and `/readings/natal`, avoids runtime mocks/MSW/demo data, and adds useful structural tests. However, there are blocking contract and process issues.

## Findings

### 1. Important: coming-card test ids are derived from Russian UI copy instead of stable product keys

`components/readings/coming-card.tsx:35` builds the card key from `title.toLowerCase().replace(...)`, which produces selectors such as `readings-card-прогноз-на-месяц`.

This violates the Wave 04 TZ requirement:

```text
coming cards use data-testid="readings-card-<key>"
```

Here `<key>` means the product catalog key from `ComingReading.key` (`month`, `year`, `synastry`, etc.), not localized title text. The current implementation makes the public test contract copy-dependent and non-ASCII.

Evidence:

- `components/readings/coming-card.tsx:35-41`
- `__tests__/components/ReadingsScreen.test.tsx:78`
- `e2e/mock-visual/readings.spec.ts:96`

Required fix:

- Pass the real `r.key` from `ReadingsScreen` into `ComingCard`.
- Render `data-testid="readings-card-month"` / `readings-card-year` / `readings-card-synastry`.
- Update unit and e2e tests to assert the stable key-based ids.

### 2. Important: new component test file lacks GRACE module contract/map

`__tests__/components/ReadingsScreen.test.tsx` is a new code/test file, but it starts directly with imports and does not include the repository-standard `AI_HEADER`, `START_MODULE_CONTRACT`, and `START_MODULE_MAP` blocks.

This violates `AGENTS.md` GRACE Canon for new code files. The new e2e spec did include these blocks, so this is a localized handoff gap.

Evidence:

- `__tests__/components/ReadingsScreen.test.tsx:1`

Required fix:

- Add GRACE header/module contract/module map to `__tests__/components/ReadingsScreen.test.tsx`.
- Keep comments concise and accurate.

### 3. Important: the implementation does not yet perform a visible `/readings` visual migration

The product component diff is almost entirely structural attributes:

```text
components/readings/available-card.tsx      5 insertions, 1 deletion
components/readings/coming-card.tsx         3 insertions
components/readings/in-dev-overlay.tsx      1 insertion, 1 deletion
components/readings/readings-screen.tsx     8 insertions, 6 deletions
```

The visible first-viewport deltas from the mock-preview oracle were not ported. For example:

- `components/readings/readings-screen.tsx:58` still uses plain `text-foreground` for the hero title, while the mock-preview oracle uses the visible cosmic gradient heading.
- `components/readings/available-card.tsx:43` still uses the pre-existing plain card class, while the oracle available card uses the visible `card-glow-hover`/relative/overflow/hover treatment.

Wave 04 is a visual migration wave, not only a semantic-selector wave. The implementation should add the narrow, product-safe visual deltas needed for `/readings` to look like the mock-preview first viewport, without copying unrelated theme/root CSS.

Required fix:

- Add a narrow `/readings` presentation polish for the visible first viewport: gradient heading and available-card visual treatment matching the oracle.
- Keep reduced-motion behavior for any animation.
- Do not copy broad mock-preview CSS/theme blocks.
- Do not port demo blocks/calculators.

### 4. Minor: report is missing one required explicit no-op statement

The report clearly states that runtime mocks/MSW/mock-preview API were not ported, but it does not explicitly state that canonical `3002`, systemd, nginx, and bot config were not changed, which the TZ required.

Required fix:

- Add that explicit statement to the report's rework section.

## Fresh Verification

Architect ran these checks on `1353b21`:

```bash
git diff --check 5963618..1353b21
```

Result: passed, exit code 0.

```bash
git diff --check
```

Result: passed, exit code 0.

```bash
pnpm exec tsc --noEmit --pretty false
```

Result: passed, exit code 0.

```bash
npx vitest run __tests__/components/ReadingsScreen.test.tsx __tests__/api/readings.test.ts __tests__/guardrails/no-runtime-mocks.test.ts
```

Result: 3 files passed, 15 tests passed.

I did not rerun full Vitest/e2e after identifying the blocking contract findings above.

## Rework

Rework instructions are in:

```text
docs/work/2026-07-07_frontend-migration-wave-04-readings/03_rework_01_TZ.md
```
