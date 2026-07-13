# Stage 2.W4 — final release candidate before main

Дата: `2026-07-13`

Branch/base: `preview/solarsage-v2-human-first-navigator-ux` /
`42a0c5dba7d476b156e0ff17d4fdccb5a22aaa93`.

Parent master:
`127_STAGE_2_CORRECTIVE_RELEASE_MAIN_DEPLOY_WAVE_MASTER.md`.

Accepted predecessor:
`169_STAGE_2_W3C_ARCH_ACCEPTANCE_COMMIT_PUSH_TZ.md`.

Статус: **AUTHORIZED FINAL RC PROOF — NO PRODUCT EDITS, NO COMMIT/PUSH, NO MAIN/DEPLOY**

Исполнитель работает лично в интерактивном `tmux astro:0.0`. Запрещены
subagents, delegation, `delegate_*`, background coding/review agents и
использование их результатов как evidence.

## 1. Goal and exit contract

This is the last feature-branch proof before a separately authorized merge to
`main`. Do not implement or clean up code in this wave. Prove the exact pushed
branch as it exists.

The wave must establish all of the following:

1. contract generation is idempotent and all contract/shared-package gates pass;
2. full frontend tests, typecheck and production/contract/frontend/secrets
   guards pass;
3. full API and sidecar test suites and both venv `pip check` commands pass;
4. feature-introduced Ruff, MyPy and GRACE regressions are zero while the exact
   pre-existing legacy baselines remain classified and do not grow;
5. production runtime cannot import/use fixtures or request-scoped preview
   access accidentally;
6. an isolated production build succeeds and serves from a managed candidate
   on loopback `3010` while canonical production `3002` is untouched;
7. strict Chromium and mobile real V2 preview passes on `3003` with no request
   interception, fixture or mock API;
8. real Telegram HMAC auth, session-cookie transport, authenticated profile and
   logout/revocation work against canonical API `8000`, without `/api/auth/dev`
   and without enabling global V2;
9. feature/main topology, tracked cleanliness, canonical services and rollback
   disk capacity remain valid.

Only if every hard gate and every classified-baseline invariant below holds,
return:

```text
READY_STAGE_2_RELEASE_CANDIDATE_FOR_MAIN
```

Do not commit or push document 170 in this wave. Architect review and an exact
acceptance-doc commit will be separate.

## 2. Absolute restrictions

No tracked repository edit is authorized, including source, tests, config,
contracts, generated files or this document. The only allowed temporary writes
are:

- `/tmp/stage2-w4-*` logs, parsers, snapshots and extracted `origin/main` files;
- generated contract execution that must leave exact zero tracked diff;
- ignored test artifacts under existing Playwright/Vitest locations;
- isolated build directory `.next-stage2-rc`, removed after candidate smoke;
- existing ignored `.next-v2-real-preview` runtime output owned by the launcher;
- exact operational `apply_patch` restoration of recognized Next-generated
  candidate references in `next-env.d.ts`/`tsconfig.json`, as specified in
  section 11. This is not a product change.

Forbidden:

- `git add`, commit, push, switch, merge, rebase, pull, stash, amend;
- `git checkout --`, `git restore`, `git reset`, `git clean`;
- source/config/test/guardrail correction after a failed gate;
- formatter, Ruff `--fix`, ESLint `--fix`, generated-diff acceptance;
- dependency install or venv mutation;
- manual uvicorn, API `8001`, mock server `18092`, runtime fixture API;
- env, systemd, nginx, Docker, DB schema or canonical build mutation;
- service restart/reload/stop;
- broad `pkill`, `killall` or killing a process not proven to be owned by the
  exact temporary tmux window created in this task;
- printing raw Telegram initData, bot token, cookie/session value, UUID,
  profile body, personal payload, API response copy or secret env values.

Never touch/stage/delete the five frozen unrelated paths:

```text
.grace/
artifacts/design/
docs/superpowers/plans/2026-07-05-fix-day-route-auth-build.md
grace.db
skills/
```

If a command changes a tracked file unexpectedly, stop subsequent runtime
steps, preserve the diff and report it. Never hide it with a destructive Git
command.

## 3. Entry gate

Read this file and documents `127`, `168`, `169` completely before executing.
Then run from `/opt/solarsage-astro`:

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
git merge-base origin/main HEAD
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
HEAD/upstream/remote feature   42a0c5dba7d476b156e0ff17d4fdccb5a22aaa93
main/origin-main/remote main   c9bc36bd9a947566eddb1ffcf5617967c7412676
origin/main ancestor           yes
feature-only commits           58
main-only commits              0
tracked worktree               clean
index                          empty
current user                   astro
```

Allowed untracked state is exactly the five frozen paths plus architect-owned
document 170. Any other untracked path at entry is a blocker unless it is an
existing ignored test/build output proven by `git check-ignore -v`.

Do not continue on ref/topology mismatch.

## 4. Canonical runtime and immutable snapshots

### 4.1 Services and listeners

Record:

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

Expected starting witnesses:

```text
sidecar PID/start   3582982 / Sun 2026-07-12 22:02:52 MSK
API PID/start       3940721 / Mon 2026-07-13 06:54:31 MSK
frontend PID/start  916433  / Thu 2026-07-09 11:30:03 MSK
nginx PID           1048
3002/8000/18091     present, health 200
3003/3010/8001/18092 absent
```

If a PID legitimately differs from the recorded value before task start, do
not restart anything. Stop and report the new exact PID/start for architect
classification. During the task all accepted starting PID/start values must
remain unchanged.

Also require no pre-existing temporary window/process:

```bash
tmux list-windows -t astro -F '#{window_index}:#{window_name} panes=#{window_panes}'
pgrep -a -f '[p]review-v2-real.mjs' || true
pgrep -a -f '[n]ext dev --hostname 127.0.0.1 --port 3003' || true
pgrep -a -f '[n]ext start --hostname 127.0.0.1 --port 3010' || true
```

No window named `stage2-rc-candidate` or `stage2-v2-preview` may exist.

### 4.2 Tracked/config/env snapshots

Capture SHA-256, size, mode and ownership before any generator/build/runtime:

```bash
sha256sum \
  next-env.d.ts tsconfig.json package.json pnpm-lock.yaml \
  packages/contracts/openapi.json \
  packages/contracts/_generated.ts \
  packages/contracts/_generated.zod.ts \
  .next-prod/BUILD_ID \
  .env .env.production \
  > /tmp/stage2-w4-start.sha256

stat -c '%n %s %a %U:%G' \
  next-env.d.ts tsconfig.json package.json pnpm-lock.yaml \
  packages/contracts/openapi.json \
  packages/contracts/_generated.ts \
  packages/contracts/_generated.zod.ts \
  .next-prod/BUILD_ID \
  .env .env.production \
  > /tmp/stage2-w4-start.stat
```

Do not print env contents. Run a safe state-only parser for these keys in both
env files:

```text
SOLARSAGE_V2_ENABLED
SOLARSAGE_V2_FRONTEND_ENABLED
SOLARSAGE_V2_DUAL_RUN
```

The parser may print only `UNSET`, `TRUE`, `FALSE`, `INVALID` or
`DUPLICATE_<n>`, never the raw value. Confirm at entry:

```text
.env:            all three UNSET
.env.production: all three UNSET
```

No env key is changed in W4.

### 4.3 Disk/rollback baseline

Record:

```bash
du -sk .next-prod
du -sk .next-v2-real-preview 2>/dev/null || true
df -Pk .
```

Accepted architect baseline before the task:

```text
.next-prod                 18104 KiB
.next-v2-real-preview     191080 KiB
filesystem available   22760948 KiB
```

Exact sizes can change only for ignored preview output during its managed run;
`.next-prod/BUILD_ID`, canonical production service and tracked config must not.

## 5. Contract platform and shared package gates

Run in this exact order and save safe logs under `/tmp/stage2-w4-*`:

```bash
pnpm contracts:generate
git diff --exit-code -- \
  packages/contracts/openapi.json \
  packages/contracts/_generated.ts \
  packages/contracts/_generated.zod.ts
pnpm contracts:check
pnpm contracts:compat
pnpm contracts:fixture:check
PYTHONPATH=packages/py-contracts \
  apps/api/.venv/bin/python -m pytest packages/py-contracts/tests/ -q
```

Require:

```text
generated contract diff     zero
contracts check             110 PASS
compatibility               16 additive / 0 breaking
fixture check               PASS / clean
Python contract package     44 PASS
```

Any generated tracked diff is a hard blocker. Do not accept or restore it.

## 6. Frontend full matrix

Run:

```bash
npx vitest run
pnpm typecheck
pnpm guardrails:prod
pnpm guardrails:contracts
pnpm guardrails:frontend
pnpm guardrails:secrets
```

Require all exit zero. Record exact fresh Vitest file/test counts; the accepted
pre-W4 branch baseline is `1067 PASS`, but callback must report the actual
fresh count rather than copy this number blindly.

`guardrails:frontend` must include green ESLint/type/GRACE-negative behavior;
no warning/error baseline is accepted there after W2A/W2B/W2C.

Also run the focused launcher unit test and source strictness scan:

```bash
npx vitest run __tests__/scripts/preview-v2-real.test.ts

test -z "$(rg -n 'page\.route|context\.route|routeFromHAR|addCookies|storageState|fixture=' \
  e2e/real-v2-preview.spec.ts || true)"

rg -n 'today\.v2\.1|frontendPayloadVersion|contentVersion|long|medium|fast' \
  e2e/real-v2-preview.spec.ts
```

The forbidden-pattern scan must have zero matches.

## 7. Backend GRACE — exact legacy classification, no cleanup

Run the full canonical command and preserve its non-zero output:

```bash
set +e
pnpm guardrails:backend-grace \
  > /tmp/stage2-w4-backend-grace-current.log 2>&1
backend_grace_rc=$?
set -e
test "$backend_grace_rc" -eq 1
```

The self-test portion must be `13 PASS`. The full app marker lint is a tracked
legacy baseline, not W4 edit authority. Architect independently established:

```text
origin/main violations              85 / 23 failing paths
current violations                  61 / 17 failing paths
current code counts:
  GRC001 3
  GRC010 34
  GRC011 3
  GRC020 8
  GRC021 12
  GRC030 1
removed normalized signatures       24
new normalized signatures             0
violations on changed paths            4 / one path (canon_service.py)
violations on feature-added lines       0
```

Reproduce the comparison mechanically:

1. parse only rows matching `<absolute .py path>:<line>: GRC...`;
2. export `origin/main:apps/api/app` with `git archive` into a unique `/tmp`
   directory; do not create a worktree/branch;
3. run current `scripts/grace_lint.py` against the exported main app;
4. normalize each diagnostic to `(repository-relative path, code, message)`,
   explicitly excluding the line number;
5. compare multisets, requiring current-minus-main `0` and main-minus-current
   `24`;
6. parse new-side ranges from
   `git diff --unified=0 origin/main...HEAD -- apps/api/app` and require zero
   current diagnostics whose line lies in an added/replaced range;
7. delete only the temporary export directory.

The four current diagnostics on changed `canon_service.py` are all present in
main and lie on unchanged lines:

```text
line 1   GRC020
line 1   GRC021
line 69  GRC010 validate_canon_bundle
line 120 GRC010 load_canon_bundle
```

Do not add comments or split `llm_service.py`. W4 acceptance is based on zero
new signature and zero added-line violation, consistent with master section 2.
Any count drift, new signature or added-line violation is a hard blocker.

## 8. Backend and sidecar runtime-independent gates

Run the complete suites from repository root:

```bash
PYTHONPATH=apps/api \
  apps/api/.venv/bin/python -m pytest apps/api/tests/ -q

PYTHONPATH=apps/solarsage \
  apps/solarsage/venv/bin/python -m pytest apps/solarsage/tests/ -q

apps/api/.venv/bin/python -m pip check
apps/solarsage/venv/bin/python -m pip check
```

Require:

```text
API                         1406 PASS / 4 SKIP
API lifecycle warnings      0
API accepted warning        one known Starlette deprecation only
sidecar                     201 PASS / 0 SKIP
sidecar accepted warning    one known Starlette deprecation only
API pip check               no broken requirements
sidecar pip check           no broken requirements
```

Do not install Ruff into the sidecar venv.

Run the security-focused API collection separately even though it is included
in the full suite:

```bash
PYTHONPATH=apps/api apps/api/.venv/bin/python -m pytest \
  apps/api/tests/test_today_preview_transport.py \
  apps/api/tests/test_today_preview_access.py \
  apps/api/tests/test_today_selection_context.py \
  apps/api/tests/test_today_cache_v2_key.py \
  -q
```

Require exact `163 PASS`, including production/public/ordinary/wrong-marker/
wrong-identity/global-selector and cache-isolation cases.

## 9. API Ruff and MyPy changed-line proof

### 9.1 API Ruff across all current changed Python paths

Build the exact current path array:

```bash
mapfile -t api_py_paths < <(
  git diff --diff-filter=ACMR --name-only origin/main...HEAD -- \
    apps/api/app apps/api/tests |
  rg '\.py$' |
  sort
)
test "${#api_py_paths[@]}" -eq 85
```

Run API-venv Ruff 0.15.14 in JSON form without fixes:

```bash
set +e
apps/api/.venv/bin/python -m ruff check --output-format json \
  "${api_py_paths[@]}" \
  > /tmp/stage2-w4-api-ruff-current.json
ruff_rc=$?
set -e
test "$ruff_rc" -eq 1
```

Export only the exact changed paths that exist in `origin/main` into a unique
`/tmp` directory. Use `git cat-file -e` before `git show`; do not pass new files
as missing main paths. Run the same Ruff JSON command there and normalize the
temporary prefix back to repository-relative paths.

Require exactly:

```text
current changed Python paths          85
paths existing in origin/main         29
current diagnostics                   31 / 6 paths
current codes                         F401 30 / F841 1
main diagnostics                      44 / 11 paths
main codes                            E741 1 / F401 40 / F841 3
current minus main signatures          0
main minus current diagnostics        13
diagnostics on added/replaced lines    0
```

Normalized Ruff signature is `(relative path, code, message)`. New-side range
ownership must come from zero-context hunk headers, not `blame` or visual
guessing. Do not edit the 31 legacy rows.

### 9.2 Canonical cold MyPy

The command is sensitive to working directory. Run exactly from `apps/api`,
not repository root:

```bash
cd /opt/solarsage-astro/apps/api
set +e
./.venv/bin/mypy app \
  --no-incremental \
  --no-error-summary \
  --show-error-codes \
  > /tmp/stage2-w4-mypy-current.log 2>&1
mypy_rc=$?
set -e
test "$mypy_rc" -eq 1
cd /opt/solarsage-astro
```

Parse only `error:` rows and normalize `app/...` to `apps/api/app/...`.
Compare each line with new-side ranges from:

```bash
git diff --unified=0 origin/main...HEAD -- apps/api/app
```

Require exact accepted W3B baseline:

```text
global diagnostics                  80
global failing paths                11
codes:
  arg-type                          11
  assignment                         2
  call-arg                          51
  name-defined                      12
  return-value                       1
  union-attr                         3
diagnostics on changed paths          6 / 2 paths
diagnostics on feature-added lines    0
```

The six changed-path diagnostics are the accepted unchanged legacy rows only:

```text
apps/api/app/services/calendar_service.py  lines 318, 320, 321, 322
apps/api/app/api/day.py                    line 141 twice
```

Do not run MyPy from repository root and do not add ignores/casts. Any new
error, path/count drift or added-line error is a blocker.

## 10. Sidecar static proof replay

Repeat the accepted W3C proof from document 168 without source changes.

Require exact diff inventory:

```text
sidecar changed paths          18
changed Python paths           16
current paths present in main  14
feature-added clean paths       2
```

Use only API-venv Ruff 0.15.14:

```bash
apps/api/.venv/bin/python -m ruff check --output-format json <16 paths>
```

Reproduce:

```text
origin/main diagnostics                 18
current diagnostics                       8
removed baseline                         10
new normalized signatures                 0
diagnostics on feature-added lines         0
```

Do not pass the two feature-added paths to the main Ruff command, do not
produce synthetic E902 rows and do not install a tool into sidecar venv.

## 11. Production-import isolation and production-dead proof

Run and save complete match lists:

```bash
rg -n 'lib/mocks|lib/demo-data|demo-data|dev-fixtures|fixture=' \
  app components hooks lib --glob '!**/*.test.*' \
  > /tmp/stage2-w4-production-import-scan-1.log || true

rg -n 'USE_FIXTURES|18092|page\.route|context\.route|routeFromHAR' \
  app components hooks lib apps/api/app apps/solarsage/solarsage \
  > /tmp/stage2-w4-production-import-scan-2.log || true
```

Classify every match as one of:

```text
production-import reachable       -> blocker
explicit development fail-closed  -> accepted with exact path/reason
test-only/reference text          -> accepted with exact path/reason
```

No runtime product path may import `lib/mocks/*`, `lib/demo-data.ts`, demo API
or fixture payload. `USE_FIXTURES`, listener `18092` and interception APIs must
remain absent from product runtime.

Together with the exact `163 PASS` collection, this is the production-dead
preview proof. Do not set `NODE_ENV`, `APP_ENV` or global V2 flags globally to
manufacture an outcome.

## 12. Isolated production build and managed candidate smoke on 3010

Do not begin this section unless sections 5–11 have no hard blocker.

### 12.1 Build preflight

Require:

```bash
test ! -e .next-stage2-rc
test -f .next-prod/BUILD_ID
! ss -ltn '( sport = :3010 )' | rg -q LISTEN
```

Record immediately before build:

```bash
du -sk .next-prod
df -Pk .
sha256sum .next-prod/BUILD_ID next-env.d.ts tsconfig.json
```

Build as user `astro`:

```bash
NEXT_DIST_DIR=.next-stage2-rc \
NEXT_TELEMETRY_DISABLED=1 \
pnpm build
```

Require build success and normal route summary. While building, canonical
frontend service PID/start and port `3002` must not change.

### 12.2 Closed generated-config restoration

After build, inspect only:

```bash
git diff -- next-env.d.ts tsconfig.json
```

Recognized Next-generated drift is limited to:

- `next-env.d.ts`: route types import points at `.next-stage2-rc` instead of
  the starting `.next` import;
- `tsconfig.json`: exact candidate-only includes
  `.next-stage2-rc/types/**/*.ts` and/or
  `.next-stage2-rc/dev/types/**/*.ts` were appended.

If and only if drift is exactly that closed shape, use minimal `apply_patch`:

1. restore the route import to the exact starting
   `import "./.next/types/routes.d.ts";` line;
2. remove only the candidate-specific `.next-stage2-rc` include entries;
3. preserve every other byte/order/value and existing real-preview includes;
4. prove starting SHA-256/mode and zero tracked diff.

Do not use copy, checkout, restore or reset. Any other drift is a blocker and
must be preserved for architect inspection.

### 12.3 Rollback-space proof before start

With both `.next-prod` and `.next-stage2-rc` present, record:

```bash
du -sk .next-prod .next-stage2-rc
df -Pk .
```

Require:

- both dist trees coexist;
- available KiB after build is greater than or equal to candidate KiB;
- `.next-prod/BUILD_ID` hash is unchanged;
- canonical frontend remains 200 on `3002` with unchanged PID/start.

### 12.4 Managed candidate window

Create exactly one detached runtime window, not another coder:

```bash
tmux new-window -d -t astro: -n stage2-rc-candidate \
  'cd /opt/solarsage-astro && exec env NODE_ENV=production NEXT_DIST_DIR=.next-stage2-rc NEXT_TELEMETRY_DISABLED=1 pnpm exec next start --hostname 127.0.0.1 --port 3010'
```

Wait bounded up to 60 seconds for the one listener/readiness. Do not create a
second process on failure. Then require all HTTP 200:

```bash
curl -fsS --max-time 10 -o /dev/null -w 'candidate_root=%{http_code}\n' \
  http://127.0.0.1:3010/
curl -fsS --max-time 10 -o /dev/null -w 'candidate_api=%{http_code}\n' \
  http://127.0.0.1:3010/api/health
curl -fsS --max-time 10 -o /dev/null -w 'candidate_day_shell=%{http_code}\n' \
  'http://127.0.0.1:3010/day/2026-07-08?why=1'
```

Prove exactly one 3010 listener and that its process tree descends from
`astro:stage2-rc-candidate.0`. Ports `3003`, `8001`, `18092` remain absent.

### 12.5 Exact candidate shutdown and cleanup

Send one `C-c` to the exact window, wait bounded up to 15 seconds and verify
the listener/process tree exits. If the now-idle exact window remains, kill
only `astro:stage2-rc-candidate`; never kill by broad process name.

Require:

```text
3010 listener/processes   absent
candidate tmux window     absent
canonical services        unchanged
```

Only after shutdown and recorded size evidence remove exactly:

```bash
rm -rf -- .next-stage2-rc
```

No other build directory may be removed. Prove `.next-stage2-rc` absent,
tracked config restored and `.next-prod/BUILD_ID` unchanged.

## 13. Strict real V2 preview on 3003

Do not begin if candidate cleanup or any earlier hard gate failed.

### 13.1 Managed start

Reconfirm 3003 free, canonical API/sidecar health 200 and no preview process.
Create exactly one detached runtime window:

```bash
tmux new-window -d -t astro: -n stage2-v2-preview \
  'cd /opt/solarsage-astro && exec pnpm preview:v2:real'
```

Wait bounded up to 90 seconds for all exact launcher labels:

```text
[preview:v2:real] Real API: http://127.0.0.1:8000
[preview:v2:real] http://127.0.0.1:3003/day/2026-07-08?why=1
[preview:v2:real] REAL backend preview; no fixture or mock API.
```

Require HTTP 200 for root, rewritten API health and day shell. Prove one 3003
listener descended from the exact preview window and no 8001/18092 listener.

While preview is running, starting SHA/mode values of `next-env.d.ts`,
`tsconfig.json`, `package.json` and `pnpm-lock.yaml` must be unchanged. The
launcher is responsible for its own recognized generated-file hygiene.

### 13.2 Strict desktop/mobile E2E

From `astro:0.0`, run exactly:

```bash
E2E_BASE_URL=http://127.0.0.1:3003 \
  pnpm exec playwright test e2e/real-v2-preview.spec.ts \
  --project=chromium \
  --project=mobile
```

Require exact `2 PASS`, one per project, with no retry-dependent success.
Evidence must prove through public DOM/network observations already encoded in
the strict spec:

- natural `POST /api/auth/dev`, no manually injected cookie;
- exact `GET /api/day/2026-07-08`;
- `today.v2.1`, frontend payload `3`, content `10`;
- backend `long`, `medium`, `fast` horizons and expanded timing/details;
- human-first actions/disclosures and 12-sphere navigation/focus behavior;
- no fixture query, mock server, interception, V1/locked/unavailable fallback;
- six project-specific redacted attachments/screenshots.

Do not print raw response payload, cookie, personal copy or attachment JSON.

### 13.3 Exact preview shutdown

After E2E, send one `C-c` to `astro:stage2-v2-preview.0`, wait bounded up to 15
seconds for launcher and its owned process group to exit. If only an idle exact
window remains, kill only that window.

Require:

```text
3003 listener/launcher/Next descendants  absent
preview tmux window                      absent
8001/18092                               absent
tracked config snapshots                 exact starting bytes/mode
canonical service PID/start              unchanged
```

Do not leave a review preview running after W4.

## 14. Real Telegram HMAC transport smoke on canonical API

Run only after 3003 and 3010 are stopped. Reconfirm the safe env-state report:
both global enable flags remain `UNSET`; do not mutate them.

Use the existing generator in memory. Do not invoke its CLI because the CLI
prints raw initData. Run this closed script with API venv Python:

```bash
apps/api/.venv/bin/python - <<'PY'
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import httpx

root = Path('/opt/solarsage-astro')
generator_path = root / 'scripts/generate-telegram-test-initdata.py'
spec = importlib.util.spec_from_file_location('stage2_rc_initdata', generator_path)
assert spec is not None and spec.loader is not None
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

# Reuse the established synthetic local-preview identity without changing its
# username/profile. The raw initData and cookie remain memory-only.
init_data = module.generate_initdata(
    user_id=999999999,
    first_name='Dev',
    last_name='User',
    username='dev_user',
)

headers = {'User-Agent': 'solarsage-stage2-rc-hmac-smoke'}
with httpx.Client(timeout=15.0, trust_env=False) as client:
    auth = client.post(
        'http://127.0.0.1:8000/api/auth/telegram',
        json={'initData': init_data},
        headers=headers,
    )
    assert auth.status_code == 200
    cookies = list(auth.cookies.items())
    assert len(cookies) == 1
    cookie_name, cookie_value = cookies[0]
    assert cookie_name and cookie_value
    cookie_headers = {
        **headers,
        'Cookie': f'{cookie_name}={cookie_value}',
    }

    profile = client.get(
        'http://127.0.0.1:8000/api/profile',
        headers=cookie_headers,
    )
    assert profile.status_code == 200

    logout = client.post(
        'http://127.0.0.1:8000/api/auth/logout',
        headers=cookie_headers,
    )
    assert logout.status_code == 204

    revoked = client.get(
        'http://127.0.0.1:8000/api/profile',
        headers=cookie_headers,
    )
    assert revoked.status_code == 401

print(json.dumps({
    'auth_status': 200,
    'session_cookie_present': True,
    'profile_status': 200,
    'logout_status': 204,
    'revoked_profile_status': 401,
    'auth_dev_used': False,
    'raw_initdata_printed': False,
    'cookie_value_printed': False,
}, sort_keys=True))
PY
```

This smoke may create/revoke one normal session row through the real auth
contract. It must not call `/api/auth/dev`, request Today V2, change profile
facts, print response bodies or change env flags. API PID/start remains
unchanged.

## 15. Final integrity, rollback and branch audit

Repeat all immutable witnesses:

```bash
sha256sum \
  next-env.d.ts tsconfig.json package.json pnpm-lock.yaml \
  packages/contracts/openapi.json \
  packages/contracts/_generated.ts \
  packages/contracts/_generated.zod.ts \
  .next-prod/BUILD_ID \
  .env .env.production \
  > /tmp/stage2-w4-final.sha256

stat -c '%n %s %a %U:%G' \
  next-env.d.ts tsconfig.json package.json pnpm-lock.yaml \
  packages/contracts/openapi.json \
  packages/contracts/_generated.ts \
  packages/contracts/_generated.zod.ts \
  .next-prod/BUILD_ID \
  .env .env.production \
  > /tmp/stage2-w4-final.stat

diff -u /tmp/stage2-w4-start.sha256 /tmp/stage2-w4-final.sha256
diff -u /tmp/stage2-w4-start.stat /tmp/stage2-w4-final.stat
```

Both diffs must be empty. Then:

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
du -sk .next-prod
df -Pk .
```

Final requirements:

```text
HEAD/upstream/remote feature    42a0c5d... equal
main/origin/remote main         c9bc36b... unchanged
feature-only/main-only          58 / 0
tracked worktree/index          clean / empty
untracked                       five frozen + doc 170 only
.next-stage2-rc                 absent
temporary tmux windows          absent
3003/3010/8001/18092            absent
3002/8000/18091                 present and healthy
canonical service PID/start     exact task-start witnesses
.next-prod BUILD_ID/hash        unchanged
env hashes/safe flag states     unchanged / enable flags UNSET
rollback capacity               available KiB >= measured candidate KiB
commit/push/main/deploy          not performed
```

## 16. Failure policy

Expected diagnostic non-zero results are only:

```text
backend-grace  61 classified legacy violations, new=0, added-line=0
API Ruff       31 classified legacy diagnostics, new=0, added-line=0
API MyPy       80 classified legacy diagnostics, added-line=0
sidecar Ruff    8 classified legacy diagnostics, new=0, added-line=0
```

Every other non-zero command is a hard blocker. A deviation in any expected
count/signature/path ownership is also a blocker; do not normalize it away.

If a hard blocker appears before runtime sections, do not start 3010/3003/HMAC.
If it appears during runtime, cleanly stop only the exact owned temporary
window/process and preserve all evidence. Do not edit code to repair it.

Blocked callback prefix:

```text
BLOCKED_STAGE_2_W4_FINAL_RC
```

Include the failed command, exit code, safe count/path summary, cleanup state
and unchanged refs/services. Never include secret/personal bodies.

## 17. Required success callback and stop

```text
READY_STAGE_2_RELEASE_CANDIDATE_FOR_MAIN
base_head: 42a0c5dba7d476b156e0ff17d4fdccb5a22aaa93
feature_local_tracking_remote: EQUAL
main_origin_remote: c9bc36bd9a947566eddb1ffcf5617967c7412676_UNCHANGED
topology: ORIGIN_MAIN_ANCESTOR_FEATURE_58_0
contracts_generate_diff: ZERO
contracts_check: 110_PASS
contracts_compat: 16_ADDITIVE_0_BREAKING
contracts_fixture: PASS
pycontracts: 44_PASS
vitest: <exact files/tests>_PASS
typecheck: PASS
prod_guard: PASS
contracts_guard: PASS
frontend_guard: PASS
secrets_guard: PASS
backend_grace_selftests: 13_PASS
backend_grace_full: CLASSIFIED_61_17
backend_grace_main_current: 85_TO_61_REMOVED_24_NEW_0
backend_grace_feature_added_lines: ZERO
api_tests: 1406_PASS_4_SKIP
api_lifecycle_warnings: ZERO
api_warning: KNOWN_STARLETTE_DEPRECATION_ONLY
sidecar_tests: 201_PASS
sidecar_warning: KNOWN_STARLETTE_DEPRECATION_ONLY
api_pip_check: PASS
sidecar_pip_check: PASS
preview_security: 163_PASS
api_ruff_current: 31_DIAGNOSTICS_6_PATHS
api_ruff_main_current: 44_TO_31_REMOVED_13_NEW_0
api_ruff_feature_added_lines: ZERO
api_mypy_cold: 80_DIAGNOSTICS_11_PATHS
api_mypy_changed_paths: 6_DIAGNOSTICS_2_PATHS
api_mypy_feature_added_lines: ZERO
sidecar_ruff: MAIN_18_CURRENT_8_REMOVED_10_NEW_0
sidecar_ruff_feature_added_lines: ZERO
production_imports: NO_RUNTIME_FIXTURE_OR_MOCK_PATH
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
telegram_auth_dev: NOT_USED
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

Then stop and wait for architect review. Do not proceed to `main` on your own.
