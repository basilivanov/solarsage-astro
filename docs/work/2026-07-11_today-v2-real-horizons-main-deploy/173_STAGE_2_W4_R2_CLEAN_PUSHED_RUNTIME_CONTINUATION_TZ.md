# Stage 2.W4.R2 — clean pushed RC runtime continuation

Дата: `2026-07-13`

Branch/base: `preview/solarsage-v2-human-first-navigator-ux` /
`dc1af73a1094b09cc938304b739a11ce17cd8508`.

Parents:

- `170_STAGE_2_W4_FINAL_RELEASE_CANDIDATE_TZ.md`;
- `172_STAGE_2_W4_R1_ARCH_ACCEPTANCE_COMMIT_PUSH_TZ.md`.

Статус: **AUTHORIZED CONTINUATION OF W4 SECTIONS 12–17 — NO PRODUCT EDIT, NO COMMIT/PUSH, NO MAIN/DEPLOY**

Работай лично в интерактивном `tmux astro:0.0`, без subagents/delegation/
background coding/review agents.

## 1. Scope and carried-forward acceptance

W4 stopped before runtime because one frontend GRACE discipline test exposed a
missing comment declaration. R1 repaired and pushed exactly one comment line.
No API, sidecar, contract, runtime, build or payload source changed.

Architect independently accepted the following evidence on parent `42a0c5d`:

```text
contracts generate/check/compat/fixture/shared package       green
frontend type/prod/contracts/frontend/secrets guards         green except found Vitest anchor blocker
backend GRACE main 85 -> current 61, new/add-line             0 / 0
API pytest                                                   1406 PASS / 4 SKIP
sidecar pytest                                               201 PASS
API/sidecar pip check                                        PASS / PASS
preview security                                             163 PASS
API Ruff main 44 -> current 31, new/add-line                 0 / 0
API MyPy                                                     80 / 11, added-line 0
sidecar Ruff main 18 -> current 8, new/add-line              0 / 0
production runtime fixture/mock imports                      zero
```

After the one-line R1 change and clean push `dc1af73a`, coder and architect
independently confirmed:

```text
focused Vitest             2 files / 5 PASS
full Vitest                97 files / 1067 PASS
typecheck                  PASS
frontend guard             PASS / 47 paths clean
GRACE frontend selftests   11 PASS
GRACE negative             6 PASS / 0 FAIL
prod guard                 PASS
secrets guard              PASS
```

Therefore do not rerun or edit the already accepted backend/static matrix in
R2. Execute only the clean-pushed preflight and formerly skipped sections
12–17: candidate build/smoke, strict real preview E2E, Telegram HMAC and final
branch/runtime/rollback audit.

## 2. Absolute restrictions

- no tracked product/test/config/docs edit;
- do not edit this document;
- no `git add`, commit, push, switch, merge, rebase, pull, stash, amend;
- no checkout/restore/reset/clean;
- no dependency install or venv mutation;
- no service restart/reload/stop;
- no env, nginx, systemd, Docker or DB schema mutation;
- no manual uvicorn, API 8001, mock API 18092 or runtime fixture;
- no broad `pkill`/`killall`;
- no raw initData/token/cookie/UUID/profile/personal payload output;
- no main merge or production deploy.

Allowed temporary writes are only:

- `/tmp/stage2-w4-r2-*` safe snapshots/logs;
- `.next-stage2-rc` until exact candidate cleanup;
- ignored `.next-v2-real-preview` launcher output;
- ignored Playwright artifacts;
- exact `apply_patch` restoration of the closed Next-generated candidate
  references described below.

Frozen paths remain untouched:

```text
.grace/
artifacts/design/
docs/superpowers/plans/2026-07-05-fix-day-route-auth-build.md
grace.db
skills/
```

## 3. Clean pushed entry gate

Read sections 12–17 of document 170 completely, then run:

```bash
git fetch origin --prune
git branch --show-current
git rev-parse HEAD
git rev-parse '@{upstream}'
git rev-parse main
git rev-parse origin/main
git ls-remote --heads origin \
  refs/heads/main \
  refs/heads/preview/solarsage-v2-human-first-navigator-ux
git merge-base --is-ancestor origin/main HEAD
git rev-list --count origin/main..HEAD
git rev-list --count HEAD..origin/main
git diff --check origin/main...HEAD
git diff --quiet
git diff --cached --quiet
git status --short --branch
id -un
```

Require exactly:

```text
branch                         preview/solarsage-v2-human-first-navigator-ux
HEAD/upstream/remote feature   dc1af73a1094b09cc938304b739a11ce17cd8508
main/origin/remote main        c9bc36bd9a947566eddb1ffcf5617967c7412676
origin/main ancestor           yes
feature-only/main-only         59 / 0
tracked worktree/index         clean / empty
untracked                      frozen five + doc 173 only
user                           astro
```

Stop on mismatch.

## 4. Runtime/config/env/disk snapshots

Record canonical witnesses:

```bash
systemctl show \
  solarsage-sidecar.service \
  solarsage-api.service \
  solarsage-frontend.service \
  nginx.service \
  --property=Id,ActiveState,SubState,MainPID,ExecMainStartTimestamp --no-pager

ss -ltnp 'sport = :3002 or sport = :3003 or sport = :3010 or sport = :8000 or sport = :8001 or sport = :18091 or sport = :18092'

curl -fsS --max-time 5 -o /dev/null -w 'frontend=%{http_code}\n' http://127.0.0.1:3002/
curl -fsS --max-time 5 -o /dev/null -w 'api=%{http_code}\n' http://127.0.0.1:8000/api/health
curl -fsS --max-time 5 -o /dev/null -w 'sidecar=%{http_code}\n' http://127.0.0.1:18091/v1/health
```

Require:

```text
sidecar   3582982 / Sun 2026-07-12 22:02:52 MSK
API       3940721 / Mon 2026-07-13 06:54:31 MSK
frontend  916433  / Thu 2026-07-09 11:30:03 MSK
nginx     1048    / Wed 2026-07-01 15:36:15 MSK
3002/8000/18091 present and 200
3003/3010/8001/18092 absent
```

Require no tmux window `stage2-rc-candidate` or `stage2-v2-preview` and no
preview/candidate processes.

Snapshot exact SHA-256, size, mode and ownership:

```bash
sha256sum \
  next-env.d.ts tsconfig.json package.json pnpm-lock.yaml \
  packages/contracts/openapi.json \
  packages/contracts/_generated.ts \
  packages/contracts/_generated.zod.ts \
  .next-prod/BUILD_ID .env .env.production \
  > /tmp/stage2-w4-r2-start.sha256

stat -c '%n %s %a %U:%G' \
  next-env.d.ts tsconfig.json package.json pnpm-lock.yaml \
  packages/contracts/openapi.json \
  packages/contracts/_generated.ts \
  packages/contracts/_generated.zod.ts \
  .next-prod/BUILD_ID .env .env.production \
  > /tmp/stage2-w4-r2-start.stat

du -sk .next-prod .next-v2-real-preview 2>/dev/null || true
df -Pk .
```

Run the safe state-only env parser from document 170 section 4.2. It may print
only closed state labels. Require all three V2 keys `UNSET` in both `.env` and
`.env.production`. Never print env values.

## 5. Short harness preflight on clean pushed HEAD

Run:

```bash
npx vitest run __tests__/scripts/preview-v2-real.test.ts
pnpm typecheck
pnpm guardrails:prod

test -z "$(rg -n 'page\.route|context\.route|routeFromHAR|addCookies|storageState|fixture=' \
  e2e/real-v2-preview.spec.ts || true)"
```

All exit zero; forbidden-pattern scan has zero matches. Any failure blocks
runtime and must not be repaired here.

## 6. Isolated production build and candidate smoke on 3010

### 6.1 Build

Require `.next-stage2-rc` absent and 3010 free. Record `.next-prod/BUILD_ID`
hash, production PID/start, `.next-prod` KiB and available KiB immediately
before build.

Run as `astro`:

```bash
NEXT_DIST_DIR=.next-stage2-rc \
NEXT_TELEMETRY_DISABLED=1 \
pnpm build
```

Require success and normal route summary. Canonical `3002` remains 200 with
unchanged frontend PID/start throughout.

### 6.2 Closed Next-generated drift handling

Inspect:

```bash
git diff -- next-env.d.ts tsconfig.json
```

Allowed generated drift only:

- `next-env.d.ts` route import changed from `.next` to `.next-stage2-rc`;
- exact `.next-stage2-rc/types/**/*.ts` and/or
  `.next-stage2-rc/dev/types/**/*.ts` include entries appended to `tsconfig`.

If and only if drift has exactly that shape, use minimal `apply_patch` to:

1. restore exact `import "./.next/types/routes.d.ts";`;
2. remove only candidate-specific `.next-stage2-rc` includes;
3. preserve all other bytes/order/real-preview includes;
4. prove starting hashes/modes and zero tracked diff.

No copy, checkout, restore or reset. Any other drift is a blocker.

### 6.3 Rollback-space proof

With both dist trees present:

```bash
du -sk .next-prod .next-stage2-rc
df -Pk .
sha256sum .next-prod/BUILD_ID
```

Record `prod_kib`, `candidate_kib`, `available_kib`. Require available KiB is
at least candidate KiB, production BUILD_ID unchanged and canonical 3002
healthy.

### 6.4 Managed candidate

Create exactly one temporary tmux runtime window:

```bash
tmux new-window -d -t astro: -n stage2-rc-candidate \
  'cd /opt/solarsage-astro && exec env NODE_ENV=production NEXT_DIST_DIR=.next-stage2-rc NEXT_TELEMETRY_DISABLED=1 pnpm exec next start --hostname 127.0.0.1 --port 3010'
```

Wait bounded up to 60 seconds. Require exact one 3010 listener descended from
that window and HTTP 200:

```bash
curl -fsS --max-time 10 -o /dev/null -w 'candidate_root=%{http_code}\n' \
  http://127.0.0.1:3010/
curl -fsS --max-time 10 -o /dev/null -w 'candidate_api=%{http_code}\n' \
  http://127.0.0.1:3010/api/health
curl -fsS --max-time 10 -o /dev/null -w 'candidate_day=%{http_code}\n' \
  'http://127.0.0.1:3010/day/2026-07-08?why=1'
```

All 200. No 3003/8001/18092.

### 6.5 Exact shutdown and dist cleanup

Send one `C-c` to `astro:stage2-rc-candidate.0`; wait bounded up to 15 seconds.
If only the idle exact window remains, kill only that window. Prove 3010 and
its owned descendants absent.

Only after size evidence and shutdown remove exactly:

```bash
rm -rf -- .next-stage2-rc
```

Prove candidate dist/window/listener absent, production BUILD_ID/PID unchanged
and tracked config clean.

## 7. Strict real V2 preview on 3003

### 7.1 Start

Reconfirm canonical API/sidecar health 200, 3003 free and no launcher process.
Create exactly one temporary runtime window:

```bash
tmux new-window -d -t astro: -n stage2-v2-preview \
  'cd /opt/solarsage-astro && exec pnpm preview:v2:real'
```

Wait bounded up to 90 seconds for exact labels:

```text
[preview:v2:real] Real API: http://127.0.0.1:8000
[preview:v2:real] http://127.0.0.1:3003/day/2026-07-08?why=1
[preview:v2:real] REAL backend preview; no fixture or mock API.
```

Require root, rewritten `/api/health` and day shell 200; one 3003 listener
owned by the exact window; 8001/18092 absent; tracked config snapshots exact
while running.

### 7.2 Strict Chromium/mobile proof

From `astro:0.0` run:

```bash
E2E_BASE_URL=http://127.0.0.1:3003 \
  pnpm exec playwright test e2e/real-v2-preview.spec.ts \
  --project=chromium \
  --project=mobile
```

Require exact `2 PASS`, no retry-dependent success, and existing strict proof
of:

```text
natural POST /api/auth/dev
exact GET /api/day/2026-07-08
today.v2.1 / frontend 3 / content 10
long / medium / fast
timing/details/actions/disclosures
12-sphere navigation/focus persistence
zero fixture/interception/mock/V1/locked/unavailable fallback
six redacted project-specific attachments
```

Do not print raw response/cookie/personal copy.

### 7.3 Exact preview shutdown

Send one `C-c` to `astro:stage2-v2-preview.0`; wait bounded up to 15 seconds.
If only the idle exact window remains, kill only that window. Prove:

```text
3003 listener/launcher/Next descendants  absent
preview window                          absent
8001/18092                              absent
tracked config snapshots                unchanged
canonical services                      unchanged
```

Do not leave review preview running.

## 8. Real Telegram HMAC transport smoke

Run only after 3003 and 3010 are absent. Reconfirm env enable flags remain
`UNSET`.

Execute the exact memory-only Python script from document 170 section 14 using
`apps/api/.venv/bin/python`. Do not invoke the generator CLI. Require safe-only
result:

```text
auth_status             200
session_cookie_present  true
profile_status          200
logout_status           204
revoked_profile_status  401
auth_dev_used           false
raw_initdata_printed     false
cookie_value_printed     false
```

No response body, UUID, cookie value, initData or bot token may be printed.
API PID/start and global flags remain unchanged.

## 9. Final immutable and branch audit

Recreate `/tmp/stage2-w4-r2-final.sha256` and `.stat` using the exact path lists
from section 4. Diff them against the starting snapshots; both diffs must be
empty.

Then run:

```bash
git fetch origin --prune
git branch --show-current
git rev-parse HEAD
git rev-parse '@{upstream}'
git rev-parse main
git rev-parse origin/main
git ls-remote --heads origin \
  refs/heads/main \
  refs/heads/preview/solarsage-v2-human-first-navigator-ux
git merge-base --is-ancestor origin/main HEAD
git rev-list --count origin/main..HEAD
git rev-list --count HEAD..origin/main
git diff --check origin/main...HEAD
git diff --check
git diff --quiet
git diff --cached --quiet
git status --short --branch

systemctl show \
  solarsage-sidecar.service \
  solarsage-api.service \
  solarsage-frontend.service \
  nginx.service \
  --property=Id,ActiveState,SubState,MainPID,ExecMainStartTimestamp --no-pager

ss -ltnp 'sport = :3002 or sport = :3003 or sport = :3010 or sport = :8000 or sport = :8001 or sport = :18091 or sport = :18092'
test ! -e .next-stage2-rc
sha256sum .next-prod/BUILD_ID
du -sk .next-prod
df -Pk .
```

Require:

```text
HEAD/upstream/remote feature   dc1af73a... equal
main/origin/remote main        c9bc36b... unchanged
topology                       59 / 0
tracked worktree/index         clean / empty
untracked                      frozen five + doc 173
temporary windows/processes    absent
3003/3010/8001/18092           absent
3002/8000/18091                present and healthy
canonical PID/start            exact task-start values
candidate dist                 absent
production BUILD_ID            unchanged
tracked/config/contracts/env   exact starting hashes/modes
global V2 enable flags         UNSET unchanged
rollback space                 available_kib >= measured candidate_kib
commit/push/main/deploy         not performed
```

## 10. Failure policy

Any non-zero command or snapshot/ref/runtime mismatch in R2 is a hard blocker.
Do not edit code/config to fix it. Cleanly stop only an exact owned temporary
window/process, preserve safe evidence and return:

```text
BLOCKED_STAGE_2_W4_R2_RUNTIME_CONTINUATION
```

with failed command, safe status/count and cleanup state.

## 11. Required success callback and stop

```text
READY_STAGE_2_RELEASE_CANDIDATE_FOR_MAIN
base_head: dc1af73a1094b09cc938304b739a11ce17cd8508
feature_local_tracking_remote: EQUAL
main_origin_remote: c9bc36bd9a947566eddb1ffcf5617967c7412676_UNCHANGED
topology: ORIGIN_MAIN_ANCESTOR_FEATURE_59_0
carried_contracts: GENERATE_DIFF_0_CHECK_110_COMPAT_16_0_FIXTURE_PASS_PYCONTRACTS_44
carried_frontend: VITEST_97_1067_TYPECHECK_AND_GUARDS_PASS
carried_backend: API_1406_4_SIDECAR_201_PIP_PASS
carried_security_static: PREVIEW_163_RUFF_MYPY_GRACE_NEW_LINES_ZERO_NO_RUNTIME_FIXTURES
launcher_unit: PASS
isolated_build: PASS_.next-stage2-rc
candidate_smoke_3010: ROOT_API_DAY_200
candidate_cleanup: 3010_AND_DIST_ABSENT
rollback_space: PASS_<prod_kib>_<candidate_kib>_<available_kib>
real_preview_e2e: 2_PASS_CHROMIUM_MOBILE
real_preview_identity: TODAY_V2_1_FRONTEND_3_CONTENT_10
real_preview_horizons: LONG_MEDIUM_FAST
real_preview_fixture_interception_mock: ZERO
real_preview_cleanup: 3003_AND_DESCENDANTS_ABSENT
telegram_hmac: AUTH_200_COOKIE_PROFILE_200_LOGOUT_204_REVOKED_401
telegram_auth_dev_in_hmac: NOT_USED
global_v2_flags: UNSET_UNCHANGED
tracked_config_contracts_env_build_id: EXACT_STARTING_HASHES_MODES
tracked_worktree: CLEAN
index: EMPTY
frozen_untracked: PRESERVED
runtime_services: UNCHANGED_HEALTHY
ports: 3003_3010_8001_18092_ABSENT
commit_push: NOT_PERFORMED
main_merge: NOT_STARTED
production_deploy: NOT_STARTED
```

Then stop for architect review. Do not proceed to main.
