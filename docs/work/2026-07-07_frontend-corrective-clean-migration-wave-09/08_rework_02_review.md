# Wave 09 Rework 02 Architect Review — Rework Required

Status: **REJECTED / REWORK REQUIRED**

Reviewed commit: `383c997`
Report: `docs/work/2026-07-07_frontend-corrective-clean-migration-wave-09/07_rework_02_report.md`

## Summary

Rework 02 still cannot be accepted as the visual/evidence gate.

The committed files now include screenshots and `capture-results.json`, which is progress, but the screenshots are not trustworthy evidence because the capture method validates one thing and screenshots another thing. Several PNG artifacts visibly show the auth/loading screen while `capture-results.json` marks those same routes as valid.

The audit also still captures only the first viewport. For this migration, that is insufficient: route content below the fold is part of the required visual parity.

## Findings

### P0 — PNG screenshots contradict `capture-results.json`

Examples:

- `artifacts/rework-02/3001-day-2026-07-05.png` visibly shows only `Авторизация...`.
- `artifacts/rework-02/3002-day-2026-07-05.png` visibly shows only `Авторизация...`.

But `artifacts/rework-02/capture-results.json` marks both routes as valid:

- `3001 /day/2026-07-05`: `"valid": true`
- `3002 /day/2026-07-05`: `"valid": true`

That makes the evidence internally inconsistent. A route cannot be accepted if the machine result says "valid" while the committed screenshot shows auth/loading.

### P0 — Screenshot capture and validation use different mechanisms

`capture-evidence.sh` captures screenshots with:

```bash
npx playwright screenshot --viewport-size="430,932" "${full_url}" "${png_path}"
```

This command does not use the Telegram initData injection/session setup needed by the app.

Then the script validates with:

```bash
PAGE_HTML=$(curl -s -L -b "grace_session_v2=${COOKIE}" "${full_url}" ...)
```

So the screenshot comes from a browser without the same authenticated/hydrated app state, while validation comes from static HTML/curl. This is the exact cause of the false "valid" results.

The capture must happen in the same Playwright `page` after:

- session cookie is seeded;
- `window.Telegram.WebApp` is injected;
- auth/loading/error are gone;
- route-specific ready sentinel is visible.

Only then may the screenshot be taken.

### P0 — `capture-stdout.txt` is required but missing

`06_rework_02_TZ.md` required:

- `artifacts/rework-02/capture-results.json`
- `artifacts/rework-02/capture-stdout.txt`

The commit contains `capture-results.json` but does not contain `capture-stdout.txt`.

### P1 — Only first viewport was captured

All committed screenshots are first-viewport only. This is not enough for this migration because important content is below the fold:

- `/day`: concrete advice list, reading, why section, week strip, chart/hidden widgets.
- `/calendar`: selected day summary and lower calendar rows.
- `/profile`: referral, horary quota, check-in statistics, data/service rows.
- `/readings`: demo/coming sections, which are exactly where production must diverge from 3001.
- `/readings/natal`: chart, chapters, sales bullets/CTA.
- `/readings/horary`: form, question moment, history.

The next evidence set must include both:

- `viewport` screenshot for Telegram first-screen framing;
- `fullPage` screenshot or scroll-section screenshots for below-the-fold parity.

### P1 — 3001 does require auth flow in practice

Rework 01/02 assumed "3001 no auth required". In actual Playwright reproduction, 3001 also initially renders `Авторизация...` and needs the same session/Telegram setup before the real route appears. The next capture must seed auth for both 3001 and 3002.

### P1 — 3001 sentinel rules were too strict for real rendered text

During local reproduction, 3001 `/day` rendered real content:

`ДЕНЬ | 5 июля | 14 дней бесплатного доступа | ...`

but the previous sentinel expected `today-screen` or `Конкретно сегодня`; the text may be below the fold or absent in the first visible text chunk. Sentinels should use robust ready content per route, not brittle single strings.

## Required Rework

Create `09_rework_03_TZ.md` and send it to the coder. The next attempt must:

- use one Playwright page per captured route;
- seed Telegram auth/session for both 3001 and 3002;
- validate DOM in the same Playwright page that takes screenshots;
- wait for ready-state content, not just route root;
- capture both viewport and full-page artifacts;
- write `capture-results.json` and `capture-stdout.txt`;
- make every route result internally consistent with its screenshots.

## Review Decision

Rejected. Do not use Rework 02 as the audit gate.
