# Wave 09 Rework 04 TZ — Scroll-Container Evidence + Cleanup

Branch: `main`
Rejected commit: `49a07c7`
Architect review: `docs/work/2026-07-07_frontend-corrective-clean-migration-wave-09/11_rework_03_review.md`

## Status

Rework 03 is rejected.

This is still **audit/evidence only**. Do not change production frontend/backend code.

## Goal

Fix the evidence gate so it proves both:

1. the first Telegram viewport;
2. route content below the first viewport.

The current `fullPage` screenshots are all `430x932`, so they do **not** prove below-the-fold content. The app scrolls inside an internal container. You must capture that internal scrolling content.

## Required Work

### 1. Clean up accidental executable file modes

Commit `49a07c7` introduced unrelated mode changes from `100644` to `100755`.

Restore non-executable mode for all existing docs/data/artifacts under:

`docs/work/2026-07-07_frontend-corrective-clean-migration-wave-09/`

Rules:

- `*.md`: `0644`
- `*.json`: `0644`
- `*.txt`: `0644`
- `*.png`: `0644`
- scripts may be `0644` or `0755`, but do not chmod the whole tree.

Self-check:

```bash
git diff --summary HEAD^..HEAD | grep 'mode change' || true
```

After your cleanup commit, there must be no old docs/artifact files left executable just because of `chmod -R`.

Do not use `chmod -R 755`.

### 2. Fix 3001 sentinels

The current script incorrectly marks 3001 `/calendar` and `/profile` as blocked even though `bodyTextSample` contains required text.

Fix readiness using same-page DOM/body text fallback:

- `/calendar` 3001 is ready when body text contains `КАЛЕНДАРЬ` and `Июль 2026`.
- `/profile` 3001 is ready when body text contains `ПРОФИЛЬ` and either `ДОСТУП` or `Доступ активен`.

Expected after rework:

- `3001 /calendar`: `valid=true`
- `3001 /profile`: `valid=true`

### 3. Capture scroll-container evidence

For every `{port, route}`, capture:

- viewport screenshot: `430x932`, first screen;
- Playwright `fullPage` screenshot;
- scroll-section screenshots for the actual scrollable container when `fullPage` is not taller than viewport.

Because Rework 03 proved `fullPage` is not enough, Rework 04 must include scroll-section evidence for every route where content can scroll internally.

Recommended algorithm:

1. After route is ready, detect the main scroll container in the page:
   - prefer a visible element with the largest `scrollHeight - clientHeight`;
   - fallback to `document.scrollingElement`;
   - record selector/description in JSON.
2. Record:
   - `documentScrollHeight`
   - `documentClientHeight`
   - `scrollContainerScrollHeight`
   - `scrollContainerClientHeight`
   - `scrollContainerMaxScrollTop`
3. Capture viewport at top.
4. Capture Playwright fullPage.
5. If the scroll container has `maxScrollTop > 0`, capture scroll slices:
   - `scroll-00` at top;
   - intermediate slices every viewport height minus overlap;
   - final slice at bottom;
   - restore scroll position if needed.
6. If `fullPage` image dimensions are `430x932`, do **not** treat it as below-fold evidence. The scroll slices are the real below-fold evidence.

Required names under:

`docs/work/2026-07-07_frontend-corrective-clean-migration-wave-09/artifacts/rework-04/`

Examples:

- `3001-day-2026-07-05-viewport.png`
- `3001-day-2026-07-05-fullpage.png`
- `3001-day-2026-07-05-scroll-00.png`
- `3001-day-2026-07-05-scroll-01.png`
- `3001-day-2026-07-05-scroll-bottom.png`

### 4. JSON contract

Write:

`artifacts/rework-04/capture-results.json`

Each route entry must include:

- `port`
- `route`
- `valid`
- `blocker`
- `viewportArtifact`
- `fullPageArtifact`
- `scrollArtifacts`
- `readySentinels`
- `bodyTextSample`
- `documentScrollHeight`
- `documentClientHeight`
- `fullPageImageSize`
- `scrollContainerDescription`
- `scrollContainerScrollHeight`
- `scrollContainerClientHeight`
- `scrollContainerMaxScrollTop`
- `notes`

Consistency rules:

- If a PNG exists, JSON must point to it.
- If `valid=true`, `viewportArtifact` and `fullPageArtifact` must be non-null.
- If `scrollContainerMaxScrollTop > 0`, `scrollArtifacts` must include at least top and bottom screenshots.
- If `fullPageImageSize.height <= 932` and `scrollContainerMaxScrollTop > 0`, the route still needs scroll artifacts.
- Do not claim `24 PNG files` unless exactly 24 PNG files exist.

### 5. Report

Write:

`docs/work/2026-07-07_frontend-corrective-clean-migration-wave-09/13_rework_04_report.md`

The report must include:

- command used to run capture;
- API preflight using `http://127.0.0.1:8000/api/health`;
- table of all 12 routes with viewport/fullPage/scroll artifacts;
- PNG counts:
  - viewport count;
  - fullPage count;
  - scroll screenshot count;
- statement that Rework 04 supersedes Rework 03;
- list of visual deltas relevant to the future frontend migration;
- confirmation accidental mode changes were cleaned.

### 6. Scope Boundaries

Allowed:

- edit/add docs, script, and artifacts under `docs/work/2026-07-07_frontend-corrective-clean-migration-wave-09/`;
- fix file modes under that same folder.

Forbidden:

- production frontend/backend changes;
- `e2e/**` changes;
- changing nginx/systemd/env;
- deleting previous reports/artifacts;
- using `/tmp` as final evidence;
- using `chmod -R 755`;
- reporting success when scroll artifacts are missing for internally scrollable routes.

## Required Self-Check Before Commit

Run and record outputs:

```bash
node docs/work/2026-07-07_frontend-corrective-clean-migration-wave-09/capture-evidence.cjs | tee docs/work/2026-07-07_frontend-corrective-clean-migration-wave-09/artifacts/rework-04/capture-stdout.txt
test -s docs/work/2026-07-07_frontend-corrective-clean-migration-wave-09/artifacts/rework-04/capture-results.json
find docs/work/2026-07-07_frontend-corrective-clean-migration-wave-09/artifacts/rework-04 -name '*-viewport.png' | wc -l
find docs/work/2026-07-07_frontend-corrective-clean-migration-wave-09/artifacts/rework-04 -name '*-fullpage.png' | wc -l
find docs/work/2026-07-07_frontend-corrective-clean-migration-wave-09/artifacts/rework-04 -name '*-scroll-*.png' | wc -l
python3 - <<'PY'
import json
from pathlib import Path
p = Path('docs/work/2026-07-07_frontend-corrective-clean-migration-wave-09/artifacts/rework-04/capture-results.json')
data = json.loads(p.read_text())
assert len(data) == 12
bad = []
for row in data:
    if not row.get('valid'):
        bad.append((row['port'], row['route'], row.get('blocker')))
    if row.get('scrollContainerMaxScrollTop', 0) > 0 and len(row.get('scrollArtifacts') or []) < 2:
        bad.append((row['port'], row['route'], 'missing_scroll_artifacts'))
print('bad=', bad)
assert not bad
PY
git diff --summary HEAD^..HEAD | grep 'mode change' || true
git status --short
```

Expected minimum:

- viewport PNGs: `12`
- fullPage PNGs: `12`
- scroll PNGs: at least `12`, and more for long routes
- JSON entries: `12`
- invalid routes: `0`

If a route is genuinely blocked, stop and report `BLOCKED` instead of committing a fake green gate.

## Commit

Commit only Wave 09 docs/artifacts/script changes.

Suggested message:

```bash
docs: add scroll-container migration evidence
```

## Callback

After commit, run:

```bash
curl --max-time 10 -X POST http://127.0.0.1:18765/trigger \
  -H "Authorization: Bearer 324b0306c32ffc5f6a64e16076c8c9ac0ee12fbba925cfd3" \
  -H "Content-Type: application/json" \
  -d '{"prompt":"Wave 09 Rework 04 ready for architect review. Report: docs/work/2026-07-07_frontend-corrective-clean-migration-wave-09/13_rework_04_report.md. Review: docs/work/2026-07-07_frontend-corrective-clean-migration-wave-09/11_rework_03_review.md. Branch: main. Commit: <commit>."}'
```
