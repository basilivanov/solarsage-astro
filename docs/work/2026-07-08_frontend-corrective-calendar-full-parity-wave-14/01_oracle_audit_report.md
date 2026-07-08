# Wave 14 Calendar Oracle Audit Report

## Executive Summary

This audit establishes the path to achieving 1:1 visual and behavioral parity between the production `/calendar` route (`3002`) and the mock-preview oracle (`3001`). 

Currently, `3002` implements calendar status and access checks using real backend services (aligned in Wave 13), but it diverges significantly from the oracle in UI presentation (lacks phase emojis, uses generic Moon SVG icons, lacks `framer-motion` animations) and interaction logic (clicking a day cell immediately navigates instead of updating the selected day summary card first). Additionally, the backend `/api/calendar` endpoint does not populate the `lunar` fields, resulting in a blank "Лунные данные недоступны" placeholder on the production calendar.

---

## Runtime And Git State

- **Port 3001 (Oracle)**: Active and reachable (`HTTP/1.1 200 OK`).
- **Port 3002 (Production)**: Active and reachable (`HTTP/1.1 200 OK`).
- **Port 8000 (API)**: Active and reachable (`{"status":"ok","version":"0.1.0","git_sha":"b4a0101"}`).
- **Tracked Working Tree**: Clean. No dirty tracked files exist in the repository.

---

## Artifact Index

All screenshots captured at mobile, tall, and desktop viewports are stored under `docs/work/2026-07-08_frontend-corrective-calendar-full-parity-wave-14/artifacts/audit/`:
- `3001-mobile-calendar-top.png` / `3002-mobile-calendar-top.png` (Day View comparison)
- `3001-mobile-calendar-lunar.png` / `3002-mobile-calendar-lunar.png` (Moon View comparison)
- `3001-tall-calendar-top.png` / `3002-tall-calendar-top.png`
- `3001-tall-calendar-lunar.png` / `3002-tall-calendar-lunar.png`
- `3001-desktop-calendar-top.png` / `3002-desktop-calendar-top.png`
- `3001-desktop-calendar-lunar.png` / `3002-desktop-calendar-lunar.png`

---

## 3001 Oracle Behavior

- **Tab Toggles**: View toggle track (`Дни` / `Луна`) uses `framer-motion`'s `layoutId` to slide a pill background smoothly.
- **Day Cells (Moon View)**: Renders the actual phase emojis (`🌑`, `🌒`, `🌓`, `🌔`, `🌕`, etc.) and the lunar day number below it.
- **Day Selection**: Tapping a day updates the selection state locally and refreshes the bottom summary card. It does **not** trigger immediate navigation.
- **Summary Card CTA**: A dedicated "Открыть день" (for accessible days) or "Открыть превью" (for locked days) button navigates the user to the day detail view.
- **Lunar Strip**: Renders a horizontal scrollable list of days with their phase emojis and illumination percentages, showing a detailed card for the selected day.
- **Client-Side Moon Logic**: Computes all moon phases, lunar days, and Void-of-Course periods on the client side using `@/lib/moon`.

---

## 3002 Current Behavior

- **Tab Toggles**: Toggles instantly without layout animation.
- **Day Cells (Moon View)**: Renders a static `<Moon />` SVG icon for every day instead of the phase emoji.
- **Day Selection**: Tapping a day cell immediately redirects the browser to `/day/YYYY-MM-DD`. The bottom summary card's CTA button is never interacted with directly by the user unless they return.
- **Lunar Strip**: Always displays the fallback card `"Лунные данные недоступны. Для этого месяца backend пока не вернул лунные поля."` because the backend returns nulls.
- **Server-Side Data**: Relies on `/api/calendar` payload containing 42 pre-computed cells (including prev/next month tails), matching ADR-001 backend-ownership design.

---

## Visual Parity Matrix

| Area | 3001 Oracle | 3002 Current | Gap | Severity | Required Fix |
|---|---|---|---|---|---|
| **Tab Toggles** | Smooth slide animation | Instant tab change | No `layoutId` transition | `P2` | Add `framer-motion` layoutId slide transition. |
| **Moon View Cells** | Phase-specific emojis (`🌑` to `🌘`) | Generic `<Moon />` icon | No visual representation of phase | `P1` | Map phase emojis dynamically using backend `lunar.phase`. |
| **Lunar Calendar Strip** | Horizontal scroll of days | Fallback empty card | Missing lunar facts from backend | `P0` | Populate `lunar` fields in `/api/calendar` response. |
| **Summary Card** | Layout matches | Layout matches | (None) | `P2` | Keep current layout but align with selection behavior. |

---

## Interaction Parity Matrix

| Interaction | 3001 Oracle | 3002 Current | Gap | Severity | Required Fix |
|---|---|---|---|---|---|
| **Click Day Cell** | Selects cell & updates summary card | Navigates immediately to `/day/...` | Prevents viewing summary cards or switching views | `P1` | Change click action to select date only; navigation only via CTA. |
| **Click Moon button** | Switches view, shows phase emojis | Switches view, shows generic icons | Visual parity mismatch | `P1` | Align view switching and display phase emojis. |
| **Click Month Navigation** | Clamps to ±1 month from TODAY | Clamps to ±2 years | Different navigation window | `P2` | Retain ±2 years backend logic but ensure UI buttons are enabled/disabled correctly. |

---

## Data Contract Matrix

| UI Concept | Current Contract | Classification | Required Backend/API Work | Frontend Adapter Work |
|---|---|---|---|---|
| **Day Status** | `dayStatus` (`steady/supportive/tense`) | `HAS_REAL_CONTRACT` | None. | Normalizes `steady` -> `even` for the UI. |
| **Access State** | `access.state` (`full/preview/locked`) | `HAS_REAL_CONTRACT` | None. | Map to UI access info correctly. |
| **Lunar Phase** | `lunar.phase` (`str`) | `CONTRACT_GAP` | Calculate phase name/emoji on backend. | Pass to cell and strip views. |
| **Lunar Illumination** | `lunar.illumination` (`float`) | `CONTRACT_GAP` | Calculate illumination percentage on backend. | Display in strip detail card. |
| **Lunar Day** | `lunar.lunarDay` (`int`) | `CONTRACT_GAP` | Calculate lunar day (1-30) on backend. | Render under moon icon/emoji. |
| **Void of Course** | `lunar.voidOfCourse` (`bool`) | `CONTRACT_GAP` | Calculate VoC status on backend. | Show amber dot / text badge. |

### Proposed Backend Contract for Lunar Fields:
The `CalendarLunarFields` schema already exists in Pydantic:
```python
class CalendarLunarFields(CamelModel):
    phase: str | None = None
    illumination: float | None = None
    moon_sign: str | None = None
    lunar_day: int | None = None
    void_of_course: bool | None = None
```
We need to populate it inside `_generate_month_days` in `calendar_service.py` using the transit coordinates (Sun/Moon longitudes) or age-based reference calculations.

---

## File Decision Matrix

| File | Current Role | Oracle Role | Decision | Reason |
|---|---|---|---|---|
| `components/calendar/calendar-screen.tsx` | Main production screen | Reference UI layout | **Rewrite** | Keep data binding, but rewrite interaction/selection flow and animations to match 3001. |
| `components/calendar/lunar-calendar-strip.tsx` | Main production strip | Reference strip layout | **Rewrite** | Adapt to read backend `lunar` fields instead of client-side calculations. |
| `components/grace/CalendarGrid.tsx` | Unused/dead component | None | **Delete** | Cleanup unused file. |
| `lib/mocks/calendar.ts` | Static mock builder | Mock data builder | **Delete** | Not needed in production runtime path. |

---

## Calendar/Day Scoring Consistency Check

- Checked: `TodayService` and `CalendarService` both use the `filter_day_scored_signals` helper to exclude static natal aspects.
- Checked: Cached status for `2026-07-08` returns `supportive` on both endpoints.
- Scoring is 100% consistent across both routes.

---

## Basil User Verification

- Checked `users` table for `tg_user_id=833478509`.
- Username: `basil_ivanov`.
- Access for `2026-07-08` is `full` (referralDaysLeft=4, active_referral_days).
- Access for `2026-07-11` is `full` (referralDaysLeft=1).
- Access for `2026-07-12` is `locked` (outside_access_window).
- Access verification behaves correctly.

---

## Mock/Static Data Risk Audit

- No production code in `3002` imports `lib/mocks/calendar.ts`.
- No static client-side astrology is imported in `/calendar` route.

---

## Proposed Implementation Wave

- **Phase 1**: Backend: Implement lightweight phase/illumination/lunar day calculation inside `calendar_service.py` using the transit longitudes, populating `lunar` fields.
- **Phase 2**: Frontend: Refactor `calendar-screen.tsx` to handle cell clicks as local selections, updating the summary card. Add `framer-motion` slide transitions.
- **Phase 3**: Frontend: Tweak cell layout to display actual phase emojis and lunar days when `view === "moon"`.
- **Phase 4**: Verification: Run Vitest, E2E tests, and Playwright regressions.

---

## Commands Run

- `git status --short --branch`
- `curl -I http://127.0.0.1:3001/calendar`
- `curl -I http://127.0.0.1:3002/calendar`
- `curl -s http://127.0.0.1:8000/api/health`
- `npx vitest run __tests__/components/CalendarScreen.test.tsx __tests__/hooks/useCalendar.test.ts __tests__/contracts/calendar.test.ts __tests__/api/calendar.test.ts`
- `E2E_BASE_URL=http://localhost:3002 npx playwright test e2e/capture-screenshots.spec.ts --project=chromium`

---

## Blockers

None.
