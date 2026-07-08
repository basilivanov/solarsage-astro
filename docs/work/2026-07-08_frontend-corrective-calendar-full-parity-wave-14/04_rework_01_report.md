# Wave 14 Calendar Oracle Audit Rework 01 Report

Date: 2026-07-08
Mode: report-only rework, no product source changes
Target route: `/calendar`
Oracle: port 3001 mock-preview
Current main: port 3002 production frontend backed by `/api/calendar`

## Executive Summary

3001 remains the visual and interaction oracle for the next parity wave. 3002 already uses the real calendar API and the same cache-backed scoring path as `/day`, but it is not visually or behaviorally 1:1 with the oracle.

The highest-priority gaps are:

- P0: lunar facts are not populated by the backend, so 3002 cannot render the oracle's phase strip, per-day phase glyphs, illumination, moon sign, lunar day, or void-of-course semantics honestly.
- P1: 3002 renders the month title in English (`July 2026`) while 3001 renders Russian (`Июль 2026`), visible in every top/lunar artifact pair.
- P1: day tapping in 3002 immediately navigates to `/day/YYYY-MM-DD`; oracle behavior is local selection first, then navigation through the footer CTA.
- P1: the selected-day footer is visible in `3001-tall-calendar-top.png` but absent/not visible in the matching `3002-tall-calendar-top.png`; desktop 3002 shows a footer lower down, but its CTA/status content still differs from the oracle.
- P1: 3002 lunar mode renders generic moon icons and dashes; 3001 renders phase-specific glyphs, lunar day numbers, selected lunar detail, and a current-day marker.

This rework addresses every finding in `02_arch_review.md`: it expands the route inventory, uses artifact filenames as evidence, answers all 13 TZ questions explicitly, replaces unsafe delete recommendations with keep/rewrite decisions, and specifies a backend-owned reusable lunar contract.

## Runtime And Git State

Inherited evidence from `01_oracle_audit_report.md`:

- 3001 oracle was reachable: `curl -I http://127.0.0.1:3001/calendar` returned `HTTP/1.1 200 OK`.
- 3002 current main was reachable: `curl -I http://127.0.0.1:3002/calendar` returned `HTTP/1.1 200 OK`.
- API was reachable: `curl -s http://127.0.0.1:8000/api/health` returned `{"status":"ok","version":"0.1.0","git_sha":"b4a0101"}`.
- Screenshot capture used a temporary Playwright screenshot spec; `01_oracle_audit_report.md` records the command `E2E_BASE_URL=http://localhost:3002 npx playwright test e2e/capture-screenshots.spec.ts --project=chromium`.
- Verification summary from the existing report: 12 screenshots captured; targeted Vitest command passed 41 tests.

This rework is documentation-only. No new screenshots were captured for this report. Source-code observations below come from read-only inspection.

Fresh verification run during this rework:

- `git status --short --branch`: branch `main...origin/main [ahead 17]`; new untracked report `docs/work/2026-07-08_frontend-corrective-calendar-full-parity-wave-14/04_rework_01_report.md`; unrelated untracked `.grace/`, `grace.db`, `skills/`, and `docs/superpowers/plans/2026-07-05-fix-day-route-auth-build.md` remain unstaged.
- `npx vitest run __tests__/components/CalendarScreen.test.tsx __tests__/hooks/useCalendar.test.ts __tests__/contracts/calendar.test.ts __tests__/api/calendar.test.ts`: 4 test files passed, 41 tests passed.

## Artifact Index

All visual evidence is under `docs/work/2026-07-08_frontend-corrective-calendar-full-parity-wave-14/artifacts/audit/`.

| Artifact | Viewport / State | Key Evidence |
|---|---|---|
| `3001-mobile-calendar-top.png` | 390x844 day/top | Russian title, oracle lunar card, compact current-month grid, bottom nav visible, footer cropped by viewport. |
| `3002-mobile-calendar-top.png` | 390x844 day/top | English title, lunar-unavailable card, faded extended 3-month grid, no footer visible. |
| `3001-tall-calendar-top.png` | 430x932 day/top | Russian title, rich lunar card, selected day footer visible with `Открыть день`. |
| `3002-tall-calendar-top.png` | 430x932 day/top | English title, lunar-unavailable card, selected footer absent/not visible before bottom nav. |
| `3001-desktop-calendar-top.png` | 900x1200 day/top | Centered mobile shell, Russian title, oracle footer and CTA visible. |
| `3002-desktop-calendar-top.png` | 900x1200 day/top | Centered shell, English title, 3-month grid extends lower, footer appears but content/button differs. |
| `3001-mobile-calendar-lunar.png` | 390x844 lunar mode | Phase glyphs, lunar day numbers, selected lunar detail, footer CTA. |
| `3002-mobile-calendar-lunar.png` | 390x844 lunar mode | Generic moon icons and dashes, no lunar footer visible. |
| `3001-tall-calendar-lunar.png` | 430x932 lunar mode | Phase glyphs, lunar days, current-day orange marker, footer detail. |
| `3002-tall-calendar-lunar.png` | 430x932 lunar mode | Generic moon icons/dashes, footer absent/not visible before nav. |
| `3001-desktop-calendar-lunar.png` | 900x1200 lunar mode | Oracle lunar mode and footer detail visible. |
| `3002-desktop-calendar-lunar.png` | 900x1200 lunar mode | Generic lunar mode, footer says lunar data unavailable. |

## 3001 Oracle Behavior

- Header: centered mobile shell, circular previous/next controls, uppercase `КАЛЕНДАРЬ`, localized month title `Июль 2026`.
- Segmented control: `Дни` and `Луна`; active segment appears as a white pill over the muted track.
- Day view: shows a rich `ЛУННЫЙ КАЛЕНДАРЬ` card above the grid with phase tags, month length (`31 дней`), horizontal phase strip, percentages, and legend.
- Grid: Monday-first weekday labels; unavailable/out-of-month days are very faint; accessible days show mood/lunar indicators; selected day is a filled purple circle.
- Lunar mode: grid cells show phase-specific glyphs plus lunar day numbers. The selected lunar day has a ring, and the current day has an orange marker.
- Selection: tapping a date updates local selected state and footer content; navigation is deferred to the footer CTA.
- Footer: selected-day summary is a fixed bottom block above tab navigation with `Сегодня` or selected-day label, formatted Russian date, day status or lunar details, and `Открыть день`.
- Bottom nav: visible and stable, with Calendar active.

## 3002 Current Behavior

- Header: mostly matching shell and nav controls, but payload title is English (`July 2026`) because backend returns `strftime("%B %Y")` and the frontend displays `payload.title` first.
- Segmented control: shape is close to oracle; transition is instant rather than oracle-like animated.
- Day view: `LunarCalendarStrip` falls back to `Лунные данные недоступны` because all backend lunar fields are null.
- Grid: backend returns previous/current/next month days, so 3002 renders a much taller 3-month stream rather than the oracle's compact current-month-centered grid presentation.
- Lunar mode: every cell uses a generic Lucide `Moon` icon and `—` when lunar data is missing.
- Selection: `selectDay()` sets selected state and immediately calls `onOpenDay` for any openable day, causing direct navigation to `/day/YYYY-MM-DD`.
- Footer: component has `data-testid="calendar-selected-summary"`, but the captured tall/top current view does not show it where the oracle does; desktop shows a footer lower down with `Открыть превью` and unavailable lunar/status states.
- Data state: `data-load-state="loading|error|ready"` exists, plus `calendar-loading`, `calendar-unavailable`, `calendar-grid`, and per-day `data-testid` values.

## Visual Parity Matrix

| Area | Evidence | 3001 Oracle | 3002 Current | Gap | Severity | Required Fix |
|---|---|---|---|---|---|---|
| Mobile shell width | `3001-desktop-calendar-top.png`, `3002-desktop-calendar-top.png` | Centered mobile app column on desktop. | Centered mobile app column. | Mostly aligned. | P2 | Preserve shell constraints while fixing inner route layout. |
| Header controls | `3001-mobile-calendar-top.png`, `3002-mobile-calendar-top.png`, `3001-tall-calendar-lunar.png`, `3002-tall-calendar-lunar.png` | Circular previous/next buttons, same placement. | Similar circular controls. | Minor visual differences only. | P2 | Keep current controls; verify disabled states after month-range changes. |
| Month title localization | `3001-mobile-calendar-top.png`, `3002-mobile-calendar-top.png`, `3001-tall-calendar-top.png`, `3002-tall-calendar-top.png` | `Июль 2026`. | `July 2026`. | English backend title leaks into Russian UI. | P1 | Localize title in backend or frontend adapter from `month`; do not display English `payload.title` in production Russian UI. |
| Header typography/title spacing | `3001-desktop-calendar-top.png`, `3002-desktop-calendar-top.png` | Serif title and uppercase label balanced. | Similar, but English title length/shape changes rhythm. | Mostly consequence of localization. | P2 | Re-check once Russian title is restored. |
| Segmented control | `3001-mobile-calendar-top.png`, `3002-mobile-calendar-top.png`, `3001-mobile-calendar-lunar.png`, `3002-mobile-calendar-lunar.png` | Active white pill on muted track; oracle has smooth selected segment treatment. | Active pill visually close, instant transition. | Motion/interaction polish gap. | P2 | Port oracle segment transition if dependency/pattern is acceptable; otherwise match final visual states and ARIA. |
| Weekday labels | `3001-tall-calendar-top.png`, `3002-tall-calendar-top.png` | Monday-first Russian uppercase short labels, weekend faded. | Same labels and similar weekend fade. | No major gap. | P2 | Preserve `WEEKDAYS_SHORT`; cover with DOM tests. |
| Day-view lunar card | `3001-mobile-calendar-top.png`, `3002-mobile-calendar-top.png`, `3001-desktop-calendar-top.png`, `3002-desktop-calendar-top.png` | Rich card with phase tags, strip, percentages, legend, month-day count. | Fallback card: `Лунные данные недоступны`. | Missing backend lunar facts and oracle presentation. | P0 | Populate backend lunar contract, then adapt `LunarCalendarStrip` to render oracle card from real data. |
| Day-view grid height/density | `3001-tall-calendar-top.png`, `3002-tall-calendar-top.png`, `3001-desktop-calendar-top.png`, `3002-desktop-calendar-top.png` | Compact month presentation; footer visible in tall view. | 3-month day stream consumes vertical space; footer not visible in tall/top. | Route does not match oracle viewport composition. | P1 | Keep backend 3-month payload if needed, but render the oracle current-month visual grid/window and avoid pushing footer below nav. |
| Current month days | `3001-mobile-calendar-top.png`, `3002-mobile-calendar-top.png` | Current month has readable numbers and status/lunar marks. | Current month numbers exist, many cells have lock markers and missing/faded markers. | Styling and access-state treatment differ. | P1 | Match oracle opacity, markers, and selected-state visual rules while preserving real access. |
| Out-of-month days | `3001-tall-calendar-top.png`, `3002-tall-calendar-top.png` | Previous/next month tail days are very faint but grid remains compact. | Previous/current/next month full runs are all rendered, with many disabled faint rows. | 3002 renders backend payload literally instead of oracle visual window. | P1 | Adapter should distinguish payload scope from display scope; render only oracle-equivalent cells for the selected month view. |
| Locked/inaccessible days | `3001-mobile-calendar-top.png`, `3002-mobile-calendar-top.png`, `3001-desktop-calendar-top.png`, `3002-desktop-calendar-top.png` | Locks appear on inaccessible days with faint treatment; selected accessible day still opens full day. | Many current-month days show locks; selected footer may show `Открыть превью`. | Access may be real but visual density/CTA differs. | P1 | Preserve backend access states; align lock marker size, opacity, and selected-day CTA label semantics with oracle and real access. |
| Today state | `3001-tall-calendar-top.png`, `3002-tall-calendar-top.png` | Day 8 selected purple, footer says `Сегодня`. | Day 8 selected purple; footer not visible in tall/top. | Selected cell roughly aligned, footer visibility not aligned. | P1 | Keep selected day visual, fix layout/selection flow so footer is visible as in oracle. |
| Selected-day footer in day view | `3001-tall-calendar-top.png`, `3002-tall-calendar-top.png`, `3001-desktop-calendar-top.png`, `3002-desktop-calendar-top.png` | Tall/top shows footer with `Сегодня`, `8 июля 2026`, status, `Открыть день`. | Tall/top does not show footer; desktop footer appears lower and can show `Открыть превью`. | Footer visibility/content parity gap. | P1 | Make footer consistently visible above bottom nav after top calendar content, and match CTA/status by selected access state. |
| Bottom navigation | `3001-mobile-calendar-top.png`, `3002-mobile-calendar-top.png`, `3001-tall-calendar-top.png`, `3002-tall-calendar-top.png`, `3001-desktop-calendar-lunar.png`, `3002-desktop-calendar-lunar.png` | Calendar tab active, bottom nav fixed. | Calendar tab active, bottom nav fixed. | Mostly aligned. | P2 | Preserve active state and accessible labels; ensure footer does not overlap nav. |
| Lunar mode day cells | `3001-mobile-calendar-lunar.png`, `3002-mobile-calendar-lunar.png`, `3001-tall-calendar-lunar.png`, `3002-tall-calendar-lunar.png` | Phase glyphs plus lunar day numbers. | Generic moon icon plus dash. | Missing visible lunar facts. | P0 | Backend-owned lunar fields and frontend mapping to oracle glyph/label presentation. |
| Lunar selected state | `3001-tall-calendar-lunar.png`, `3002-tall-calendar-lunar.png` | Selected lunar day has ring around phase glyph and number. | Selected ring around generic icon/dash. | Data and visual mismatch. | P1 | Once data exists, match ring, sizing, and glyph treatment. |
| Lunar current-day marker | `3001-mobile-calendar-lunar.png`, `3002-mobile-calendar-lunar.png` | Orange dot marker on current day in lunar grid. | No equivalent visible marker. | Missing current-day marker in lunar mode. | P1 | Add marker driven by `isToday`, not fake lunar data. |
| Lunar footer detail | `3001-desktop-calendar-lunar.png`, `3002-desktop-calendar-lunar.png` | `убыв. серп · 39% · 24 лунный день` style detail. | `Лунные данные недоступны`. | Missing backend lunar fields and presentation. | P0 | Render phase label, illumination, lunar day, moon sign/void state from backend contract. |
| Loading state | Source evidence: `components/calendar/calendar-screen.tsx` | Not captured in artifacts. | Has `calendar-loading` card with Russian text. | Visual parity unverified. | P2 | Add targeted screenshot/test for loading state before implementation signoff. |
| Error/unavailable state | Source evidence: `components/calendar/calendar-screen.tsx`; visual fallback in `3002-*-calendar-top.png` is lunar-only unavailable | Not captured as full route error. | Has `calendar-unavailable` route state and lunar fallback card. | Full route error parity unverified; lunar fallback is non-oracle once data exists. | P2 | Keep route error state for real failures; replace lunar fallback in normal ready state once contract is populated. |

## Interaction Parity Matrix

| Interaction | 3001 Oracle | 3002 Current | Gap | Severity | Required Fix |
|---|---|---|---|---|---|
| Initial load | Shows day mode with oracle lunar summary card and current selected day. | Shows day mode with lunar-unavailable card while payload loads/returns null lunar fields. | Initial ready surface differs. | P0 | Backend lunar population plus oracle card rendering. |
| Previous month tap | Moves calendar month within oracle navigation window; visual title remains localized. | Calls `go(-1)` and uses backend `allowedRange`; title comes from backend payload. | Range source differs; localized title can become English for every month. | P1 | Keep backend range; localize visible title from `month` or localized `titleLabel`. |
| Next month tap | Same as previous, oracle-localized and compact. | Same mechanism as previous. | Same gap. | P1 | Same fix as previous. |
| Normal available date tap | Selects day locally and updates footer summary; does not navigate immediately. | `selectDay()` sets selected and immediately calls `onOpenDay` when `canOpen(day)`, navigating to `/day/YYYY-MM-DD`. | User cannot inspect selected summary before navigation. | P1 | Split selection from opening; day tap selects only, footer CTA navigates. |
| Today tap | Selects today and footer says `Сегодня`. | If openable, navigates immediately; if not, selection remains. | Same immediate-navigation mismatch. | P1 | Same selection/CTA split. |
| Locked/inaccessible date tap | Oracle keeps user in calendar and presents preview/open affordance through footer if allowed by design. | `canOpen(day)` is true for non-disabled days, so locked/preview days can call `onOpenDay`; footer may show preview only if navigation does not happen first. | Locked/preview interaction is not reliably observable in calendar. | P1 | Define `full`, `preview`, `locked` tap policy: select all current-month days, CTA opens full/preview only when backend says it can. |
| Disabled/out-of-month day tap | Oracle treats outside-month tails as non-primary/faint; no unsafe navigation. | `disabled` true for non-current month, button disabled. | Likely aligned semantically, visual scope differs. | P2 | Preserve disabled behavior while changing rendered month window. |
| Sunday tap | Oracle treats Sunday like any other date with its own status/access. | Backend status uses same scoring helper as `/day`; visual behavior currently immediate-navigation if openable. | Scoring likely aligned, interaction not. | P1 | Add regression for a Sunday comparing `/calendar` status/access to `/day`, plus selection-only calendar tap. |
| Switch `Дни` to `Луна` | Switches to phase-glyph grid and footer lunar detail. | Switches to generic moon/dash grid and unavailable footer/detail. | Data and presentation mismatch. | P0 | Backend lunar contract plus oracle glyph/label mapping. |
| Switch `Луна` to `Дни` | Returns to day grid/card while preserving selected date. | Returns to day grid; selected date state exists unless navigation already occurred. | Immediate navigation can prevent mode comparison. | P1 | Local selection first; preserve selected date across mode switches. |
| Tap lunar strip item | Oracle strip/card supports selecting a lunar day in day view. | `LunarCalendarStrip` has item selection logic, but there are no items because backend lunar facts are null. | Interaction unreachable in production. | P0 | Populate lunar facts; test strip item selection updates selected detail without route navigation. |
| Footer CTA tap | Oracle `Открыть день` navigates to `/day/YYYY-MM-DD`; preview label may apply to locked/preview state. | CTA exists in component, but normal day tap navigates first; desktop current artifact shows `Открыть превью`. | CTA is not the primary open action. | P1 | Make CTA the only route-opening action and align label/icon/lock state with access. |
| Focus/keyboard | Oracle visual screenshots do not show focus rings. | 3002 has `focus-visible:ring` and real buttons. | Accessibility behavior not fully audited visually. | P2 | Preserve keyboard focus and ARIA; test by role/state rather than class names. |
| Expand/collapse | No expanded/collapsed calendar control visible in artifacts. | No explicit accordion/disclosure in current calendar. | No parity requirement beyond lunar strip item selection. | P2 | Do not invent accordion behavior; add only if oracle source proves it. |

## Data Contract Matrix

| UI Concept | Current JSON Path / Type | Current Contract Status | Classification | Required Backend/API Work | Frontend Adapter Work | Cache/Versioning | Tests |
|---|---|---|---|---|---|---|---|
| Payload version | `meta.schemaVersion: "calendar/v1"`, `meta.contractVersion: number`, `meta.generatedAt: string` | Present. | HAS_REAL_CONTRACT | Increment contract version when lunar shape expands. | Validate new version in Zod/types. | Bump `contractVersion` and document compatibility. | Contract tests for v1/v2 acceptance or migration. |
| Requested month | `month: "YYYY-MM"` | Present. | HAS_REAL_CONTRACT | None. | Use as source for localized title if backend title remains display-unsafe. | None. | Unit test title derivation. |
| Month display title | `title: string` | Present but English from backend `strftime("%B %Y")`. | CONTRACT_GAP | Either return `titleLabel: string` localized for user locale or define `title` as non-authoritative and add locale metadata. | Prefer render from `month` using Russian month names until backend locale contract exists. | If backend-owned locale, include locale in cache key or response metadata. | API test for July 2026 Russian label or frontend adapter test from `month`. |
| Allowed range | `allowedRange.from/to: YYYY-MM-DD` | Present. | HAS_REAL_CONTRACT | None. | Keep button disabled logic from backend range. | None. | Existing API tests plus UI disabled-state tests. |
| Calendar cells | `days[]` includes previous/current/next months | Present. | HAS_REAL_CONTRACT | Keep as data payload if needed for range/access context. | Render oracle visual window instead of blindly rendering all 3 months. | None. | UI test that visible grid/summary matches oracle layout while preserving payload parsing. |
| Cell date | `days[i].date: YYYY-MM-DD` | Present. | HAS_REAL_CONTRACT | None. | Use for selection, CTA route, test IDs. | None. | Contract and route tests. |
| Day number | `days[i].dayNumber: int` | Present. | HAS_REAL_CONTRACT | None. | Render in day cells. | None. | Existing contract tests. |
| Current month flag | `days[i].isCurrentMonth: boolean` | Present. | HAS_REAL_CONTRACT | None. | Use to filter/render oracle visual scope and disable tails. | None. | UI test for out-of-month opacity/disabled. |
| Today flag | `days[i].isToday: boolean` | Present. | HAS_REAL_CONTRACT | None. | Use for marker/footer `Сегодня`; lunar orange marker. | None. | UI test for today marker in both modes. |
| Disabled state | `days[i].disabled: boolean` | Present. | HAS_REAL_CONTRACT | None. | Keep `disabled` attr for out-of-month/non-clickable cells. | None. | Accessibility test for disabled cells. |
| Status/scoring | `days[i].dayStatus: "supportive" / "steady" / "tense" / null` | Present; frontend maps `steady` to `even`. | HAS_REAL_CONTRACT | Continue using shared `filter_day_scored_signals` path. | Keep status normalization and labels. | Cache already tied to `TODAY_CONTENT_VERSION` and profile hash for semantic cache. | Calendar/day consistency tests including Sunday. |
| Access state | `days[i].access.state: "full" / "preview" / "locked"` plus reason/referral/subscription fields | Present. | HAS_REAL_CONTRACT | None. | Use to choose lock marker, opacity, CTA label, and route permission. | Access changes should invalidate/refetch normally through API. | Basil access regression with real tg_user_id and no default test user. |
| Lunar phase key | Proposed `days[i].lunar.phase: "new_moon" / "waxing_crescent" / ... / null` | Existing `phase: string|null` exists but is null and underspecified. | CONTRACT_GAP | Add shared backend lunar helper/service and populate stable enum key. Source of truth should be SolarSage/Sun-Moon longitudes or a sidecar-backed calculation, not frontend math. | Map enum to oracle glyph and localized label. | Include lunar algorithm/version in cache metadata or bump contract/content version. | API contract test for enum values; frontend mapping test. |
| Lunar phase index | Proposed `days[i].lunar.phaseIndex: 0..7 / null` | Absent. | CONTRACT_GAP | Compute from same backend lunar helper. | Use for ordering/phase strip and deterministic glyph mapping. | Version with lunar helper. | Schema test for nullable int range. |
| Lunar phase label | Proposed `days[i].lunar.phaseLabel: string|null` | Absent. | CONTRACT_GAP | Backend may return Russian label for current locale, or frontend may localize from phase key. Preferred: stable key + localized label in API if backend owns locale. | Display `убыв. серп` style label; avoid hardcoded astrology meaning not backed by key. | Locale impacts cache if backend-owned. | Snapshot/DOM test for label when fixture contains it. |
| Illumination | Proposed/current `days[i].lunar.illumination: number|null` | Existing field but null. | CONTRACT_GAP | Populate percentage as number, define precision (recommended 0-100 float, frontend rounds for display). | Render percentages in strip/card/footer. | Include lunar calc version. | API and adapter tests for rounding. |
| Moon sign key | Proposed/current `days[i].lunar.moonSign: string|null` | Existing field but null; key/label ambiguity. | CONTRACT_GAP | Return stable sign key/name from backend, derived from Moon longitude. | Use only for display/filter when present. | Lunar calc version. | API test for sign. |
| Moon sign label | Proposed `days[i].lunar.moonSignLabel: string|null` | Absent. | CONTRACT_GAP | Return localized label (`Рак`) or document frontend localization from key. | Display localized sign, not English-only backend key. | Locale cache note if backend-owned. | Contract/frontend localization tests. |
| Lunar day | Proposed/current `days[i].lunar.lunarDay: int|null` | Existing field but null. | CONTRACT_GAP | Compute backend lunar day 1-30 from accepted algorithm/source. | Render under glyph and in footer. | Lunar calc version. | API test for int range. |
| Void of course | Proposed/current `days[i].lunar.voidOfCourse: boolean|null` | Existing field but null. | CONTRACT_GAP | Compute backend-side or sidecar-side; define null as unknown/uncomputed, false as computed-not-void. | Render amber marker/text only when true; distinguish null from false in labels. | Lunar calc version and ephemeris/source version. | API tests for true/false/null semantics. |
| Phase glyph/emoji | No API path recommended. | Oracle currently has display glyphs. | FRONTEND_PRESENTATION_ONLY | Backend should not return emoji as source of truth. | Map `phase`/`phaseIndex` to glyph assets/classes. | None beyond contract version. | Visual fixture tests. |
| Loading state | DOM `data-load-state="loading"`, `calendar-loading` | Present in component, not screenshot-captured. | FRONTEND_PRESENTATION_ONLY | None. | Ensure `role="status"`/`aria-busy` if missing in implementation wave. | None. | Component test for loading semantics. |
| Error state | DOM `data-load-state="error"`, `calendar-unavailable` | Present in component, not screenshot-captured as full-route error. | FRONTEND_PRESENTATION_ONLY | Preserve API errors. | Add `role="alert"` if missing. | None. | Component test for error semantics. |
| Test selectors | `calendar-screen`, `calendar-grid`, `calendar-day-YYYY-MM-DD`, `calendar-selected-summary`, view buttons | Mostly present. | HAS_REAL_CONTRACT for UI test contract | None. | Add missing structural selectors for lunar card states and footer CTA if needed. | Selector changes require e2e updates. | Playwright structural tests by `data-testid` and roles. |
| Runtime mocks/static astrology | `lib/mocks/calendar.ts` not imported by production search; docs/tests reference it. | Not in product path based on read-only `rg`. | KEEP_TEST_ONLY | None. | Keep out of production imports; use only test harness/fixtures. | None. | Static import guard test can remain/add. |

Recommended lunar contract to evaluate and implement as backend-owned shared data:

```json
{
  "lunar": {
    "phase": "waning_crescent",
    "phaseIndex": 7,
    "phaseLabel": "убыв. серп",
    "illumination": 39.0,
    "moonSign": "Cancer",
    "moonSignLabel": "Рак",
    "lunarDay": 24,
    "voidOfCourse": false
  }
}
```

Architecture direction:

- Create a shared backend lunar helper/service, for example `LunarFactsService`, called by `CalendarService` and reusable by `/api/day`.
- Source of truth should be SolarSage/Sun-Moon longitudes or a sidecar extension. A simplified algorithm is acceptable only if explicitly documented, versioned, tested, and accepted as product behavior.
- Do not calculate astrological facts in frontend code. Frontend may localize labels and map stable backend values to glyphs/classes.
- Treat `null` as unknown/uncomputed, not as false. Especially for `voidOfCourse`, `false` means computed and not void; `null` means unavailable.
- Bump `contractVersion` or introduce `calendar/v2` when adding `phaseIndex`, `phaseLabel`, and `moonSignLabel`.
- Include lunar algorithm/source version in cache metadata or cache invalidation notes so stale lunar facts can be invalidated if ephemeris logic changes.

## File Decision Matrix

| File | Current Role | Oracle Role | Decision | Reason |
|---|---|---|---|---|
| `app/(grace)/calendar/page.tsx` | Client route wiring; passes `onOpenDay` router callback. | Oracle route opens day through footer CTA. | REWRITE_LIGHT | Keep route and auth/access path; change calendar screen contract so `onOpenDay` is called only from CTA. |
| `components/calendar/calendar-screen.tsx` | Main production calendar UI and interaction logic. | Equivalent source exists in mock-preview and is the main component tree to port from. | REWRITE_FOR_PARITY | Port oracle layout/interaction while preserving real API payload, access, selectors, and auth. |
| `components/calendar/lunar-calendar-strip.tsx` | Production lunar card/strip with fallback when fields null. | Oracle rich lunar card/strip. | REWRITE_FOR_PARITY | Rebuild around backend-owned lunar fields; no frontend astrology calculations. |
| `components/calendar/mood-icon.tsx` | Production status/mood glyph rendering. | Oracle has status/lunar visual marks. | KEEP_AND_ADAPT | Keep if it can render oracle-equivalent status marks; update styling only as needed. |
| `lib/api/calendar.ts` | Fetches `/api/calendar`, validates payload, normalizes status. | Oracle used mock/client data. | KEEP_AND_EXTEND | Add contract support for expanded lunar shape; keep real API and validation. |
| `lib/contracts/calendar.ts` | Zod read model for calendar payload. | Oracle has richer lunar data. | EXTEND | Add `phaseIndex`, `phaseLabel`, `moonSignLabel`, stricter phase enum if backend adopts it. |
| `packages/contracts/calendar.ts` | Deprecated re-export to package barrel. | None. | KEEP | Do not expand deprecated source; ensure barrel/source of truth stays aligned. |
| `lib/grace/hooks/useCalendar.ts` | Legacy/hook fetch path using package contract. | Not visible in active calendar screenshots. | KEEP_COMPAT | Do not delete; update only if active callers/tests require expanded contract. |
| `lib/calendar.ts` | Pure calendar utilities and status labels. | Oracle utility role. | KEEP_AND_ADAPT | Keep pure; do not add astrology calculations. Add only display-safe helpers if needed. |
| `lib/date.ts` | Russian date formatting constants/functions. | Oracle localized date/title display. | KEEP_AND_USE | Use for month title fallback/adapter to avoid English backend `title`. |
| `lib/mocks/calendar.ts` | Static mock builder; no production import found by read-only search. | Test/demo support only. | KEEP_TEST_ONLY | Do not delete. Keep out of production runtime and use only fixtures/test harness unless a separate cleanup plan proves safe removal. |
| `apps/api/app/schemas/calendar.py` | Backend Pydantic calendar schema; has nullable old lunar fields. | Needs richer oracle lunar facts. | EXTEND | Add recommended lunar fields and versioning. |
| `apps/api/app/api/calendar.py` | Authenticated `/api/calendar` route. | Oracle has no real API. | KEEP | Preserve Telegram/session auth and month validation; do not add bypasses. |
| `apps/api/app/services/calendar_service.py` | Generates 3-month payload with real access/status; currently leaves lunar default null. | Needs oracle facts from backend-owned service. | EXTEND_WITH_SHARED_SERVICE_CALL | Do not bury lunar algorithm here; call shared helper/service and populate schema. |
| `apps/api/app/services/today_service.py` or day service equivalent | `/day` status/content source. | Needs consistency if day UI uses lunar facts. | EXTEND_IF_NEEDED | Reuse same lunar helper/service for day payloads; avoid duplicate calculations. |
| `apps/api/tests/test_calendar_endpoints.py` | Backend calendar tests; currently asserts nullable lunar fields. | Needs real lunar contract coverage. | UPDATE_TESTS | Replace null-only assertion with fixture/algorithm-backed lunar fact assertions. |
| `__tests__/components/CalendarScreen.test.tsx` | Component tests for calendar UI. | Must lock oracle DOM contract. | UPDATE_TESTS | Add selection-only, footer CTA, locale, grid, loading/error, lunar mode cases. |
| `__tests__/hooks/useCalendar.test.ts` | Hook tests. | Contract consumer coverage. | UPDATE_AS_NEEDED | Cover expanded lunar payload parsing if hook remains active. |
| `__tests__/contracts/calendar.test.ts` | Zod/contract tests. | Must enforce new lunar shape. | UPDATE_TESTS | Add phase enum/index/label/sign/void nullability semantics. |
| `__tests__/api/calendar.test.ts` | Frontend API facade tests. | Real API contract consumer. | UPDATE_TESTS | Add expanded lunar payload and English title/localization behavior. |
| `e2e/calendar.spec.ts` | Real e2e route. | Must verify real auth/API path. | UPDATE_TESTS | Add no-route-interception checks for Basil/access and `/day` consistency. |
| `e2e/mock-visual/calendar.spec.ts` | Mock visual e2e. | Fixture oracle regression surface. | UPDATE_TESTS | Use stable fixtures for visual/structural parity only. |
| `e2e/mock-visual/fixtures/calendar-2026-07.ts` | Stable calendar fixture. | Should include oracle lunar facts. | UPDATE_FIXTURE | Add complete lunar fields matching recommended contract. |
| `components/grace/CalendarGrid.tsx` | Legacy/grace component; only local import found from `components/grace/CalendarGrid.tsx` to `CalendarMonth`. | No proven oracle role. | KEEP_LEGACY_NO_PARITY_ACTION | Do not delete in calendar parity wave; deletion is unrelated unless a separate cleanup proves no tests/docs/dependencies matter. |
| `components/grace/CalendarMonth.tsx` | Legacy/grace component used by `CalendarGrid`. | No proven oracle role. | KEEP_LEGACY_NO_PARITY_ACTION | Same as above. |

## Calendar/Day Scoring Consistency Check

Existing report evidence says calendar and `/day` both use `filter_day_scored_signals` and returned `supportive` for `2026-07-08`. Read-only inspection supports the shared scoring path:

- `apps/api/app/services/calendar_service.py` imports and uses `filter_day_scored_signals(signals)` before `ScoringService().score_day(...)`.
- Calendar cache reads `TodayPayloadCache` and `SemanticLayerCache` using `TODAY_CONTENT_VERSION` and profile hash.
- Frontend maps backend `steady` to UI `even` in `lib/api/calendar.ts` and `components/calendar/calendar-screen.tsx`.

Traceability gap remaining from the original report: it did not include exact endpoint bodies, SQL, or command output for the `supportive` result. The next implementation wave should preserve the architecture but add explicit regression evidence:

- authenticated `/api/calendar?month=2026-07` response for the target user/date;
- authenticated `/api/day/2026-07-08` response for the same user/date;
- at least one Sunday comparison, for example `2026-07-12`, covering both status and access.

## Basil User Verification

Existing report evidence:

- User checked: `tg_user_id=833478509`, username `basil_ivanov`.
- `2026-07-08`: `full`, `referralDaysLeft=4`, reason `active_referral_days`.
- `2026-07-11`: `full`, `referralDaysLeft=1`.
- `2026-07-12`: `locked`, reason `outside_access_window`.

Traceability gap remaining from the original report: exact SQL/endpoint commands and summarized raw outputs were not included. Treat the reported access behavior as inherited evidence, not freshly reverified in this rework. The next wave should repeat it through real Telegram HMAC/session auth, not a default test user and not route-intercepted fixtures.

## Mock/Static Data Risk Audit

Read-only import search found no production import of `lib/mocks/calendar.ts` or `mocks/calendar` in active product paths. It did find docs/coverage references and the file itself. Therefore:

- `lib/mocks/calendar.ts` decision is `KEEP_TEST_ONLY`.
- Do not import `lib/mocks/calendar.ts`, `lib/demo-data.ts`, MSW fixtures, or oracle-only client astrology into production runtime.
- Test-only Playwright route interception remains allowed under `e2e/mock-visual` or equivalent test harness.
- Oracle client-side moon logic must not be ported as frontend domain calculation; only the visual presentation and interactions should be ported.

## Answers To TZ Section 9 Questions

1. Which calendar component tree is the correct source to port from 3001?

   Port from `/opt/solarsage-astro-mock-preview/components/calendar/calendar-screen.tsx`, `/opt/solarsage-astro-mock-preview/components/calendar/lunar-calendar-strip.tsx`, `/opt/solarsage-astro-mock-preview/components/calendar/mood-icon.tsx`, `/opt/solarsage-astro-mock-preview/lib/calendar.ts`, and `/opt/solarsage-astro-mock-preview/app/(grace)/calendar/page.tsx`, but port only presentation and interactions. Do not port oracle mock data or frontend moon calculations.

2. Which current main calendar files should be rewritten, retained, or deleted?

   Rewrite for parity: `components/calendar/calendar-screen.tsx`, `components/calendar/lunar-calendar-strip.tsx`.
   Extend: `lib/contracts/calendar.ts`, `lib/api/calendar.ts`, `apps/api/app/schemas/calendar.py`, `apps/api/app/services/calendar_service.py` via a shared lunar helper/service.
   Retain: `app/(grace)/calendar/page.tsx`, `lib/calendar.ts`, `lib/date.ts`, `components/calendar/mood-icon.tsx` with targeted adaptations.
   Keep test-only: `lib/mocks/calendar.ts`.
   Do not delete for parity: `components/grace/CalendarGrid.tsx`, `components/grace/CalendarMonth.tsx`.

3. Does current main use the same real backend calendar contract as `/day` after Wave 13?

   It uses real `/api/calendar` data and the same scoring helper/cache lineage as `/day` for day status, but the calendar contract is not yet rich enough for lunar parity. Status/access are real; lunar facts are schema-present but unpopulated/underspecified.

4. Does calendar status/scoring match `/day` for the same user/date, especially Sunday?

   Inherited evidence says `2026-07-08` matched as `supportive`. Source inspection supports a shared scoring helper. Sunday-specific parity was not traceably proven in the existing report and must be added as a regression check, especially for `2026-07-12` or another visible Sunday.

5. Which fields in `CalendarDayReadModel` are enough for the oracle UI?

   Enough for base calendar: `date`, `dayNumber`, `isCurrentMonth`, `isToday`, `disabled`, `dayStatus`, `access`.
   Not enough for oracle lunar UI: current `lunar.phase`, `illumination`, `moonSign`, `lunarDay`, `voidOfCourse` are nullable and unpopulated, and the shape lacks `phaseIndex`, `phaseLabel`, and `moonSignLabel`.

6. Which oracle fields are absent from backend contracts?

   Absent or underspecified: stable lunar `phase` enum, `phaseIndex`, localized `phaseLabel`, populated `illumination`, stable/localized `moonSign` and `moonSignLabel`, populated `lunarDay`, computed `voidOfCourse`, localized month title/display label, and any explicit lunar algorithm/source version.

7. Are any current calendar texts hardcoded or templated in a way that should become backend-owned?

   Astrological facts and labels derived from facts should be backend-owned or backend-key-owned. UI chrome such as `Календарь`, `Дни`, `Луна`, `Сегодня`, `Открыть день`, and loading/error copy can remain frontend presentation. The month title is currently backend-templated in English and must be fixed by backend localization or frontend display derivation from `month`.

8. Does the calendar display month/week/day access correctly for Basil (`tg_user_id=833478509`, username `basil_ivanov`) without using a default test user?

   Existing report says yes for sampled dates: July 8 and July 11 full via referral days, July 12 locked outside access window. This rework did not freshly verify with commands. Next wave must repeat read-only/authenticated checks and include raw endpoint/SQL evidence.

9. Does any frontend code import `lib/mocks/calendar.ts` or static astrology outside tests?

   Read-only `rg` did not find production imports of `lib/mocks/calendar.ts` or `mocks/calendar`. Keep it test-only. No production `/calendar` path should import static astrology or oracle moon calculations.

10. What visual deltas remain between 3001 and 3002, ordered by severity?

   P0: missing lunar data/card/glyphs/details in 3002.
   P1: English month title in 3002 versus Russian oracle title.
   P1: selected-day footer not visible in `3002-tall-calendar-top.png` where it is visible in `3001-tall-calendar-top.png`.
   P1: 3002 renders a taller 3-month stream instead of oracle compact month composition.
   P1: locked/out-of-month opacity and markers differ.
   P1: lunar selected/current-day markers differ.
   P2: segment animation/focus polish/loading/error visual parity needs targeted capture.

11. What interaction deltas remain between 3001 and 3002, ordered by severity?

   P0: lunar strip item interaction is unreachable in 3002 because backend lunar facts are null.
   P1: day tap navigates immediately instead of selecting.
   P1: footer CTA is not the sole navigation action.
   P1: locked/preview date tap behavior is not oracle-equivalent.
   P1: mode switching cannot preserve an inspection flow if date taps navigate away.
   P2: month nav range is backend-driven and acceptable, but disabled states and localized titles need tests.
   P2: focus/keyboard behavior needs explicit accessibility verification.

12. What test coverage must be added before or during implementation?

   Add backend tests for populated lunar fields, phase enum/index range, illumination range, moon sign label/key, lunar day range, and void-of-course null/false/true semantics.
   Add calendar/day parity tests for same user/date including a Sunday.
   Add Basil access regression using real auth/session path or read-only DB plus authenticated endpoint evidence.
   Add contract tests for expanded `CalendarLunarFields`.
   Add component tests for localized title, selection-only day tap, footer CTA navigation, locked/preview CTA behavior, current-day marker, out-of-month disabled state, loading/error ARIA, and lunar mode rendering.
   Add Playwright mock-visual tests with stable fixtures for top, footer, lunar mode, locked, empty/error, and mobile/tall/desktop viewports.
   Keep real e2e without route interception for Telegram HMAC -> API -> UI.

13. What exact implementation sequence should the next wave follow?

   1. Add backend lunar helper/service with documented source of truth and tests.
   2. Expand backend and frontend calendar contracts with the recommended lunar shape and versioning.
   3. Populate `/api/calendar` lunar fields through the shared helper; reuse the same helper for `/api/day` if day UI needs lunar facts.
   4. Fix month title localization by backend localized label or frontend adapter from `month`.
   5. Refactor `CalendarScreen` so day taps select only and footer CTA opens `/day/YYYY-MM-DD`.
   6. Port oracle day-view layout, compact grid rendering, footer visibility, selected/today/locked/out-of-month styling.
   7. Port oracle lunar strip/grid/detail presentation from backend lunar facts.
   8. Update unit/contract/API tests.
   9. Update mock-visual fixtures and Playwright tests.
   10. Run targeted Vitest, backend pytest for calendar contracts/services, mock visual e2e, and real e2e without route interception.

## Verification Plan For Next Wave

Minimum commands for the implementation wave:

```bash
npx vitest run __tests__/components/CalendarScreen.test.tsx __tests__/hooks/useCalendar.test.ts __tests__/contracts/calendar.test.ts __tests__/api/calendar.test.ts
cd apps/api && source .venv/bin/activate && python -m pytest tests/test_calendar_endpoints.py -q
E2E_BASE_URL=http://localhost:3000 npx playwright test e2e/mock-visual/calendar.spec.ts
E2E_BASE_URL=http://localhost:3000 npx playwright test e2e/calendar.spec.ts
```

For this documentation rework, the required evidence incorporated from the existing report is: 12 screenshots captured and targeted Vitest 41 passed. Fresh verification during the rework also passed the same targeted Vitest set: 4 files, 41 tests.

## Rework Findings Closure

| Review Finding | Resolution In This Report |
|---|---|
| P0 report too shallow | Expanded route-level visual, interaction, data/contract, and file matrices; answered all 13 questions. |
| P1 missed visible differences | Added artifact-backed rows for localization, footer visibility, lunar card, lunar glyphs/dashes, grid density, opacity, lock markers, and selected states. |
| P1 lunar architecture underspecified | Specified backend-owned shared helper/service, exact JSON fields/types/nullability, source-of-truth options, cache/versioning, adapter work, and tests. |
| P1 unsafe deletion recommendations | Reclassified `lib/mocks/calendar.ts` as `KEEP_TEST_ONLY`; kept `components/grace/*` as `KEEP_LEGACY_NO_PARITY_ACTION`. |
| P2 verification evidence not traceable | Separated inherited evidence from fresh proof, listed exact remaining evidence gaps, and required endpoint/SQL summaries in next wave. |
