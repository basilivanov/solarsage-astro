# Stage 2.W6B — atomic production deployment with closed rollback

Дата: `2026-07-13`

Prerequisites:

- accepted main merge `57230b7b8eedb772a936726f6abf97427bc37f6a`;
- accepted main docs commit `24b453e95bd244e9628cd66a74caee24b9d70e8c`;
- accepted W6A preflight `177_STAGE_2_W6A_DEPLOY_PREFLIGHT_AND_WHEEL_PROOF_TZ.md`;
- final deployment-doc commit created by document 180 and pushed before this
  task is sent.

Статус: **PRODUCTION MUTATION AUTHORIZED ONLY AFTER EXACT FINAL-MAIN PREFLIGHT**

Работай лично в `tmux astro:0.0`, без subagents/delegation/background coding.

## 1. Goal and terminal state

Deploy the accepted main tree into the canonical production stack:

```text
one retained shared-contract wheel
  -> exact same wheel installed in sidecar/API venvs
  -> isolated production frontend candidate + 3010 smoke
  -> root-only env backup + exact two V2 flags true in .env
  -> stopped frontend + atomic old/new dist rename
  -> sidecar restart/health
  -> API restart/health/git SHA/flags
  -> frontend start/health
  -> public health smoke
  -> retained rollback env/dist/wheel
```

No product/source/test/config commit occurs in W6B. Main is already final and
must remain byte-identical throughout.

W6B exits only as:

```text
READY_STAGE_2_W6_DEPLOYED_FOR_PRODUCTION_ACCEPTANCE
```

or a blocked callback that proves automatic rollback restored the previous
production runtime.

## 2. Absolute prohibitions

- no source/test/tracked config/docs edit;
- do not edit document 178;
- no git add/commit/push/switch/merge/rebase/pull/stash;
- no force push or git history rollback;
- no systemd unit or nginx config edit;
- no daemon-reload;
- no nginx restart/reload because no nginx file changes;
- no DB migration/schema/data mutation;
- no global Python or `/opt/astro-project` mutation;
- no dependency resolver upgrade/downgrade; wheel install uses `--no-deps`;
- no `pnpm install`;
- no manual uvicorn/Next production daemon;
- no API 8001, mock 18092 or preview 3003;
- no raw env/token/cookie/initData/profile/personal payload output;
- no deletion of any pre-existing build or frozen path.

Allowed persistent production artifacts are only under one unique:

```text
/opt/solarsage-release/<STAMP>/
```

Allowed transient repo artifact is exactly `.next-release-<STAMP>` until it is
renamed to `.next-prod` or removed during rollback.

## 3. Exact final-main authorization gate

Document 180 will create one docs-only main commit with exact subject:

```text
docs(release): authorize v2 production deployment
```

Before any `/opt`, venv, build, env or service mutation run:

```bash
git fetch origin --prune
git branch --show-current
git rev-parse HEAD
git rev-parse origin/main
git ls-remote --heads origin refs/heads/main
git rev-parse HEAD^1
git log -1 --format=%s
git show --format= --name-only HEAD
git diff --quiet
git diff --cached --quiet
git diff --check
git status --short --branch
```

Require:

```text
branch                         main
HEAD/origin/remote main        one identical 40-char SHA (DEPLOY_SHA)
HEAD subject                   docs(release): authorize v2 production deployment
HEAD parent                    24b453e95bd244e9628cd66a74caee24b9d70e8c
HEAD paths                     exact docs 177,178,179,180
tracked worktree/index         clean / empty
untracked                      frozen five only
```

Also require:

```bash
git diff --exit-code 24b453e95bd244e9628cd66a74caee24b9d70e8c HEAD -- \
  ':(exclude)docs/work/2026-07-11_today-v2-real-horizons-main-deploy/177_STAGE_2_W6A_DEPLOY_PREFLIGHT_AND_WHEEL_PROOF_TZ.md' \
  ':(exclude)docs/work/2026-07-11_today-v2-real-horizons-main-deploy/178_STAGE_2_W6B_ATOMIC_PRODUCTION_DEPLOY_TZ.md' \
  ':(exclude)docs/work/2026-07-11_today-v2-real-horizons-main-deploy/179_STAGE_2_W7_PRODUCTION_ACCEPTANCE_TZ.md' \
  ':(exclude)docs/work/2026-07-11_today-v2-real-horizons-main-deploy/180_STAGE_2_W6A_ACCEPTANCE_AND_DEPLOY_DOCS_COMMIT_PUSH_TZ.md'
```

Non-doc diff from accepted main must be zero. Stop if remote main changed.

## 4. Release variables and immutable start snapshot

Generate once after gate:

```bash
DEPLOY_SHA=$(git rev-parse HEAD)
DEPLOY_SHORT=$(git rev-parse --short=12 HEAD)
MERGE_SHA=57230b7b8eedb772a936726f6abf97427bc37f6a
STAMP=$(date -u +%Y%m%dT%H%M%SZ)
RELEASE_ROOT="/opt/solarsage-release/$STAMP"
WHEEL_DIR="$RELEASE_ROOT/wheels"
ENV_DIR="$RELEASE_ROOT/env"
ENV_BACKUP="$ENV_DIR/.env.before"
FRONTEND_DIR="$RELEASE_ROOT/frontend"
EVIDENCE_DIR="$RELEASE_ROOT/evidence"
RC_DIST=".next-release-$STAMP"
ROLLBACK_DIST="$FRONTEND_DIR/next-prod.rollback"
FAILED_DIST="$FRONTEND_DIR/next-prod.failed"
```

Require all target paths absent and `RC_DIST` not equal `.next-prod`.

Record safe variables to `/tmp/stage2-w6b-vars.txt`; no secret values.

Capture before state:

```bash
RELEASE_START_UTC=$(date -u +'%Y-%m-%d %H:%M:%S UTC')

systemctl show \
  solarsage-sidecar.service \
  solarsage-api.service \
  solarsage-frontend.service \
  nginx.service \
  --property=Id,ActiveState,SubState,MainPID,ExecMainStartTimestamp --no-pager \
  > /tmp/stage2-w6b-services-before.txt

sha256sum \
  next-env.d.ts tsconfig.json package.json pnpm-lock.yaml \
  packages/contracts/openapi.json \
  packages/contracts/_generated.ts \
  packages/contracts/_generated.zod.ts \
  .next-prod/BUILD_ID .env .env.production \
  > /tmp/stage2-w6b-files-before.sha256

stat -c '%n %s %a %U:%G %d' \
  next-env.d.ts tsconfig.json package.json pnpm-lock.yaml \
  packages/contracts/openapi.json \
  packages/contracts/_generated.ts \
  packages/contracts/_generated.zod.ts \
  .next-prod .next-prod/BUILD_ID .env .env.production \
  > /tmp/stage2-w6b-files-before.stat

OLD_BUILD_ID_SHA=$(sha256sum .next-prod/BUILD_ID | awk '{print $1}')
OLD_BUILD_ID=$(tr -d '\n' < .next-prod/BUILD_ID)
OLD_PROD_KIB=$(du -sk .next-prod | awk '{print $1}')
AVAILABLE_KIB=$(df -Pk . | awk 'NR==2 {print $4}')
```

Do not print raw BUILD_ID unless it is treated only as a non-secret release
identifier. Never print env contents.

Require canonical services/DB/ports/health exactly as accepted W6A and
`sudo -n nginx -t` PASS.

Run safe env parser: both enable keys and dual-run have zero occurrences/UNSET
in `.env`; same in `.env.production`.

## 5. Create persistent release root and secure env backup

Create outside Git:

```bash
sudo -n install -d -o root -g root -m 750 "$RELEASE_ROOT"
sudo -n install -d -o astro -g astro -m 750 "$WHEEL_DIR"
sudo -n install -d -o root -g root -m 700 "$ENV_DIR"
sudo -n install -d -o astro -g astro -m 750 "$FRONTEND_DIR" "$EVIDENCE_DIR"
sudo -n install -o root -g root -m 600 .env "$ENV_BACKUP"
```

Require backup SHA equals starting `.env` SHA, backup root:root 600, original
`.env` still astro:astro 664.

Require `stat -c %d` proves repository, RC dist parent, `.next-prod` and
`FRONTEND_DIR` share the same filesystem. This guarantees rename-based swap and
rollback do not copy partial trees.

## 6. Build and retain one exact shared-contract wheel

Use one temporary source export and the persistent wheel directory:

```bash
SRC_ROOT=$(mktemp -d /tmp/stage2-w6b-src.XXXXXX)
git archive "$DEPLOY_SHA" packages/py-contracts | tar -x -C "$SRC_ROOT"

apps/solarsage/venv/bin/python -m pip wheel \
  --no-deps \
  --no-build-isolation \
  --wheel-dir "$WHEEL_DIR" \
  "$SRC_ROOT/packages/py-contracts"

rm -rf -- "$SRC_ROOT"
```

Require exactly one:

```text
solarsage_contracts-0.1.0-py3-none-any.whl
```

Set:

```bash
WHEEL=$(find "$WHEEL_DIR" -maxdepth 1 -type f -name '*.whl' -print -quit)
WHEEL_SHA256=$(sha256sum "$WHEEL" | awk '{print $1}')
WHEEL_SIZE=$(stat -c %s "$WHEEL")
chmod 640 "$WHEEL"
```

Inspect ZIP/METADATA as W6A: exact nine entries, required modules/`py.typed`, no
tests/pyc/secrets, version 0.1.0 and pydantic bound. Keep wheel through W7.

## 7. Install the exact same wheel into both canonical venvs

Record current editable facts without raw unrelated freeze output. Then:

```bash
apps/solarsage/venv/bin/python -m pip install \
  --no-deps --force-reinstall "$WHEEL"

apps/api/.venv/bin/python -m pip install \
  --no-deps --force-reinstall "$WHEEL"
```

The command argument must be the same absolute `$WHEEL` path and retained hash.

After both succeed require:

- `pip show solarsage-contracts` version 0.1.0 in both;
- no `Editable project location` in either;
- import path in each owning `site-packages/solarsage_contracts`, not repo;
- both imports expose the same public version/activation contracts;
- both `pip check` PASS;
- run `packages/py-contracts/tests/ -q` with API venv and sidecar venv, each
  `44 PASS`, without `PYTHONPATH=packages/py-contracts`, proving installed
  wheel use.

If either install/import/test/check fails before frontend/env mutation:

1. reinstall editable contracts in both exact venvs with `--no-deps
   --force-reinstall -e /opt/solarsage-astro/packages/py-contracts`;
2. `pip check` both;
3. prove services remained unchanged;
4. return blocked; do not build/swap/restart.

## 8. Build isolated production frontend candidate

Require RC path absent and production frontend still serving old BUILD_ID.

Run as astro:

```bash
NEXT_DIST_DIR="$RC_DIST" \
NEXT_TELEMETRY_DISABLED=1 \
pnpm build
```

Require build success, candidate owner astro:astro, candidate BUILD_ID present,
production 3002/PID/old BUILD_ID unchanged.

Inspect only `next-env.d.ts` and `tsconfig.json` drift. Allowed Next-generated
drift is limited to RC_DIST route import and exact RC_DIST type globs. Restore
only that closed drift through minimal `apply_patch` as in W4; no copy/checkout/
restore/reset. Any other tracked drift triggers pre-swap failure and wheel
rollback to editable.

Record candidate KiB, BUILD_ID SHA and available KiB. Require available KiB is
at least candidate KiB plus old prod KiB.

## 9. Managed 3010 candidate smoke, keep candidate for swap

Create exact temporary window:

```bash
tmux new-window -d -t astro: -n stage2-w6b-candidate \
  "cd /opt/solarsage-astro && exec env NODE_ENV=production NEXT_DIST_DIR=$RC_DIST NEXT_TELEMETRY_DISABLED=1 pnpm exec next start --hostname 127.0.0.1 --port 3010"
```

Wait bounded 60 seconds. Require one owned listener and 200 for root,
`/api/health`, `/day/2026-07-08?why=1`. API still runs pre-restart and flags
remain false/unset; this smoke validates build transport, not V2 selection.

Send one C-c, wait up to 15 seconds, remove only exact idle window, prove 3010
and descendants absent. Do not remove RC_DIST after success.

If smoke fails: stop candidate, remove exact RC_DIST, reinstall editable
contracts in both venvs, verify old production health and return blocked.

## 10. Exact `.env` two-line rollout

Reconfirm backup SHA and current `.env` SHA equal start; enable keys still
absent; `.env.production` hash unchanged.

Use `apply_patch` only. Append exactly once at EOF, after existing final env
entry:

```text
SOLARSAGE_V2_ENABLED=true
SOLARSAGE_V2_FRONTEND_ENABLED=true
```

Do not add/change any other line/comment/blank section. Preserve mode/owner
`664 astro:astro`.

Use a safe comparison parser against `$ENV_BACKUP`; it may output only:

```text
added_keys: SOLARSAGE_V2_ENABLED,SOLARSAGE_V2_FRONTEND_ENABLED
added_states: TRUE,TRUE
removed_keys: 0
changed_existing_keys: 0
duplicate_keys: 0
```

Validate from `apps/api` through `Settings` and print only both booleans; both
must be True. `.env.production` remains byte-exact.

If env validation fails, restore `.env` immediately from root backup with:

```bash
sudo -n install -o astro -g astro -m 664 "$ENV_BACKUP" /opt/solarsage-astro/.env
```

then remove candidate/reinstall editable contracts and return blocked.

## 11. Stop frontend and atomically swap build

Record old frontend PID/start again. Then:

```bash
sudo -n systemctl stop solarsage-frontend.service
```

Wait bounded up to 30 seconds for inactive and port 3002 absent. Sidecar/API/
nginx remain active.

Require ROLLBACK_DIST and FAILED_DIST absent. Perform same-filesystem renames:

```bash
mv -- .next-prod "$ROLLBACK_DIST"
mv -- "$RC_DIST" .next-prod
```

Require:

- new `.next-prod` owner/group astro:astro and expected candidate BUILD_ID;
- rollback dist owner/group astro:astro and exact old BUILD_ID hash;
- RC_DIST absent;
- no partial/copy artifact;
- frontend remains stopped until sidecar/API are healthy.

If second rename fails, immediately rename rollback dist back to `.next-prod`,
restore env, reinstall editable contracts, restart old services and return
blocked.

## 12. Dependency-safe restart sequence

Record one UTC timestamp immediately before each exact operation.

### 12.1 Sidecar

```bash
sudo -n systemctl restart solarsage-sidecar.service
```

Wait bounded max 120 seconds for active/running, new PID/start, exactly one
18091 listener and `/v1/health` 200. No 18092.

### 12.2 API

Only after sidecar passes:

```bash
sudo -n systemctl restart solarsage-api.service
```

Wait bounded max 120 seconds for active/running, new PID/start, exactly one
8000 listener and `/api/health` 200. Require health `git_sha` equals first seven
characters of `$DEPLOY_SHA` and status/version shape remains valid.

Re-run safe Settings parser: both flags True. No 8001.

### 12.3 Frontend

Only after API passes:

```bash
sudo -n systemctl start solarsage-frontend.service
```

Wait bounded max 120 seconds for active/running, new PID/start, exactly one
3002 listener and root 200. Require served BUILD_ID is new `.next-prod` tree.

### 12.4 Nginx

Do not restart/reload nginx. Require original PID/start unchanged,
`sudo nginx -t` still PASS, loopback nginx `/api/health` and `/` 200, public
HTTPS `/api/health` and `/` 200.

## 13. Automatic rollback on any post-env/swap/restart failure

Any failure in sections 10–12 triggers immediate rollback; do not wait for
architect input.

Closed rollback:

1. stop only frontend service if running;
2. if new `.next-prod` exists, rename it to `$FAILED_DIST` (path must be absent);
3. if `$ROLLBACK_DIST` exists, rename it back to `.next-prod`;
4. restore `.env` from `$ENV_BACKUP` as astro:astro mode 664;
5. reinstall editable contracts in both exact venvs using the W6A commands;
6. `pip check` both;
7. restart sidecar; wait 18091 health;
8. restart API; wait 8000 health and flags false/unset;
9. start frontend; wait 3002 old root/BUILD_ID;
10. prove nginx unchanged, public health restored, temporary ports absent;
11. preserve release root/wheel/failed dist for diagnosis;
12. return `BLOCKED_STAGE_2_W6B_ROLLED_BACK` with safe reason/class.

Never reset/revert/force-push main during runtime rollback.

## 14. Post-deploy structural smoke and journal audit

After successful starts require all:

```text
sidecar 18091 health 200 / new PID
API 8000 health 200 / git_sha DEPLOY_SHORT7 / new PID
frontend 3002 root 200 / new BUILD_ID / new PID
nginx original PID / loopback and public root+API 200
DB 5433 accepting
3003/3010/8001/18092 absent
flags True/True from Settings
wheel non-editable same path/hash source in both venvs
```

Inspect journals only since each new start. Do not dump raw journals. Produce
safe counts for traceback, critical, startup failure, unhandled exception and
5xx patterns. Require zero new startup/runtime loop. Known unrelated nginx
warnings remain outside changed services.

Do not run real personal payload/browser proof here; W7 owns that immediately
after W6B acceptance.

## 15. Final integrity and retained rollback assets

Require:

- `git branch --show-current` main;
- local/origin/remote main equal DEPLOY_SHA;
- tracked worktree/index clean;
- only five frozen untracked paths;
- `next-env.d.ts`, `tsconfig.json`, package/lock/contracts hashes/modes equal
  starting snapshots;
- `.env.production` exact starting hash/mode;
- `.env` differs from root backup only by exact two true lines;
- release root outside Git retained;
- wheel root `$WHEEL` retained and hash recorded;
- root-only env backup retained;
- rollback dist retained with old BUILD_ID;
- new `.next-prod` present with candidate BUILD_ID;
- RC_DIST and temporary tmux window absent;
- no service outside sidecar/API/frontend changed; nginx PID unchanged.

Do not delete rollback assets before W7 final acceptance and explicit later
cleanup authorization.

## 16. Callback and stop

```text
READY_STAGE_2_W6_DEPLOYED_FOR_PRODUCTION_ACCEPTANCE
deploy_sha: <40-char final main SHA>
merge_sha: 57230b7b8eedb772a936726f6abf97427bc37f6a
stamp: <UTC stamp>
release_root: /opt/solarsage-release/<stamp>
wheel: <absolute path>
wheel_sha256: <sha256>
wheel_size: <bytes>
wheel_installs: API_NONEDITABLE_SIDECAR_NONEDITABLE_SAME_WHEEL
wheel_tests: API_44_SIDECAR_44
pip_check: API_PASS_SIDECAR_PASS
env_backup: <absolute root-owned path>
env_delta: EXACT_TWO_TRUE_LINES
env_production: UNCHANGED
flags: SOLARSAGE_V2_ENABLED_TRUE_FRONTEND_TRUE_DUAL_DEFAULT
candidate_build: PASS_<kib>_<build-id-sha>
candidate_smoke_3010: ROOT_API_DAY_200
rollback_dist: <absolute path>
rollback_build_id_sha: <sha256>
new_build_id_sha: <sha256>
sidecar_pid: <old>_TO_<new>
api_pid: <old>_TO_<new>
frontend_pid: <old-mainpid>_TO_<new-mainpid>
nginx_pid: 1048_UNCHANGED
health: SIDECAR_API_FRONTEND_NGINX_PUBLIC_PASS
api_git_sha: <short deploy SHA>
journal_startup_errors: ZERO
ports: 18091_8000_3002_PRESENT_3003_3010_8001_18092_ABSENT
tracked_worktree: CLEAN
index: EMPTY
frozen_untracked: PRESERVED
rollback_assets: ENV_WHEEL_OLD_DIST_RETAINED
rollback_command: RESTORE_ENV_OLD_DIST_EDITABLE_CONTRACTS_RESTART_ORDER
production_acceptance: NOT_STARTED
```

Then stop. Do not delete rollback assets or start W7 without architect review.
