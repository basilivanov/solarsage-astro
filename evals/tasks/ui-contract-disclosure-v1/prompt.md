# Eval task — UI semantic contract disclosure v1

## Packet

- Phase / Wave: `EVAL-UI-CONTRACT-V1`
- Modules: `M-COMPONENTS-CHECKIN-STATISTICS`
- Goal: bring the Profile check-in statistics section fully in line with the
  repository's UI Semantic/Test Contract and add a contract-compliant
  collapsible methodology block.

Work autonomously in the provided repository. Do not use subagents or delegate
the task. Do not commit, push, install system packages, access secrets, or modify
files outside the exact write scope. Run the targeted checks before reporting.

The repository's UI Semantic/Test Contract (see `AGENTS.md`) requires that the
user, the accessibility tree and headless tests see the same public UI
contract. Follow it exactly.

## Required behavior

### 1. State contract on the root section

Every rendered state of `CheckinStatistics` must expose the root
`data-testid="profile-checkin-statistics"` together with
`data-state="loading" | "error" | "ready"`:

- loading: the existing skeleton keeps `role="status"` and `aria-busy="true"`
  and gains the root testid/state;
- error: the existing message keeps `role="alert"` and gains the root
  testid/state;
- ready: the existing populated section adds `data-state="ready"`;
- empty (`totalCheckins === 0`) intentionally keeps rendering nothing — do not
  invent an empty-state card.

Visual layout, spacing and text of existing states must not change.

### 2. Methodology disclosure

Inside the ready state, add a collapsible block explaining how the statistics
are computed:

- a `<button type="button">` with the exact label `Как считается статистика`,
  `data-testid="checkin-stats-methodology-toggle"`, `aria-expanded` reflecting
  the state and `aria-controls="checkin-stats-methodology"`;
- a region with `id="checkin-stats-methodology"`,
  `data-testid="checkin-stats-methodology"`, hidden while collapsed;
- collapsed by default; toggling opens/closes without a page reload;
- static Russian text inside covering: the 30-day window of the metrics, the
  1–5 mood scale, and that the streak counts consecutive days with a check-in.
  Static text only — no API or LLM content.

## Exact write scope

- `components/profile/checkin-statistics.tsx`
- `__tests__/components/CheckinStatistics.test.tsx`
- `__tests__/components/ProfileScreen.test.tsx`
- `grace/verification-matrix.md`

## Required evidence

- A new `__tests__/components/CheckinStatistics.test.tsx` covering:
  all three root states with their `data-state` values; the disclosure's
  default `aria-expanded="false"`; `aria-controls` pointing at an existing
  region; toggling updates `aria-expanded` and reveals the region; and the
  three static methodology facts being present.
- `__tests__/components/ProfileScreen.test.tsx` kept green (update only what
  the contract change legitimately breaks).
- GRACE contracts/maps kept accurate in the touched source file and the
  verification matrix updated for the new behavior.
- A final report listing changed files and the exact commands/results run.

## Frozen / out of scope

- Any other component or screen; the check-in API and its payload shape.
- Styling redesign beyond the small disclosure row.
- New dependencies, mock/fixture API layers, production configuration.

## Verification

Run at least:

```bash
npx vitest run __tests__/components/CheckinStatistics.test.tsx __tests__/components/ProfileScreen.test.tsx
npx tsc --noEmit
python3 scripts/grace_front_lint.py components/profile/checkin-statistics.tsx
git diff --check
```

If correct implementation requires a file outside the exact write scope, stop
and report the missing scope instead of changing that file.
