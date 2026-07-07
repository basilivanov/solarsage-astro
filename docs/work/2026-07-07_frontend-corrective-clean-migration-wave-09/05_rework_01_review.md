# Wave 09 Rework 01 Architect Review — Rework Required

Status: **REJECTED / REWORK REQUIRED**

Reviewed commit: `f413149`
Report: `docs/work/2026-07-07_frontend-corrective-clean-migration-wave-09/04_rework_01_report.md`

## Summary

Rework 01 improved the data-safety classification direction, but it still fails the evidence gate. The report claims valid screenshots and a capture run, but the committed tree contains no `artifacts/rework-01/` screenshots or blocker files. The capture command in the report references a file that does not exist, and the committed capture script has a navigation bug that prevents it from proving the stated evidence.

Do not use this report to choose the migration strategy yet.

## Findings

### P0 — Required rework screenshots are missing from the commit

The report claims valid captures are in `artifacts/rework-01/`:

- `04_rework_01_report.md:13-22`
- `04_rework_01_report.md:31-38`
- `04_rework_01_report.md:183`

But the commit contains only:

- `04_rework_01_report.md`
- `capture-evidence.mjs`

There is no committed `docs/work/2026-07-07_frontend-corrective-clean-migration-wave-09/artifacts/rework-01/` directory, no new PNGs, and no `.txt` blocker files. The only screenshots still present are the original invalid auth-loading artifacts from the first audit run.

### P0 — Report references a capture test that does not exist

The report says this command was run:

- `04_rework_01_report.md:169-171`: `E2E_BASE_URL=http://localhost:3002 npx playwright test e2e/wave-09-capture.spec.ts --project=mobile`

But `e2e/wave-09-capture.spec.ts` does not exist in the working tree or the submitted commit. The only submitted capture tool is `docs/work/.../capture-evidence.mjs`. The report and artifacts must be internally consistent and reproducible.

### P0 — Submitted capture script does not navigate to the target services

`capture-evidence.mjs:40` defines `baseURL`, but `capture-evidence.mjs:109` calls:

```js
await page.goto(path, ...)
```

In a raw Playwright `chromium.launch()` context, this does not navigate to `http://127.0.0.1:3001${path}` or `http://127.0.0.1:3002${path}`. The capture script must use an absolute URL:

```js
await page.goto(`${baseURL}${path}`, ...)
```

As submitted, the script cannot substantiate the report's claim that all 12 routes were captured successfully.

### P1 — 3001 sentinels are not verified against the oracle code

The report claims 3001 sentinels such as `calendar-screen`, `profile-screen`, `readings-screen`, and `natal-preview-screen`.

Those exact `data-testid` values are not present in the 3001 oracle for several route families. For example:

- 3001 calendar has visible route evidence like `Календарь`, `aria-label="Предыдущий месяц"`, `aria-label="Следующий месяц"`, but no `data-testid="calendar-screen"`.
- 3001 profile has visible `Профиль`, but no `data-testid="profile-screen"`.
- 3001 readings has visible `Разборы`, `Доступно сейчас`, `Скоро будет`, but no `data-testid="readings-screen"`.
- 3001 natal page has visible natal content, but no `data-testid="natal-preview-screen"`.

Sentinels must be route-specific and actually present in the rendered DOM for each app version. Do not use a single assumed `data-testid` table for both 3001 and 3002.

### P1 — Report still makes strategic recommendation without committed visual evidence

The corrected recommendation switches to Option A in `04_rework_01_report.md:131-141`. This may be directionally right, but it is not yet acceptable because the valid visual evidence is missing. Recommendation may stay, but confidence must be downgraded to blocked/pending until the artifacts are present and architect-reviewed.

## Required Rework

Create `06_rework_02_TZ.md` and send it to the coder. The next rework must:

- fix the capture script or replace it with a reproducible command;
- capture absolute URLs for both 3001 and 3002;
- use route-specific sentinels that actually exist per app version;
- commit the new screenshots or blocker `.txt` files;
- include a machine-readable capture result file and command stdout;
- correct the report so every claim points to committed artifacts.

## Review Decision

Rejected. Evidence gate is still not satisfied.
