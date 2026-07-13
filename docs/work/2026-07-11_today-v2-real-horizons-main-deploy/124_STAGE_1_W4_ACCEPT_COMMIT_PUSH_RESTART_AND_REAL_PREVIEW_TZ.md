# Stage 1.W4 — accepted implementation: commit, push, controlled API restart and real preview

Дата: `2026-07-13`
Ветка: `preview/solarsage-v2-human-first-navigator-ux`
Accepted base: `7d37acbaa31118a8545987a39a5fabe18fbb6e32`
Runtime parent: `117_STAGE_1_W4_STRICT_REAL_PREVIEW_EXECUTION_TZ.md`

Статус: **ARCHITECT ACCEPTED — AUTHORIZED COMMIT/PUSH + API RESTART + STRICT REAL PREVIEW**

## 1. Architect acceptance

The exact nine-path implementation/repair wave is accepted after independent
review and repeated gates:

```text
request-scoped preview access: fail-closed and isolated
focused backend: 83 passed
focused frontend: 121 passed
full backend: 1405 passed, 4 skipped
full frontend: 1067 passed
typecheck: PASS
contracts generate diff: ZERO
contracts check: PASS (110 tests)
isolated build: PASS
GRACE linter self-tests: 11 passed
GRACE negative after repair: 6 pass / 0 fail
frontend ESLint baseline: 64 errors / 5 warnings, zero W4 diff-hunk regression
active GRACE slice baseline: 49 violations / 47 files, zero W4 intersection
```

No product/test/code edit is authorized in this execution wave. Only exact git
staging/commits/push and controlled runtime operations below are allowed.

This document supersedes the no-commit/no-restart clauses of 117 only after the
preflight and exact staging checks below pass. All no-fixture/no-second-API/no-
global-flag/no-production-frontend restrictions remain literal.

## 2. Preflight before staging

From `/opt/solarsage-astro`:

1. confirm branch and local/tracking base are `7d37acb...`;
2. `git fetch origin` without merge/rebase;
3. confirm remote branch still equals `7d37acb...` using both tracking ref and
   `git ls-remote`;
4. confirm index empty and `git diff --check` clean;
5. confirm exact nine tracked implementation/repair paths and exact architect
   docs 117–124 as the only task untracked docs;
6. confirm frozen unrelated paths are untouched;
7. confirm 3003/8001/18092 absent and no `v2-preview` window;
8. record current service PID/start witnesses.

If remote branch changed, stop. No pull/rebase/force push.

## 3. Exact commit A — Today preview access

Stage only these thirteen paths:

```text
apps/api/app/services/today_preview_access.py
apps/api/app/api/day.py
apps/api/tests/test_today_preview_access.py
lib/adapters/today-payload.ts
__tests__/lib/adapt-payload.test.ts
components/today/today-screen.tsx
__tests__/components/TodayScreen.test.tsx
e2e/real-v2-preview.spec.ts
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/117_STAGE_1_W4_STRICT_REAL_PREVIEW_EXECUTION_TZ.md
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/118_STAGE_1_W4_ARCH_ERRATA_NEXT_ENV_MTIME_NON_CONTRACT_TZ.md
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/119_STAGE_1_W4_R1_REQUEST_SCOPED_FULL_ACCESS_PREVIEW_TZ.md
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/120_STAGE_1_W4_R1_ARCH_ERRATA_REPO_ROOT_FULL_API_TZ.md
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/121_STAGE_1_W4_R2_ARCH_REVIEW_AND_BASELINE_LINT_CONTINUATION_TZ.md
```

Use explicit path arguments; never `git add .`, `-A` or wildcard staging.

Before commit prove staged path set equals the list exactly and unstaged tracked
diff is only `scripts/grace_front_lint.py`. Then commit:

```text
feat(preview): grant request-scoped access to local v2
```

Record SHA.

## 4. Exact commit B — guardrail repair and acceptance docs

Stage only:

```text
scripts/grace_front_lint.py
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/122_STAGE_1_W4_R3_REPAIR_DUPLICATED_GRACE_FRONT_LINTER_TZ.md
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/123_STAGE_1_W4_R4_CLASSIFY_GRACE_SLICE_BASELINE_AND_FINISH_GATES_TZ.md
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/124_STAGE_1_W4_ACCEPT_COMMIT_PUSH_RESTART_AND_REAL_PREVIEW_TZ.md
```

Before commit prove staged set equals exactly four paths and there is no
unstaged tracked diff. Then commit:

```text
fix(guardrails): repair duplicated frontend grace linter
```

Record SHA. After commit B, tracked tree and index must be clean; only the five
frozen unrelated untracked roots/files remain.

## 5. Push

Push normally, never force:

```bash
git push origin HEAD:refs/heads/preview/solarsage-v2-human-first-navigator-ux
```

Verify local HEAD, tracking ref and `git ls-remote` all equal commit B SHA.
If push fails or remote advances, stop without rewriting history.

## 6. Controlled API restart only

Backend route code changed, so restart only the canonical API:

```bash
sudo -n systemctl restart solarsage-api.service
```

Forbidden:

- manual uvicorn;
- API on 8001;
- sidecar/frontend/nginx restart or reload;
- production frontend build/restart on 3002;
- env/global V2 flag mutation.

Wait up to 60 seconds for:

```text
solarsage-api.service active/running
http://127.0.0.1:8000/api/health = 200
exactly one 8000 listener owned by canonical service tree
sidecar health 18091 = 200
```

API PID/start must change. Sidecar/frontend/nginx PID/start must remain exact
preflight values. Confirm 8001/18092 absent.

Inspect API journal only since the new start for traceback, critical, startup
failure and 5xx patterns. Do not print raw request bodies, cookies, Telegram
data, profile facts or dynamic personal copy.

If restart/health fails, do not start preview. Return blocked callback with safe
service evidence.

## 7. Real preview preflight

Use the now-pushed clean HEAD. Repeat the safe static launcher gates from 117:

```bash
npx vitest run __tests__/scripts/preview-v2-real.test.ts
pnpm typecheck
pnpm guardrails:prod
```

All must pass. Capture SHA/size/mode snapshots of `next-env.d.ts`,
`tsconfig.json`, `package.json`, `pnpm-lock.yaml`.

Confirm:

```text
port 3003 free
no v2-preview window
no preview-v2-real.mjs process
no next dev on 3003
canonical API 8000 and sidecar 18091 healthy
```

## 8. Start the managed preview

Create exactly one window:

```bash
tmux new-window -d -t astro: -n v2-preview \
  'cd /opt/solarsage-astro && exec pnpm preview:v2:real'
```

Wait up to 90 seconds for the exact three launcher labels from 117. Do not
create a second launcher if readiness fails.

Then require exact 200:

```text
http://127.0.0.1:3003/
http://127.0.0.1:3003/day/2026-07-08?why=1
http://127.0.0.1:3003/api/health
```

Prove one managed preview process tree, one 3003 listener, no orphan, no 8001
or 18092.

## 9. Strict desktop + mobile E2E

Run exactly in `astro:0.0` while preview stays running:

```bash
E2E_BASE_URL=http://127.0.0.1:3003 \
  pnpm exec playwright test e2e/real-v2-preview.spec.ts \
    --project=chromium --project=mobile
```

Required:

```text
2 passed / 0 failed / 0 skipped
auth/day transport = 200/200 per project
versions = today.v2.1 / 3 / 10 per project
access = full with all commercial metadata null per project
horizons = long / medium / fast per project
today-screen = ready
access-card = absent
fixture/interception/mock/18092 = absent
```

Validate the six redacted evidence attachments exactly as section 9 of 117.
Do not print response payload or personal copy.

## 10. Success/failure lifecycle

On any failure after preview creation, perform the bounded cleanup from section
11 of 117 and prove 3003 descendants absent. Do not edit code or retry with a
second preview window.

On full success:

- leave `astro:v2-preview.0` running;
- leave review URL alive;
- repeat config snapshots and prove unchanged;
- tracked worktree/index clean;
- only frozen unrelated untracked paths remain;
- production frontend/nginx and sidecar PID/start unchanged;
- API is the new controlled-restart PID;
- no lifecycle/journal privacy errors.

Review URL:

```text
http://127.0.0.1:3003/day/2026-07-08?why=1
```

## 11. Callback

```text
READY_STAGE_1_W4_ACCEPTED_REAL_PREVIEW
commit_a: <sha> feat(preview): grant request-scoped access to local v2
commit_b: <sha> fix(guardrails): repair duplicated frontend grace linter
push: HEAD_TRACKING_REMOTE_EQUAL
api_restart: PASS <old_pid> -> <new_pid> <new_start>
sidecar_frontend_nginx: UNCHANGED
launcher_unit: 31 PASS
typecheck: PASS
prod_guard: PASS
launcher_target: astro:v2-preview.0
launcher_labels: EXACT_3
root_day_health_3003: 200_200_200
managed_preview_tree: PASS_SINGLE_NO_ORPHAN
strict_e2e: 2_PASS_0_FAIL_0_SKIP
auth_day_transport_each_project: 200_200
versions_each_project: TODAY_V2_1_FRONTEND_3_CONTENT_10
access_each_project: FULL_NULL_COMMERCIAL_METADATA
horizons_each_project: LONG_MEDIUM_FAST
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

Then stop. Do not merge to main and do not restart production frontend.
