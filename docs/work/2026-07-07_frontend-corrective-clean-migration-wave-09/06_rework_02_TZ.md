# Wave 09 Rework 02 — Commit Reproducible Capture Evidence

> Role: implementer/auditor. Do not change production UI code.

## Goal

Fix Rework 01's evidence failure. The report must be backed by committed screenshots or committed blocker files, and the capture command must be reproducible from the committed audit artifacts.

## Read First

- Original TZ: `00_TZ.md`
- First review: `02_arch_review.md`
- Rework 01 TZ: `03_rework_01_TZ.md`
- Rework 01 report: `04_rework_01_report.md`
- Rework 01 review: `05_rework_01_review.md`

`05_rework_01_review.md` governs this rework.

## Non-Negotiable Constraints

- Do not edit production app/runtime code.
- Do not edit `app/**`, `components/**`, `lib/**`, `packages/**`, `apps/**`, or root config.
- Do not create or edit `e2e/**` for this audit. Keep audit-only scripts under this Wave 09 docs directory.
- Do not run destructive git operations.
- Do not force push.
- Do not claim valid screenshots unless the files are committed.
- Do not claim a command ran unless the exact committed command/stdout proves it.
- Commit only `docs/work/2026-07-07_frontend-corrective-clean-migration-wave-09/**`.

## Required Fixes

### 1. Fix Or Replace Capture Script

The current script defines `baseURL` but navigates to `path`. Fix it:

```js
await page.goto(`${baseURL}${path}`, { waitUntil: 'networkidle', timeout: 20000 })
```

If you replace the script, keep it under:

`docs/work/2026-07-07_frontend-corrective-clean-migration-wave-09/`

The script must exit with non-zero status if any expected route has neither a valid screenshot nor a blocker `.txt`.

### 2. Use Version-Specific Sentinels

Do not assume 3001 and 3002 have the same `data-testid`.

Use this sentinel model:

- 3002 current main: prefer real `data-testid` values where present.
- 3001 oracle: use actual 3001 DOM evidence from code or visible text/ARIA.

Minimum accepted sentinels:

| Port | Route | Sentinel Requirement |
|------|-------|----------------------|
| 3001 | `/day/2026-07-05` | visible `[data-testid="today-screen"]` OR visible text `Конкретно сегодня` |
| 3001 | `/calendar` | visible text `Календарь` AND visible button `aria-label="Предыдущий месяц"` |
| 3001 | `/profile` | visible text `Профиль` |
| 3001 | `/readings` | visible text `Разборы` AND visible text `Доступно сейчас` |
| 3001 | `/readings/horary` | visible text `Хорарный оракул` |
| 3001 | `/readings/natal` | visible text `Разборы` AND one of `Твой характер`, `Что войдёт в полный отчёт`, `Разбор по точным данным рождения` |
| 3002 | `/day/2026-07-05` | visible `[data-testid="today-screen"]` |
| 3002 | `/calendar` | visible `[data-testid="calendar-screen"]` |
| 3002 | `/profile` | visible `[data-testid="profile-screen"]` |
| 3002 | `/readings` | visible `[data-testid="readings-screen"]` |
| 3002 | `/readings/horary` | visible `[data-testid="horary-screen"]` |
| 3002 | `/readings/natal` | visible `[data-testid="natal-preview-screen"]` |

For every route also assert:

- final URL includes the expected route path;
- `Авторизация...` is not visible;
- `[data-testid="auth-loading"]` is not visible;
- `[data-testid="auth-error"]` is not visible.

### 3. Commit Capture Artifacts

Write new captures under:

`docs/work/2026-07-07_frontend-corrective-clean-migration-wave-09/artifacts/rework-02/`

Expected files for successful captures:

- `3001-day-2026-07-05.png`
- `3002-day-2026-07-05.png`
- `3001-calendar.png`
- `3002-calendar.png`
- `3001-profile.png`
- `3002-profile.png`
- `3001-readings.png`
- `3002-readings.png`
- `3001-horary.png`
- `3002-horary.png`
- `3001-natal.png`
- `3002-natal.png`

If a route cannot be captured, write the corresponding `.txt` blocker, for example:

- `3001-calendar.txt`
- `3002-calendar.txt`

The blocker must include:

- final URL,
- which sentinel failed,
- whether auth/loading/error was visible,
- relevant console/network error summary if available.

Also write:

- `artifacts/rework-02/capture-results.json`
- `artifacts/rework-02/capture-stdout.txt`

`capture-results.json` must list all 12 route attempts with:

```json
{
  "label": "3001",
  "route": "/calendar",
  "finalUrl": "http://127.0.0.1:3001/calendar",
  "valid": true,
  "artifact": "artifacts/rework-02/3001-calendar.png",
  "blocker": null,
  "sentinels": {
    "authLoadingVisible": false,
    "authErrorVisible": false,
    "authTextVisible": false,
    "routeSentinelVisible": true
  }
}
```

### 4. Update Report

Create:

`docs/work/2026-07-07_frontend-corrective-clean-migration-wave-09/07_rework_02_report.md`

Also append a short "Rework 02 supersedes Rework 01" section to:

`docs/work/2026-07-07_frontend-corrective-clean-migration-wave-09/04_rework_01_report.md`

The new report must include:

- exact command run;
- path to `capture-stdout.txt`;
- path to `capture-results.json`;
- table of 12 route attempts;
- list of valid screenshots and blockers;
- corrected statement that Rework 01 screenshots were missing;
- data-safety classification from Rework 01, corrected if necessary;
- strategy recommendation marked as `pending architect visual review` unless all required PNGs are present.

## Required Self-Check Before Commit

Run these commands and paste their outputs into `07_rework_02_report.md`:

```bash
find docs/work/2026-07-07_frontend-corrective-clean-migration-wave-09/artifacts/rework-02 -maxdepth 1 -type f | sort
git status --short --untracked-files=all docs/work/2026-07-07_frontend-corrective-clean-migration-wave-09
git diff --name-status HEAD -- docs/work/2026-07-07_frontend-corrective-clean-migration-wave-09
```

Before committing, verify that the artifact directory contains either `.png` or `.txt` for all 12 route names plus `capture-results.json` and `capture-stdout.txt`.

## Commit

Commit only Wave 09 docs/artifacts:

```bash
git add docs/work/2026-07-07_frontend-corrective-clean-migration-wave-09
git commit -m "docs: add corrective migration capture evidence"
```

## Callback

After the commit, notify the architect:

```bash
curl --max-time 10 -X POST http://127.0.0.1:18765/trigger \
  -H "Authorization: Bearer 324b0306c32ffc5f6a64e16076c8c9ac0ee12fbba925cfd3" \
  -H "Content-Type: application/json" \
  -d '{"prompt":"Wave 09 Rework 02 ready for architect review. Report: docs/work/2026-07-07_frontend-corrective-clean-migration-wave-09/07_rework_02_report.md. Review: docs/work/2026-07-07_frontend-corrective-clean-migration-wave-09/05_rework_01_review.md. Branch: <branch>. Commit: <commit>."}'
```

Return only a short completion line in tmux after callback.
