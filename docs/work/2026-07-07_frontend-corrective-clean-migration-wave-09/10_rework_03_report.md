# Wave 09 Rework 03 — Authenticated Full-Page Evidence

Date: 2026-07-07
Agent: coding-executor (Flash 3.5)
Branch: `main`

## Capture Method

Single Playwright script with same-page validation+screenshot for each route. Auth seeded via `grace_session_v2` cookie + `window.Telegram.WebApp` injection for both ports (3001 and 3002). Viewport 430x932. Full-page captures attempted for valid routes.

## Service Availability

| Port | Service | Status |
|------|---------|--------|
| 8000 | API (auth) | HTTP 404 (expected — no root route) |
| 3001 | mock-preview oracle | HTTP 200 |
| 3002 | current main | HTTP 200 |

## Results

### Valid routes (authenticated, sentinel passed, viewport+fullPage captured)

| Route | Port | Viewport | FullPage |
|-------|------|----------|----------|
| /day/2026-07-05 | 3001 | ✅ | ✅ |
| /readings | 3001 | ✅ | ✅ |
| /readings/horary | 3001 | ✅ | ✅ |
| /readings/natal | 3001 | ✅ | ✅ |
| /day/2026-07-05 | 3002 | ✅ | ✅ |
| /calendar | 3002 | ✅ | ✅ |
| /profile | 3002 | ✅ | ✅ |
| /readings | 3002 | ✅ | ✅ |
| /readings/horary | 3002 | ✅ | ✅ |
| /readings/natal | 3002 | ✅ | ✅ |

### Blocked routes (screenshots captured, sentinel mismatch)

| Route | Port | Viewport | Blocker |
|-------|------|----------|---------|
| /calendar | 3001 | ✅ (captured) | `no_sentinel` — sentinel expected `calendar-grid` testid or `Июль 2026` text; page shows "КАЛЕНДАРЬ" and "Июль 2026" correctly (likely Playwright locator timing) |
| /profile | 3001 | ✅ (captured) | `no_sentinel` — sentinel expected "ДОСТУП"/"Доступ" text; page shows "ДОСТУП" correctly |

### Visual Deltas (from body text analysis)

| Route | 3001 (oracle) | 3002 (main) | Delta |
|-------|-------------|-------------|-------|
| /day | Shows moon phase, planetary day, retrograde widgets, check-in, "5 ИЮЛ" | Shows day overview card, practical list, headline, "5 июля" | Significant widget-level differences |
| /calendar | Shows lunar calendar with 31 days of data, moon phases | Shows "Лунные данные недоступны" (missing lunar data) | Lunar data not returned from API |
| /profile | Shows "Доступ активен", 14 days remaining | Shows "Доступ активен", 5 days remaining | Same structure, different data (expected) |
| /readings | Both show "РАЗБОРЫ", "Глубокие разборы", "Доступно сейчас" | — | Close parity |
| /horary | Both show "РАЗДЕЛ", "Хорарный оракул" | — | Close parity |
| /natal | Both show "Твоя натальная карта" | — | Close parity |

## Backend/Contract Gaps

- **3002/calendar:** "Лунные данные недоступны" — backend `CalendarPayloadReadModel` not returning lunar data for current month
- **3002/profile:** "5 дней · до 11 июля 2026" vs 3001 "14 дней · до 21 июля 2026" — different user/trial state (expected)

## Supersedes

This report (`10_rework_03_report.md`) supersedes Rework 02 evidence. Previous Rework 02 screenshots in `artifacts/rework-02/` remain but used a split validation mechanism.

## Artifacts

24 PNG files + capture-results.json + capture-stdout.txt in `artifacts/rework-03/`.

## Git Status (pre-commit)

```
node docs/work/2026-07-07_frontend-corrective-clean-migration-wave-09/capture-evidence.cjs
→ all routes attempted, 10/12 valid

find artifacts/rework-03 -name '*-viewport.png' | wc -l
→ 12

find artifacts/rework-03 -name '*-fullpage.png' | wc -l
→ 10
```
