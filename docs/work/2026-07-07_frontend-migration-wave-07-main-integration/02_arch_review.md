# Architect Review: Wave 07 Main Integration

Date: 2026-07-07
Status: REWORK_REQUIRED
Reviewed branch: `main`
Reviewed commit: `ee0fb3c`
TZ: `docs/work/2026-07-07_frontend-migration-wave-07-main-integration/00_TZ.md`
Agent report: `docs/work/2026-07-07_frontend-migration-wave-07-main-integration/01_agent_report.md`

## Verdict

Rework is required before Wave 07 can be accepted.

The integration path itself looks correct:

- local `main` fast-forwarded from `wave-06-natal-visual-migration`;
- no merge commit was created;
- required product migration gates were reported as green;
- push was not attempted after optional full mobile e2e failed, which matches the TZ.

However, the current `main` is not clean against the required diff-check gate, and the report contains stale/incorrect audit data.

## Findings

### 1. Critical: required `git diff --check origin/main..HEAD` currently fails

Fresh architect verification found:

```bash
git diff --check origin/main..HEAD
```

Result:

```text
docs/work/2026-07-07_frontend-migration-wave-07-main-integration/01_agent_report.md:89: new blank line at EOF.
```

This blocks acceptance because the Wave 07 TZ requires a green `git diff --check origin/main..HEAD` and a green `git diff --check`.

Required fix:

- Remove the trailing blank line / whitespace problem from `01_agent_report.md`.
- Rerun both:

```bash
git diff --check origin/main..HEAD
git diff --check
```

- Record the fresh results in the report.

### 2. Important: report records the wrong diff-check command

The TZ requires:

```bash
git diff --check origin/main..HEAD
```

The report says:

```text
### `git diff --check main..HEAD`
```

That range is empty while already on `main`, so it does not prove the integration diff is whitespace-clean.

Evidence:

- `docs/work/2026-07-07_frontend-migration-wave-07-main-integration/01_agent_report.md:27`

Required fix:

- Replace that gate section with `git diff --check origin/main..HEAD`.
- Include the actual rerun result after fixing whitespace.

### 3. Important: report commit SHA is stale placeholder text

The callback and git history identify the report commit as `ee0fb3c`, but the report says:

```text
Commit `4166c21` (to be generated)
```

Evidence:

- `docs/work/2026-07-07_frontend-migration-wave-07-main-integration/01_agent_report.md:87`
- `git log --oneline -1` returned `ee0fb3c`

Required fix:

- Update the report self-check to record the actual original report commit `ee0fb3c`.
- Add a `Rework 01` section with the new rework commit SHA and exact rerun gates.

### 4. Important: optional full mobile e2e failure summary is too vague

The report says optional full mobile e2e failed due to "real auth flow flakiness", but the artifacts show multiple concrete failures:

- `edge-cases.spec.ts` — onboarding network-error expectation did not match the rendered state;
- `edge-cases.spec.ts` — calendar day click did not navigate from `/calendar`;
- `edge-cases.spec.ts` — reset page timed out even though the done state was visible;
- `locked-features.spec.ts` — `/readings` navigation was interrupted by `/day/today`;
- optional run also produced WebKit/browser channel-closed artifacts around mock-visual calendar.

Required fix:

- Update the optional e2e section with these exact failed test names.
- Keep the distinction clear: required mock-visual mobile gate passed; optional full mobile e2e failed.
- Do not claim the optional failure is only auth flakiness.

## Fresh Verification

Architect ran:

```bash
git status --short --branch
```

Result:

- branch: `main`;
- ahead of `origin/main` by 38 commits;
- no uncommitted tracked files;
- known unrelated untracked files remain: `.grace/`, `grace.db`, `skills/`, `docs/superpowers/plans/2026-07-05-fix-day-route-auth-build.md`.

```bash
git diff --check origin/main..HEAD
```

Result: failed with `new blank line at EOF` in `01_agent_report.md`.

Because a required gate is already red, I did not rerun the full required suite before requesting rework.

## Rework

Rework instructions are in:

```text
docs/work/2026-07-07_frontend-migration-wave-07-main-integration/03_rework_01_TZ.md
```
