# Wave 09 Rework 05 TZ — Real Internal Scroll Capture

Branch: `main`
Rejected commit: `a0c9538`
Architect review: `docs/work/2026-07-07_frontend-corrective-clean-migration-wave-09/14_rework_04_review.md`

## Status

Rework 04 is rejected.

This is still **audit/evidence only**. Do not change production frontend/backend code.

## Root Cause

Rework 04 detected the internal scroll container correctly, but then scrolled `window`.

The app document is fixed-height:

```json
"documentScrollHeight": 932,
"documentClientHeight": 932
```

The real scroll container is an element like:

```json
"scrollContainerDescription": ".flex-1.overflow-y-auto.overscroll-contain"
```

So `window.scrollTo(...)` does not move visible content. This produced fake scroll artifacts: `scroll-bottom.png` is byte-identical to the first viewport.

## Goal

Produce real below-the-fold screenshots by scrolling the actual detected element and proving that the screenshots changed.

## Required Work

### 1. Do not reuse Rework 04 artifacts

Write a new evidence set under:

`docs/work/2026-07-07_frontend-corrective-clean-migration-wave-09/artifacts/rework-05/`

Write report:

`docs/work/2026-07-07_frontend-corrective-clean-migration-wave-09/16_rework_05_report.md`

### 2. Mark and scroll the real container

When detecting the scroll container, mark the chosen element in DOM:

```js
best.setAttribute('data-evidence-scroll-root', 'true')
```

Then scroll that exact element:

```js
const actual = await page.evaluate((top) => {
  const el = document.querySelector('[data-evidence-scroll-root="true"]')
  if (!el) return null
  el.scrollTop = top
  el.dispatchEvent(new Event('scroll', { bubbles: true }))
  return el.scrollTop
}, targetScrollTop)
```

Do not use `window.scrollTo` for routes whose detected scroll container is not the document.

After every scroll:

- wait briefly for rendering;
- record requested scrollTop;
- record actual scrollTop;
- screenshot the page viewport.

### 3. Prove scroll artifacts are real

For every route where `scrollContainerMaxScrollTop > 0`:

- capture top screenshot;
- capture at least one middle screenshot when the route is long enough;
- capture bottom screenshot;
- compute SHA256 or MD5 hash for every artifact;
- require at least two unique hashes among scroll artifacts;
- require `scroll-bottom` hash to differ from `viewport` hash when `maxScrollTop > 100`;
- record `actualScrollTops` in JSON.

If these checks fail, set `valid=false` and `blocker="scroll_artifacts_identical"` or `blocker="scroll_not_applied"`. Do not commit a green report.

### 4. JSON contract

Write:

`artifacts/rework-05/capture-results.json`

Each route entry must include:

- `port`
- `route`
- `valid`
- `blocker`
- `viewportArtifact`
- `fullPageArtifact`
- `scrollArtifacts`
- `artifactHashes`
- `artifactImageSizes`
- `requestedScrollTops`
- `actualScrollTops`
- `uniqueScrollHashCount`
- `readySentinels`
- `bodyTextSample`
- `documentScrollHeight`
- `documentClientHeight`
- `scrollContainerDescription`
- `scrollContainerScrollHeight`
- `scrollContainerClientHeight`
- `scrollContainerMaxScrollTop`
- `notes`

Required consistency:

- all artifact paths in JSON must exist;
- all 12 routes must be `valid=true`;
- for `scrollContainerMaxScrollTop > 100`, bottom hash must differ from viewport hash;
- for `scrollContainerMaxScrollTop > 100`, `uniqueScrollHashCount >= 2`;
- actual bottom scrollTop must be within 5px of `scrollContainerMaxScrollTop`.

### 5. Image dimensions

Record PNG dimensions in JSON by reading the PNG header or using any already-installed package.

Do not leave image size fields null.

### 6. Report

`16_rework_05_report.md` must include:

- exact capture command;
- API health preflight using `http://127.0.0.1:8000/api/health`;
- counts:
  - viewport PNGs;
  - fullPage PNGs;
  - scroll PNGs;
  - invalid routes;
- table with route, port, maxScrollTop, actual bottom scrollTop, unique scroll hashes, top/bottom hash comparison;
- explicit statement that Rework 05 supersedes Rework 04;
- visual deltas relevant to future frontend migration;
- mode check output showing only `capture-evidence.cjs` is executable.

### 7. Self-Check

Run and record:

```bash
node docs/work/2026-07-07_frontend-corrective-clean-migration-wave-09/capture-evidence.cjs | tee docs/work/2026-07-07_frontend-corrective-clean-migration-wave-09/artifacts/rework-05/capture-stdout.txt

python3 - <<'PY'
import json
from pathlib import Path
p = Path('docs/work/2026-07-07_frontend-corrective-clean-migration-wave-09/artifacts/rework-05/capture-results.json')
data = json.loads(p.read_text())
bad = []
for row in data:
    if not row.get('valid'):
        bad.append((row['port'], row['route'], row.get('blocker')))
    max_scroll = row.get('scrollContainerMaxScrollTop') or 0
    if max_scroll > 100:
        hashes = row.get('artifactHashes') or {}
        vp = row.get('viewportArtifact')
        bottom = next((x for x in row.get('scrollArtifacts') or [] if 'bottom' in x), None)
        if not bottom:
            bad.append((row['port'], row['route'], 'missing_bottom_scroll'))
        elif hashes.get(vp) == hashes.get(bottom):
            bad.append((row['port'], row['route'], 'bottom_same_as_viewport'))
        if (row.get('uniqueScrollHashCount') or 0) < 2:
            bad.append((row['port'], row['route'], 'scroll_hashes_not_unique'))
        actual = row.get('actualScrollTops') or []
        if not actual or abs(actual[-1] - max_scroll) > 5:
            bad.append((row['port'], row['route'], 'bottom_scroll_not_applied'))
print('bad=', bad)
assert len(data) == 12
assert not bad
PY

find docs/work/2026-07-07_frontend-corrective-clean-migration-wave-09/artifacts/rework-05 -name '*-viewport.png' | wc -l
find docs/work/2026-07-07_frontend-corrective-clean-migration-wave-09/artifacts/rework-05 -name '*-fullpage.png' | wc -l
find docs/work/2026-07-07_frontend-corrective-clean-migration-wave-09/artifacts/rework-05 -name '*-scroll-*.png' | wc -l
git ls-files -s docs/work/2026-07-07_frontend-corrective-clean-migration-wave-09 | awk '$1==100755 {print $4}'
git status --short
```

### 8. Scope Boundaries

Allowed:

- update `capture-evidence.cjs`;
- add `artifacts/rework-05/*`;
- add `16_rework_05_report.md`;
- keep prior artifacts/reports.

Forbidden:

- production frontend/backend changes;
- `e2e/**` changes;
- deleting previous evidence;
- using `/tmp` as final evidence;
- committing green evidence with identical scroll screenshots.

## Commit

Commit only Wave 09 docs/artifacts/script changes.

Suggested message:

```bash
docs: add verified internal-scroll migration evidence
```

## Callback

After commit, run:

```bash
curl --max-time 10 -X POST http://127.0.0.1:18765/trigger \
  -H "Authorization: Bearer 324b0306c32ffc5f6a64e16076c8c9ac0ee12fbba925cfd3" \
  -H "Content-Type: application/json" \
  -d '{"prompt":"Wave 09 Rework 05 ready for architect review. Report: docs/work/2026-07-07_frontend-corrective-clean-migration-wave-09/16_rework_05_report.md. Review: docs/work/2026-07-07_frontend-corrective-clean-migration-wave-09/14_rework_04_review.md. Branch: main. Commit: <commit>."}'
```
