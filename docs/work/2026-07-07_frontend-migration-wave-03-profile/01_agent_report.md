# Agent Report: Wave 03 — `/profile` Real-Data Visual Migration

Date: 2026-07-07
Agent: coding-executor (DeepSeek 4.2 Flash)
Branch: `wave-03-profile-visual-migration`
Base: `b3888ec`

## Summary

Wave 03 migrates the `/profile` screen presentation toward the mock-preview visual oracle while keeping all data flowing through real product APIs (`/api/profile`, `/api/access`, `/api/horary/quota`, `/api/referral`, `/api/checkin/metrics`).

No backend contracts were changed. No runtime mocks, MSW, or client-side astrology calculations were introduced.

## Changes Made

### Modified files

| File | Change |
|------|--------|
| `app/(grace)/profile/page.tsx` | Fixed default `rewardDays` from 7 to 14 |
| `lib/api/profile-meta.ts` | Map `daysPerInvite` from backend response into `rewardDays`; compute `bonusDays = count * rewardDays` |
| `components/profile/profile-screen.tsx` | Added `data-testid="profile-screen"`, `data-state`, `data-access-state` on root; added section testids (`profile-header`, `profile-access-card`, `profile-referral-card`, `profile-horary-card`, `profile-data-section`, `profile-service-section`); added `testId` prop on each `ProfileRow` |
| `components/profile/profile-row.tsx` | Added optional `testId` prop → `data-testid` on the button |
| `components/profile/edit-sheet.tsx` | Added `data-testid="profile-edit-sheet"` on dialog container |
| `components/profile/checkin-statistics.tsx` | Added `data-testid="profile-checkin-statistics"` on section |
| `e2e/mock-visual/profile.spec.ts` | New: 4 mock visual e2e tests (ready, edit-sheet, overflow, negative-proof) |
| `e2e/mock-visual/fixtures/profile.ts` | New: contract-valid fixtures for profile, access, horary quota, referral, checkin metrics |

### Not changed (preserved)

- Backend contracts unchanged
- No `lib/mocks/*`, `lib/demo-data.ts`, MSW, or mock-preview API routes ported
- No systemd, nginx, port 3002, or auth model changes
- No `DevModeSwitcher`, `TransitTimeline`, `LunarNodeWidget`, `YookassaPaywall`, or mock-preview page-level access setters
- Root layout/auth provider behavior unchanged
- `components/profile/access-card.tsx`, `referral-card.tsx`, `horary-card.tsx`, `avatar.tsx`, `service-row.tsx` unchanged (already met visual requirements)

## UI Semantic/Test Contract

| Attribute | Present | Location |
|-----------|---------|----------|
| `data-testid="profile-screen"` | ✅ | Root div |
| `data-state="loading\|ready\|error"` | ✅ | Root div |
| `data-access-state="trial\|subscription\|expired\|none"` | ✅ | Root div |
| `data-testid="profile-header"` | ✅ | Header |
| `data-testid="profile-access-card"` | ✅ | Access card section |
| `data-testid="profile-referral-card"` | ✅ | Referral card section |
| `data-testid="profile-horary-card"` | ✅ | Horary card section |
| `data-testid="profile-checkin-statistics"` | ✅ | Checkin metrics section |
| `data-testid="profile-data-section"` | ✅ | Profile data section |
| `data-testid="profile-data-row-birth-date"` | ✅ | Birth date row |
| `data-testid="profile-data-row-birth-time"` | ✅ | Birth time row |
| `data-testid="profile-data-row-birth-place"` | ✅ | Birth place row |
| `data-testid="profile-data-row-current-city"` | ✅ | Current city row |
| `data-testid="profile-data-row-birthday-city"` | ✅ | Birthday city row |
| `data-testid="profile-service-section"` | ✅ | Service section |
| `data-testid="profile-edit-sheet"` | ✅ | Edit sheet dialog |
| `role="dialog"` on edit sheet | ✅ | Edit sheet |
| `disabled` on rows before hydration | ✅ | Profile rows |

## Profile Meta Fix

- Default `rewardDays` changed from 7 → 14 in `profile/page.tsx`
- `lib/api/profile-meta.ts` now reads `daysPerInvite` from `/api/referral` response and maps it into `rewardDays`
- `bonusDays` computed as `count * rewardDays` (was hardcoded `count * 14`)

## Gates Results

### `git diff --check main..HEAD`
```
Exit code: 0
```

### `git diff --check`
```
Exit code: 0
```

### `pnpm exec tsc --noEmit --pretty false`
```
Exit code: 0
```

### `npx vitest run __tests__/components/ProfileScreen.test.tsx __tests__/hooks/useProfile.test.ts __tests__/api/profile-meta.test.ts __tests__/api/access.test.ts __tests__/contracts/profile.test.ts __tests__/contracts/access.test.ts __tests__/lib/profile.test.ts __tests__/lib/access.test.ts`
```
Test Files  8 passed (8)
     Tests  86 passed (86)
```

### `npx vitest run`
```
Test Files  84 passed (84)
     Tests  867 passed (867)
```

### `E2E_BASE_URL=http://localhost:3000 pnpm exec playwright test e2e/mock-visual --project=mobile`
```
12 passed (30.8s)
```

## Non-Ported Mock Preview Pieces

The following mock-preview pieces were explicitly NOT ported in Wave 03:

- `DevModeSwitcher` — not ported
- `TransitTimeline` — not ported (requires real transit data contract)
- `LunarNodeWidget` — not ported (requires real lunar node data contract)
- `YookassaPaywall` — not ported (payment/billing out of scope)
- Mock-preview page-level `onChangeState` access switching — not ported
- `lib/lunar-nodes.ts` client calculations — not ported
- `NATAL_LONGITUDES`, `MEAN_MOTION`, `J2000_LONGITUDE` static astrology — not ported
- Root layout/theme/`ThemeToggle` changes — not ported

## Known Gaps and Risks

- Transit timeline and lunar node widgets from mock-preview are not present in Wave 03. They require real backend transit/lunar-node data contracts. This gap is acceptable per TZ section 4 and 6.
- Payment/subscription management remains disabled (same as before Wave 03).
- Canonical `3002`, systemd, nginx, and bot config were not changed.

## Runtime Mock / MSW Statement

**No runtime mocks, MSW, mock-preview API routes, or demo data were ported to the product path.**
All profile data comes through real API endpoints. Mock fixtures live only in `e2e/mock-visual/` (test-only Playwright route interception).
No imports from `lib/mocks/*` or `lib/demo-data.ts` in product code.
