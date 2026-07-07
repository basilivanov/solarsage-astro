# Wave 09 Rework 04 Architect Review — Rework Required

Status: **REJECTED / REWORK REQUIRED**

Reviewed commit: `a0c9538`
Report: `docs/work/2026-07-07_frontend-corrective-clean-migration-wave-09/13_rework_04_report.md`

## Summary

Rework 04 fixed important parts:

- 12/12 routes are now marked valid.
- 12 viewport artifacts exist.
- 12 fullPage artifacts exist.
- 48 scroll artifacts exist.
- accidental executable modes were cleaned up for docs/data/images.

However, the scroll artifacts are not real below-the-fold screenshots. They are byte-identical to the viewport/fullPage screenshots for the same route.

This means the evidence gate still fails the user's core requirement: verify information below the first screen.

## Findings

### P0 — Scroll artifacts are identical to the first viewport

For `/day/2026-07-05`, all supposed scroll screenshots have the same hash and size as the first viewport.

3001:

```text
3001-day-2026-07-05-viewport.png       md5 4c6a0fc11f
3001-day-2026-07-05-fullpage.png       md5 4c6a0fc11f
3001-day-2026-07-05-scroll-00.png      md5 4c6a0fc11f
3001-day-2026-07-05-scroll-01.png      md5 4c6a0fc11f
3001-day-2026-07-05-scroll-02.png      md5 4c6a0fc11f
3001-day-2026-07-05-scroll-03.png      md5 4c6a0fc11f
3001-day-2026-07-05-scroll-bottom.png  md5 4c6a0fc11f
```

3002:

```text
3002-day-2026-07-05-viewport.png       md5 314b1b014c
3002-day-2026-07-05-fullpage.png       md5 314b1b014c
3002-day-2026-07-05-scroll-00.png      md5 314b1b014c
3002-day-2026-07-05-scroll-bottom.png  md5 314b1b014c
```

Visual inspection confirms `scroll-bottom` still shows the top of the page.

### P0 — Script detects the scroll container but scrolls `window`

`capture-results.json` correctly reports an internal scroll container:

```json
"scrollContainerDescription": ".flex-1.overflow-y-auto.overscroll-contain",
"scrollContainerScrollHeight": 3115,
"scrollContainerClientHeight": 857,
"scrollContainerMaxScrollTop": 2258
```

But `capture-evidence.cjs` scrolls the window:

```js
window.scrollTo(0, st);
```

The document itself has:

```json
"documentScrollHeight": 932,
"documentClientHeight": 932
```

So `window.scrollTo(...)` cannot move the visible content. The script must scroll the detected element itself.

### P0 — No verification that screenshots changed after scroll

The script records intended scroll offsets but does not verify:

- actual scrollTop applied to the detected element;
- screenshot hash changed from viewport/top when `maxScrollTop > 0`;
- bottom screenshot differs from top for scrollable routes.

Counters alone are insufficient.

### P1 — `fullPageImageSize` is still null

The Rework 04 TZ required:

```json
"fullPageImageSize"
```

Current JSON has:

```json
"fullPageImageSize": null
```

This does not block the root finding, but it is still a missed contract field.

## Required Rework

Create `15_rework_05_TZ.md` and send it to the coder.

Rework 05 must:

- scroll the actual detected element, not `window`;
- record actual scrollTop values after each scroll;
- write PNG dimensions and hashes into JSON;
- fail if scrollable routes produce identical screenshots for top and bottom;
- produce a new `artifacts/rework-05/` evidence set.

## Review Decision

Rejected. Do not use Rework 04 as the visual gate.
