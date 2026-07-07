# Rework 01 TZ: Wave 07 Main Integration

Date: 2026-07-07
Status: ready for coder
Owner: architect
Coder model: Flash 3.5
Branch: `main`
Reviewed commit: `ee0fb3c`
Base review: `docs/work/2026-07-07_frontend-migration-wave-07-main-integration/02_arch_review.md`

## Goal

Fix the Wave 07 report and required diff-check gate without changing product code.

This rework is docs/report only. Do not change frontend/backend source, tests, configs, systemd, nginx, bot config, `.env.production`, or canonical `3002`.

Do not push in this rework. Push remains blocked until architect accepts the corrected integration report.

## Required Fixes

### 1. Fix whitespace and rerun diff-check

Update:

```text
docs/work/2026-07-07_frontend-migration-wave-07-main-integration/01_agent_report.md
```

Required:

- Remove the `new blank line at EOF` problem.
- Rerun:

```bash
git diff --check origin/main..HEAD
git diff --check
```

- Record both fresh results in the report.

### 2. Correct the diff-check gate name

In the `Gates` section, replace:

```text
git diff --check main..HEAD
```

with:

```text
git diff --check origin/main..HEAD
```

The report must not imply that `main..HEAD` proves anything while already on `main`.

### 3. Fix report commit evidence

In `Self-Check`, replace:

```text
Commit `4166c21` (to be generated)
```

with the actual original report commit:

```text
Commit `ee0fb3c`
```

Then add a `Rework 01` section with:

- new rework commit SHA;
- files changed;
- exact commands rerun and results;
- explicit statement that product code was not changed;
- explicit statement that push was not attempted.

### 4. Make optional full mobile e2e failure precise

Update the optional full mobile e2e section.

It must list the concrete failures from `test-results/*/error-context.md`:

- `edge-cases.spec.ts >> Onboarding — Validation >> should handle network error during profile save (graceful)`;
- `edge-cases.spec.ts >> Calendar >> should navigate to day on click`;
- `edge-cases.spec.ts >> Reset >> should load reset page and show done state`;
- `locked-features.spec.ts >> Locked Features >> /readings page shows Спросить in TabBar`;
- note that optional run also produced WebKit/browser channel-closed artifacts around mock-visual calendar.

Keep this wording clear:

- required mock-visual mobile gate passed;
- optional full mobile e2e gate failed;
- push was not attempted because the optional gate failed and the TZ required architect review before push.

## Required Gates

Run and report exact results:

```bash
git status --short --branch
git diff --check origin/main..HEAD
git diff --check
```

Do not rerun full Vitest/Pytest/Playwright unless you changed anything beyond the docs report, which is not expected.

## Commit Requirements

Create one new commit on `main`:

```bash
git add docs/work/2026-07-07_frontend-migration-wave-07-main-integration/01_agent_report.md
git commit -m "docs: fix frontend migration main integration report"
```

Do not commit:

- `.grace/`
- `grace.db`
- `skills/`
- `docs/superpowers/plans/2026-07-05-fix-day-route-auth-build.md`
- `test-results/`
- `playwright-report/`
- unrelated files

## Required Callback

At the very end, run this callback from the repo root:

```bash
curl --max-time 10 -X POST http://127.0.0.1:18765/trigger \
  -H "Authorization: Bearer 324b0306c32ffc5f6a64e16076c8c9ac0ee12fbba925cfd3" \
  -H "Content-Type: application/json" \
  -d '{"prompt":"Wave 07 Rework 01 ready for architect review. Report: docs/work/2026-07-07_frontend-migration-wave-07-main-integration/01_agent_report.md. Review: docs/work/2026-07-07_frontend-migration-wave-07-main-integration/02_arch_review.md. Rework TZ: docs/work/2026-07-07_frontend-migration-wave-07-main-integration/03_rework_01_TZ.md. Branch: main. Commit: <commit_sha>. Push: NOT_ATTEMPTED"}'
```

Replace `<commit_sha>` with the actual Rework 01 commit SHA.
