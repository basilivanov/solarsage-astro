# Packet 01 — Telegram content safe area

## Packet title

Today mobile readability / Telegram content-safe-area propagation

## Phase / Wave

W-TODAY-MOBILE-READABILITY / 01

## Modules

- M-COMPONENTS-TELEGRAM-INIT
- M-APP-DAY-PAGE
- M-CALENDAR-CALENDAR-SCREEN
- M-TODAY-IMPULSE-DRILLDOWN

## Goal

Propagate Telegram `contentSafeAreaInset.top` into a CSS variable with fallback and apply it to all in-scope top controls so iPhone Telegram's Dynamic Island/Mini App close control cannot cover content.

## Exact write scope

- `components/telegram-init.tsx`
- `app/(grace)/day/[date]/page.tsx`
- `components/calendar/calendar-screen.tsx`
- `components/today-convergence/impulse-drilldown-sheet.tsx`
- the narrowest existing frontend test files needed for this behavior

## Frozen / out of scope

- No backend or OpenAPI changes.
- No redesign of modal content (packet 02 owns that).
- No global rewrite of every screen's safe-area styles.
- No baseline PNG changes.

## Must preserve

- Existing Telegram viewport expansion and `--app-height` behavior.
- Existing `data-testid`, `aria-*`, and Today state contracts.
- Non-Telegram browser fallback using `env(safe-area-inset-top)`.
- Modal remains a dialog with Escape handling.

## Verification

`npx vitest run components/today-convergence/__tests__/today-screen.test.tsx components/calendar/__tests__/calendar-screen.test.tsx`

Also run `git diff --check` and frontend GRACE marker check.

## Expected evidence

Diff limited to scope, targeted tests green, and a note showing the CSS variable fallback and change-event cleanup.

## Escalation

If a shared shell/global CSS change is required, stop and report; do not absorb it into this packet.

## No-commit rule

Do not commit or push. The reviewer will integrate and commit.
