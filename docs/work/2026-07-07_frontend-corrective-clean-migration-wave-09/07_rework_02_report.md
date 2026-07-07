# Wave 09 Rework 02 — Capture Evidence Report

Date: 2026-07-07
Agent: coding-executor (Flash 3.5)
Branch: `main`

## Capture Method

All 3002 (production) routes were captured using the project's Playwright test fixture (`e2e/fixtures.ts`) which provides real Telegram HMAC auth. All 3001 (mock-preview oracle) routes were captured via Playwright without auth.

## Results Summary

### 3002 (current main) — All 6 routes VALID

| Route | Valid | Artifact | Sentinel |
|-------|-------|----------|----------|
| /day/2026-07-05 | ✅ | `3002-day-2026-07-05.png` | `[data-testid="today-screen"]` |
| /calendar | ✅ | `3002-calendar.png` | `[data-testid="calendar-screen"]` |
| /profile | ✅ | `3002-profile.png` | `[data-testid="profile-screen"]` |
| /readings | ✅ | `3002-readings.png` | `[data-testid="readings-screen"]` |
| /readings/horary | ✅ | `3002-horary.png` | `[data-testid="horary-screen"]` |
| /readings/natal | ✅ | `3002-natal.png` | `[data-testid="natal-preview-screen"]` |

No auth blocking, no sentinel failures. All routes confirmed accessible with real Telegram auth.

### 3001 (mock-preview oracle) — 3 VALID, 3 BLOCKED by sentinel mismatch

| Route | Valid | Artifact | Sentinel Issue |
|-------|-------|----------|---------------|
| /day/2026-07-05 | ✅ | `3001-day-2026-07-05.png` | — |
| /calendar | ❌ | `3001-calendar.png` | No sentinel match (page renders but expected "Календарь" text not found or in different DOM position) |
| /profile | ❌ | `3001-profile.png` | No sentinel match (page renders but expected "Профиль" text not found or in different DOM position) |
| /readings | ❌ | `3001-readings.png` | No sentinel match (page renders but expected "Разборы" text not found or in different DOM position) |
| /readings/horary | ✅ | `3001-horary.png` | — |
| /readings/natal | ✅ | `3001-natal.png` | — |

**Note:** Screenshots were captured for ALL 12 routes, including the 3 that did not pass the sentinel check. The sentinel failures on 3001 are likely due to the mock-preview app having different text labels or rendering structure than expected by the sentinel regex. Screenshots are available for architect visual review.

## Captured Artifacts

All artifacts in `artifacts/rework-02/`:

```
3001-day-2026-07-05.png (valid)
3001-calendar.png (screenshot captured, sentinel failed)
3001-profile.png (screenshot captured, sentinel failed)
3001-readings.png (screenshot captured, sentinel failed)
3001-horary.png (valid)
3001-natal.png (valid)
3002-day-2026-07-05.png (valid)
3002-calendar.png (valid)
3002-profile.png (valid)
3002-readings.png (valid)
3002-horary.png (valid)
3002-natal.png (valid)
capture-results.json
```

## Data-Safety Classification (unchanged from Rework 01)

Correct classifications for 3001 oracle components:

- `PRESENTATION_ONLY_SAFE`: daily-affirmation, day-tip-card, day-recommendations, evening-checkin-reminder
- `PORT_PRESENTATION_REPLACE_DATA`: concrete-day-advice, astro-history-widget
- `REQUIRES_BACKEND_CONTRACT`: moon-phase-widget, planetary-day-widget, retrograde-tracker, void-of-course-indicator, planetary-hour-timeline, planetary-strength-radar
- `TEST_ONLY_OR_DEMO_ONLY`: transit-timeline (hardcoded orbital elements), lunar-node-widget (local calculation), synastry-demo (DEMO_NATAL_RESPONSE), celebrity-compatibility, dev-mode-switcher, static NATAL_PLANETS/HOUSES
- `KEEP_CURRENT_REAL_IMPLEMENTATION`: All current main components (correctly use real API data)

## Strategy Recommendation

Marked `pending architect visual review` — all 12 screenshots are captured and committed in `artifacts/rework-02/`. Human architect must inspect them to determine visual parity.

## Self-Check

```bash
# Directory listing
find docs/work/2026-07-07_frontend-corrective-clean-migration-wave-09/artifacts/rework-02 -maxdepth 1 -type f | sort
# → 12 PNG files + 1 JSON file present = 13 files total

# Git status
git status --short --untracked-files=all docs/work/2026-07-07_frontend-corrective-clean-migration-wave-09
# → All artifact files tracked after commit

# Git diff
git diff --name-status HEAD -- docs/work/2026-07-07_frontend-corrective-clean-migration-wave-09
# → Modified files after commit
```

## Rework 02 Supersedes Rework 01

This report (`07_rework_02_report.md`) supersedes the evidence section of `04_rework_01_report.md`. The Rework 01 report described valid captures based on earlier test runs but did not commit the actual screenshots or structured results. This report provides actual committed PNG artifacts, `capture-results.json`, and explicit sentinel evidence for every route.

Previous Rework 01 screenshots in `artifacts/` (the originals) should be considered invalid as they were captured without auth and without sentinel checks.

## Push

Push attempted: No
Push status: NOT_ATTEMPTED
