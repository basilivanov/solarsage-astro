# Wave 09 Rework 03 TZ — Authenticated Full-Page Visual Evidence Gate

Branch: `main`
Previous report: `docs/work/2026-07-07_frontend-corrective-clean-migration-wave-09/07_rework_02_report.md`
Architect review: `docs/work/2026-07-07_frontend-corrective-clean-migration-wave-09/08_rework_02_review.md`

## Status

Rework 02 is rejected.

Your task is **audit/evidence only**. Do not change production frontend/backend code in this wave.

## Root Cause To Fix

The previous evidence gate was invalid because it captured screenshots and validated routes through different mechanisms:

- screenshots: unauthenticated `npx playwright screenshot`;
- validation: authenticated `curl`;
- result: PNG artifacts could show `Авторизация...` while JSON marked the same route as valid.

This must not happen again.

The user also correctly pointed out that first-screen screenshots are insufficient. Important visual/content parity is below the fold, so the next gate must capture the full route content.

## Goal

Produce a trustworthy visual evidence package comparing:

- mock-preview visual oracle on `http://127.0.0.1:3001`;
- current main production frontend on `http://127.0.0.1:3002`;

for these routes:

- `/day/2026-07-05`
- `/calendar`
- `/profile`
- `/readings`
- `/readings/horary`
- `/readings/natal`

The output must let the architect review both:

- first viewport Telegram framing;
- below-the-fold page content.

## Hard Requirements

### 1. Use Playwright page for both validation and screenshot

For each `{port, route}`:

1. create/open a Playwright browser page;
2. seed the required Telegram auth/session before navigation;
3. inject `window.Telegram.WebApp` before navigation;
4. navigate to the route;
5. wait until auth/loading/error states are gone;
6. wait until route-specific ready sentinel is visible;
7. validate DOM/text **from the same page**;
8. capture screenshots **from the same page**.

Do **not** use `npx playwright screenshot`.
Do **not** validate with `curl`.
Do **not** mark a route valid if the committed screenshot shows `Авторизация...`, generic loader, or an error screen.

### 2. Seed auth for both 3001 and 3002

3001 also renders `Авторизация...` initially in real reproduction. Treat both ports as auth-required.

Use the existing test initData flow:

- `scripts/generate-telegram-test-initdata.py`
- `POST http://127.0.0.1:8000/api/auth/telegram`
- resulting `grace_session_v2` cookie

Set the cookie for `127.0.0.1` before navigating to both `3001` and `3002` pages.

Also inject a minimal Telegram WebApp object with `initData`, `ready()`, `expand()`, and `close()` before route code runs.

### 3. Capture viewport and full-page evidence

For every route and every port, write both artifacts:

- viewport screenshot: `430x932`, first Telegram viewport;
- full-page screenshot: entire scrollable page after route is ready.

Required file naming under:

`docs/work/2026-07-07_frontend-corrective-clean-migration-wave-09/artifacts/rework-03/`

Use names like:

- `3001-day-2026-07-05-viewport.png`
- `3001-day-2026-07-05-fullpage.png`
- `3002-calendar-viewport.png`
- `3002-calendar-fullpage.png`

If Playwright full-page screenshot is unreliable for a route, add scroll-section screenshots too:

- `3002-day-2026-07-05-scroll-00.png`
- `3002-day-2026-07-05-scroll-01.png`

But full-page is still preferred and should be attempted first.

### 4. Strong ready sentinels

Do not treat route root alone as ready if it can exist during loading.

Use robust per-route sentinels. Examples:

#### 3001 `/day/2026-07-05`

Ready only when visible page text includes real day content such as:

- `14 дней бесплатного доступа`
- date/day content like `5 июля` or `5 ИЮЛ`
- and not `Авторизация`

`Конкретно сегодня` may be below the fold. Do not require it for viewport readiness, but full-page evidence should show whether it exists below.

#### 3002 `/day/2026-07-05`

Ready only when:

- `today-screen` is present;
- `14 дней бесплатного доступа` is visible;
- auth/loading/error text is absent.

#### 3001 `/calendar`

Ready only when rendered calendar content is visible, e.g.:

- `КАЛЕНДАРЬ`
- `Июль 2026`
- calendar grid or lunar calendar strip

#### 3002 `/calendar`

Ready only when:

- `calendar-screen` is present;
- `calendar-loading` is gone;
- either `calendar-grid` or `calendar-unavailable` is present.

If `calendar-unavailable` appears because real backend data is missing, mark the route valid as "loaded" but record the backend contract gap explicitly in JSON/report.

#### 3001 `/profile`

Ready only when profile content is visible, e.g.:

- `ПРОФИЛЬ`
- `ДОСТУП`
- profile/access card content

#### 3002 `/profile`

Ready only when:

- `profile-screen` is present;
- `profile-access-card` is present;
- auth/loading/error text is absent.

#### 3001 `/readings`

Ready only when rendered readings content is visible. Beware text case: the page may render `ДОСТУПНО СЕЙЧАС`, not `Доступно сейчас`.

#### 3002 `/readings`

Ready only when:

- `readings-screen` is present;
- `readings-available-section` is present;
- auth/loading/error text is absent.

#### 3001 `/readings/horary`

Ready only when the actual horary form/content is visible, e.g.:

- `Хорарный оракул`
- question textarea/input/form controls

#### 3002 `/readings/horary`

Ready only when:

- `horary-screen[data-state="ready"]` is present;
- `horary-form` or `horary-quota-section` is present;
- auth/loading/error text is absent.

#### 3001 `/readings/natal`

Ready only when natal content is visible, e.g.:

- `Твоя натальная карта`
- chart/content sections

#### 3002 `/readings/natal`

Ready only when:

- `natal-preview-screen[data-state="ready"]` is present;
- `natal-preview-content` is present;
- auth/loading/error text is absent.

### 5. Results must be internally consistent

Write:

- `artifacts/rework-03/capture-results.json`
- `artifacts/rework-03/capture-stdout.txt`

Every JSON route entry must include:

- `port`
- `route`
- `valid`
- `blocker` or `null`
- `viewportArtifact`
- `fullPageArtifact`
- `scrollArtifacts` if any
- `readySentinels`
- `missingSentinels`
- `bodyTextSample`
- `notes`

If `valid=true`, both screenshots must visibly show the real route, not auth/loading/error.

If screenshots are not valid, set `valid=false` and explain why. Do not fabricate success.

### 6. Report

Write:

`docs/work/2026-07-07_frontend-corrective-clean-migration-wave-09/10_rework_03_report.md`

The report must include:

- exact command used to run capture;
- service availability preflight for ports `8000`, `3001`, `3002`;
- table for each route/port with `valid`, viewport artifact path, full-page artifact path, blockers;
- explicit list of visual deltas discovered from evidence;
- explicit backend/contract gaps, if any;
- confirmation that Rework 02 evidence is superseded.

### 7. Scope Boundaries

Allowed:

- edit/add docs under `docs/work/2026-07-07_frontend-corrective-clean-migration-wave-09/`;
- add evidence scripts/artifacts under that same folder.

Forbidden:

- production frontend/backend changes;
- `e2e/**` changes;
- deleting previous wave reports/artifacts;
- changing systemd/nginx/env config;
- marking invalid screenshots as valid.

## Required Self-Check Before Commit

Run and record outputs in the report:

```bash
git status --short
node docs/work/2026-07-07_frontend-corrective-clean-migration-wave-09/capture-evidence.mjs | tee docs/work/2026-07-07_frontend-corrective-clean-migration-wave-09/artifacts/rework-03/capture-stdout.txt
test -s docs/work/2026-07-07_frontend-corrective-clean-migration-wave-09/artifacts/rework-03/capture-results.json
test -s docs/work/2026-07-07_frontend-corrective-clean-migration-wave-09/artifacts/rework-03/capture-stdout.txt
find docs/work/2026-07-07_frontend-corrective-clean-migration-wave-09/artifacts/rework-03 -name '*-viewport.png' | wc -l
find docs/work/2026-07-07_frontend-corrective-clean-migration-wave-09/artifacts/rework-03 -name '*-fullpage.png' | wc -l
git diff --stat
```

Expected screenshot counts:

- viewport PNGs: `12`
- full-page PNGs: `12`

If any route is blocked, still commit the evidence and mark it blocked honestly.

## Commit

Commit only Wave 09 docs/artifacts/script changes.

Suggested commit message:

```bash
docs: add authenticated full-page migration evidence
```

## Callback

After commit, run:

```bash
curl --max-time 10 -X POST http://127.0.0.1:18765/trigger \
  -H "Authorization: Bearer 324b0306c32ffc5f6a64e16076c8c9ac0ee12fbba925cfd3" \
  -H "Content-Type: application/json" \
  -d '{"prompt":"Wave 09 Rework 03 ready for architect review. Report: docs/work/2026-07-07_frontend-corrective-clean-migration-wave-09/10_rework_03_report.md. Review: docs/work/2026-07-07_frontend-corrective-clean-migration-wave-09/08_rework_02_review.md. Branch: main. Commit: <commit>."}'
```
