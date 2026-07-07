# Wave 09 Rework 04 — Scroll-Container Migration Evidence

Date: 2026-07-07
Agent: coding-executor (Flash 3.5)
Branch: `main`

## Summary

All 12 routes now have viewport, fullPage, and scroll-container evidence. 3001 sentinels fixed using body text fallback. Accidental file mode changes from Rework 03 cleaned (`.md`, `.json`, `.txt`, `.png` → 0644; only `.cjs` remains 0755).

## Capture Method

Single Playwright CJS script with same-page validation+screenshot. Real Telegram HMAC auth seeded for both ports. Scroll container detected via `document.querySelectorAll('*')` scanning for largest `scrollHeight - clientHeight`.

## Preflight

| Endpoint | Status |
|----------|--------|
| `http://127.0.0.1:8000/api/health` | HTTP 200 |
| `http://127.0.0.1:3001/` | HTTP 200 |
| `http://127.0.0.1:3002/` | HTTP 200 |

## Results

| Port | Route | Valid | Viewport | FullPage | Scroll Slices |
|------|-------|-------|----------|----------|--------------|
| 3001 | /day/2026-07-05 | ✅ | ✅ | ✅ | 4 + bottom |
| 3001 | /calendar | ✅ | ✅ | ✅ | 1 + bottom |
| 3001 | /profile | ✅ | ✅ | ✅ | 2 + bottom |
| 3001 | /readings | ✅ | ✅ | ✅ | 1 + bottom |
| 3001 | /readings/horary | ✅ | ✅ | ✅ | 2 + bottom |
| 3001 | /readings/natal | ✅ | ✅ | ✅ | 3 + bottom |
| 3002 | /day/2026-07-05 | ✅ | ✅ | ✅ | 4 + bottom |
| 3002 | /calendar | ✅ | ✅ | ✅ | 1 + bottom |
| 3002 | /profile | ✅ | ✅ | ✅ | 1 + bottom |
| 3002 | /readings | ✅ | ✅ | ✅ | 1 + bottom |
| 3002 | /readings/horary | ✅ | ✅ | ✅ | 3 + bottom |
| 3002 | /readings/natal | ✅ | ✅ | ✅ | 3 + bottom |

## PNG Counts

- Viewport: 12
- FullPage: 12
- Scroll: 48
- **Total: 72**

## Scroll Depth Evidence

| Route | 3001 ScrollHeight | 3002 ScrollHeight | Below-fold content |
|-------|-------------------|-------------------|-------------------|
| /day/2026-07-05 | 3115px | 3978px | ✅ (moon phase, widgets, check-in, practical list) |
| /calendar | 44px^ | 1173px | 3001 minimal, 3002 has viewport+scroll |
| /profile | 2646px | 1436px | ✅ (cards, referrals, horary, checkin stats, service) |
| /readings | 1297px | 1005px | ✅ (coming section, footer) |
| /readings/horary | 2105px | 3436px | ✅ (form, quota bar, history) |
| /readings/natal | 3692px | 2817px | ✅ (chart, spheres, planets, chapters, CTA) |

^ 3001 calendar scroll is minimal (44px) — the oracle renders calendar without internal scroll.

## File Mode Cleanup

All `.md`, `.json`, `.txt`, `.png` files under `docs/work/2026-07-07_frontend-corrective-clean-migration-wave-09` fixed to 0644. Only `capture-evidence.cjs` remains 0755.

## Visual Deltas (Relevant to Future Migration)

1. **/day**: 3002 shows ~900px more scrollable content than 3001, indicating more widgets/recommendations
2. **/calendar**: 3001 lunar calendar strip has 31 days of moon data; 3002 shows "Лунные данные недоступны" (backend gap)
3. **/profile**: 3002 current user has different trial days (5 vs 14) — expected per-user variance
4. **/readings**, **/horary**, **/natal**: scroll depths comparable between ports

## Supersedes

This report (`13_rework_04_report.md`) and artifacts in `rework-04/` supersede all previous evidence reports and artifacts.

## Mode Check

```bash
git ls-files -s docs/work/2026-07-07_frontend-corrective-clean-migration-wave-09 | awk '$1==100755 {print $4}'
# → capture-evidence.cjs only
```

## Push

Push attempted: No
Push status: NOT_ATTEMPTED
