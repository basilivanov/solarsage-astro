# Stage 1.W4.R5 — await smooth sphere navigation, commit/push and retry real preview

Дата: `2026-07-13`
Ветка: `preview/solarsage-v2-human-first-navigator-ux`
Accepted pushed base: `8f529bb6cc979c7ba19d3c43f9c8e2fc2753a9d1`
API runtime: PID `3940721`, started `Mon 2026-07-13 06:54:31 MSK`

Статус: **AUTHORIZED TEST-RACE CORRECTION + COMMIT/PUSH + ONE STRICT PREVIEW RETRY**

## 1. Proven failure

The first accepted runtime attempt proved before failure, in both projects:

```text
auth/day transport = 200/200
wire schema = valid
versions = today.v2.1 / 3 / 10
access = full with all commercial metadata null
horizons = long / medium / fast
today-screen = ready
access-card = absent
three horizon disclosures = expanded with correct ARIA
sphere row = selected + expanded + status preserved + focused
details = visible and matched to sphere/status
```

Both projects then failed only at:

```text
e2e/real-v2-preview.spec.ts:247
expect(rowBox.y + rowBox.height).toBeGreaterThan(0)
chromium received -2213.625
mobile received -2529.125
```

The production handler intentionally performs:

```ts
row.scrollIntoView({ behavior: "smooth", block: "center" })
row.focus({ preventScroll: true })
```

The strict test currently reads `boundingBox()` immediately after selection,
focus and details assertions. Those assertions do not wait for the asynchronous
smooth-scroll animation. Failure video/screenshots show the page mid-animation:
desktop is still in the Why section and mobile is between long document regions.

Architect verdict: this is an E2E timing race, not a product navigation defect.
Do not change the production scroll/focus behavior.

## 2. Exact edit scope

Coder may edit only:

```text
e2e/real-v2-preview.spec.ts
```

Architect-owned document 125 must remain byte-identical and may only be staged
for its exact corrective commit.

No backend/frontend/component/launcher/config/generated/tooling edit. No API,
sidecar, frontend or nginx restart/reload.

## 3. Required E2E correction

In `SPHERE_NAVIGATION` keep all existing assertions literal:

- chip visible and sphere key closed-enum validation;
- target row initial status;
- selected=true;
- aria-expanded=true;
- status unchanged;
- target row focused;
- details visible and exact key/status;
- real project viewport exists;
- explicit final bounding-box bounds;
- repeated same-key click preserves selection/expanded/focus/status/details.

Correct only the smooth-scroll race:

1. after the first click and semantic/focus/details assertions, before reading
   `boundingBox()`, add an auto-retrying Playwright assertion:

```ts
await expect(targetRow).toBeInViewport({ ratio: 0.5 })
```

2. retain the existing explicit `viewportSize`, `boundingBox`, `y + height > 0`
   and `y < viewport.height` assertions after that retrying assertion;
3. after the repeated same-key click and its semantic/focus/details assertions,
   add the same `toBeInViewport({ ratio: 0.5 })` proof so repeat navigation also
   waits for and proves completed smooth scrolling;
4. update the nearby module invariant/map wording only if required to say the
   viewport proof is auto-retrying across smooth-scroll completion.

Forbidden:

- `waitForTimeout`, arbitrary sleep or fixed delay;
- increasing global/test timeout to hide the race;
- changing `behavior: "smooth"` to `auto`/`instant`;
- removing bounding-box, focus, selection, status, repeated-click or viewport
  assertions;
- using `scrollIntoViewIfNeeded()` from the test to manufacture success;
- test route interception, fixture, mock, cookie seeding or alternate payload;
- relaxing ratio below 0.5;
- retrying with a second preview after a runtime failure.

## 4. Static/focused gates

Before commit:

```bash
git diff --check
npx vitest run \
  __tests__/components/TodayScreen.v2-downstream.test.tsx \
  __tests__/scripts/preview-v2-real.test.ts
pnpm typecheck
pnpm guardrails:prod
```

Required exact known counts:

```text
TodayScreen.v2-downstream = 39 passed
preview-v2-real launcher = 31 passed
total focused = 70 passed
typecheck = PASS
prod guard = PASS
```

Static proof:

```bash
rg -n 'waitForTimeout|setTimeout|scrollIntoViewIfNeeded|page\.route|context\.route|fixture=' \
  e2e/real-v2-preview.spec.ts
```

Expected zero matches. Prove exactly two occurrences of:

```text
toBeInViewport({ ratio: 0.5 })
```

## 5. Exact corrective commit and push

Preflight:

- branch/HEAD/tracking/remote all equal pushed base `8f529bb...`;
- tracked tree/index clean before edit;
- only five frozen unrelated untracked paths plus architect doc 125;
- API/sidecar/frontend/nginx active;
- 3003/8001/18092 absent;
- no `v2-preview` window/process.

Stage only:

```text
e2e/real-v2-preview.spec.ts
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/125_STAGE_1_W4_R5_AWAIT_SMOOTH_SPHERE_NAVIGATION_AND_RETRY_PREVIEW_TZ.md
```

Commit:

```text
test(preview): await smooth sphere navigation
```

Push normally to the same preview branch, never force. Verify HEAD, tracking and
remote equality. No API restart: runtime product/backend code is unchanged.

## 6. Clean prior ignored evidence

Before retry, remove only stale ignored Playwright outputs from the failed run:

```text
test-results/
playwright-report/
```

Do not remove any other ignored/untracked path. Confirm tracked tree/index clean
and frozen unrelated paths unchanged.

## 7. One managed preview retry

Repeat launcher preflight and config snapshots from 124. Create exactly one:

```bash
tmux new-window -d -t astro: -n v2-preview \
  'cd /opt/solarsage-astro && exec pnpm preview:v2:real'
```

Require exact three readiness labels and 200/200/200 for root/day/API health.
Prove one managed 3003 tree, no 8001/18092.

Run once:

```bash
E2E_BASE_URL=http://127.0.0.1:3003 \
  pnpm exec playwright test e2e/real-v2-preview.spec.ts \
    --project=chromium --project=mobile
```

Required exact result:

```text
2 passed / 0 failed / 0 skipped
```

Validate all six redacted attachments per 117/124. On failure, use the bounded
single-C-c cleanup and stop; no second retry, no code edit during runtime.

On success leave `astro:v2-preview.0` and review URL running.

## 8. Final callback

```text
READY_STAGE_1_W4_R5_REAL_PREVIEW
base_commits: 1b22a5a / 8f529bb
corrective_commit: <sha> test(preview): await smooth sphere navigation
push: HEAD_TRACKING_REMOTE_EQUAL
api_runtime: 3940721 / Mon 2026-07-13 06:54:31 MSK UNCHANGED
sidecar_frontend_nginx: UNCHANGED
focused_tests: 70 PASS
typecheck: PASS
prod_guard: PASS
smooth_scroll_proof: TWO_AUTO_RETRY_VIEWPORT_ASSERTIONS_RATIO_0_5
launcher_target: astro:v2-preview.0
launcher_labels: EXACT_3
root_day_health_3003: 200_200_200
managed_preview_tree: PASS_SINGLE_NO_ORPHAN
strict_e2e: 2_PASS_0_FAIL_0_SKIP
auth_day_transport_each_project: 200_200
versions_each_project: TODAY_V2_1_FRONTEND_3_CONTENT_10
access_each_project: FULL_NULL_COMMERCIAL_METADATA
horizons_each_project: LONG_MEDIUM_FAST
sphere_navigation_each_project: SELECTED_EXPANDED_FOCUSED_IN_VIEWPORT_REPEAT
route_interception_fixture_mock_18092: ZERO_ABSENT
artifacts: SIX_REDACTED_EXACT
config_snapshots: EXACT_UNCHANGED
tracked_worktree: CLEAN
index: EMPTY
untracked_scope: FROZEN_UNRELATED_ONLY
journal_runtime_errors_5xx: ABSENT
journal_privacy: PASS
review_url: http://127.0.0.1:3003/day/2026-07-08?why=1
review_url_state: RUNNING_LEFT_MANAGED
```

Then stop. Do not merge to main or restart production frontend.
