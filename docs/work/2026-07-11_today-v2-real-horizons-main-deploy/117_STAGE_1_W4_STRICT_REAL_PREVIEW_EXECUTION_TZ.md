# Stage 1.W4 — strict real preview execution on 3003

Дата: 2026-07-13
Ветка: `preview/solarsage-v2-human-first-navigator-ux`
Accepted W3 SHA: `7d37acbaa31118a8545987a39a5fabe18fbb6e32`
Parent plans:

- `101_TWO_STAGE_COMPLETION_MASTER_PLAN.md`
- `102_STAGE_1_SAFE_DEV_SCOPED_V2_PREVIEW_MASTER_TZ.md`

Статус: **AUTHORIZED RUNTIME/E2E WAVE — NO REPOSITORY EDITS**

## 1. Цель

Поднять существующий fail-closed real preview launcher на `127.0.0.1:3003`,
доказать desktop и mobile реальный V2 UI без fixture/interception и оставить
accepted review URL работающим для пользователя:

```text
http://127.0.0.1:3003/day/2026-07-08?why=1
```

Runtime chain:

```text
browser 127.0.0.1:3003
  -> Next development frontend
  -> /api rewrite to canonical 127.0.0.1:8000
  -> natural POST /api/auth/dev
  -> natural GET /api/day/2026-07-08
  -> frontend exact local-dev marker
  -> request-scoped today.v2.1 / 3 / 10
  -> backend long / medium / fast horizons
```

No fixture, mock, route interception, second API or global V2 flag.

## 2. Accepted components — do not edit

Launcher and strict E2E were accepted in W0 at commit `828c20d...`:

```text
scripts/preview-v2-real.mjs
e2e/real-v2-preview.spec.ts
__tests__/scripts/preview-v2-real.test.ts
package.json -> preview:v2:real
playwright.config.ts configured chromium + mobile projects
```

W3 canonical runtime is accepted at `7d37acb...`:

```text
API PID 3887119, active since Mon 2026-07-13 05:12:53 MSK
ordinary request -> today.v1 / 1
exact preview request -> today.v2.1 / 3 / 10
cache families distinct
global V2 flags unset
```

This wave runs existing code only. It does not repair or weaken it.

## 3. Allowed scope

Allowed:

1. read-only git/service/port/config preflight;
2. focused launcher unit test and TypeScript typecheck;
3. create one new tmux window inside existing session `astro` named exactly
   `v2-preview`;
4. run exactly `pnpm preview:v2:real` in that managed window;
5. read-only HTTP readiness checks;
6. run strict Playwright spec in existing coder pane `astro:0.0`;
7. inspect ignored `test-results/` and `playwright-report/` artifacts;
8. read-only process tree/config/runtime/journal proof;
9. leave `astro:v2-preview.0` running only after every success gate;
10. safe callback to architect.

No repository file may be created or edited by coder in this execution wave.
Document 117 is architect-authored and must remain byte-identical.

## 4. Absolute prohibitions

- no `git add`, commit, push, merge, rebase;
- no product/test/docs/config edit;
- no weakening/skip/conditional acceptance in E2E;
- no fixture query, dev-fixture API, captured payload or mock JSON;
- no `page.route`, `context.route`, HAR or request interception;
- no manual cookie seeding or Telegram initData injection;
- no mock preview `pnpm preview:v2`;
- no listener/process on 18092;
- no API on 8001 and no manual/second uvicorn;
- no service restart/reload/stop;
- no env/unit/nginx mutation;
- no global V2 flag edit;
- no production frontend restart/build on 3002;
- no main merge or deploy;
- no deletion of frozen unrelated paths;
- no printing raw payload, Cookie/Set-Cookie/session token, user UUID,
  activation ids or personal/human copy from response artifacts.

If launcher/E2E/config/process proof fails, do not modify code. Stop the managed
preview cleanly, prove 3003 descendants absent and return blocked callback.

## 5. Mandatory preflight

### 5.1 Git identity and clean state

```bash
git branch --show-current
git rev-parse HEAD
git rev-parse refs/remotes/origin/preview/solarsage-v2-human-first-navigator-ux
git ls-remote --heads origin refs/heads/preview/solarsage-v2-human-first-navigator-ux
git diff --quiet
git diff --cached --quiet
git status --short
git diff --check
```

Required:

```text
branch = preview/solarsage-v2-human-first-navigator-ux
HEAD = tracking = remote = 7d37acbaa31118a8545987a39a5fabe18fbb6e32
tracked tree = clean
index = empty
```

Exact untracked before execution:

```text
?? .grace/
?? artifacts/design/
?? docs/superpowers/plans/2026-07-05-fix-day-route-auth-build.md
?? docs/work/2026-07-11_today-v2-real-horizons-main-deploy/117_STAGE_1_W4_STRICT_REAL_PREVIEW_EXECUTION_TZ.md
?? grace.db
?? skills/
```

Any other repository change blocks execution.

### 5.2 Canonical runtime witnesses

```bash
systemctl show solarsage-api.service solarsage-sidecar.service solarsage-frontend.service nginx.service \
  --property=Id,ActiveState,SubState,MainPID,ExecMainStartTimestamp --no-pager

ss -ltnp 'sport = :3002 or sport = :3003 or sport = :8000 or sport = :8001 or sport = :18091 or sport = :18092'
```

Required exact:

```text
API PID/start = 3887119 / Mon 2026-07-13 05:12:53 MSK
sidecar PID/start = 3582982 / Sun 2026-07-12 22:02:52 MSK
frontend PID/start = 916433 / Thu 2026-07-09 11:30:03 MSK
nginx PID/start = 1048 / Wed 2026-07-01 15:36:15 MSK
8000/18091/3002 present
3003/8001/18092 absent
```

Exact health 200:

```bash
curl -fsS --max-time 5 -o /dev/null -w 'api=%{http_code}\n' http://127.0.0.1:8000/api/health
curl -fsS --max-time 5 -o /dev/null -w 'sidecar=%{http_code}\n' http://127.0.0.1:18091/v1/health
```

### 5.3 No existing preview window/process

```bash
tmux list-windows -t astro -F '#{window_index}:#{window_name} panes=#{window_panes}'
pgrep -a -f '[p]review-v2-real.mjs' || true
pgrep -a -f '[n]ext dev --hostname 127.0.0.1 --port 3003' || true
```

Required:

- no tmux window named `v2-preview`;
- no launcher process;
- no Next 3003 process;
- port 3003 free.

Do not kill an unexpected occupant. Unexpected state blocks execution.

### 5.4 Config snapshots

Record before SHA-256, size, mode and mtime:

```bash
sha256sum next-env.d.ts tsconfig.json package.json pnpm-lock.yaml
stat -c '%n %s %Y %a %U:%G' next-env.d.ts tsconfig.json package.json pnpm-lock.yaml
```

After readiness, after E2E and at final callback all values must match literally.

### 5.5 Focused static/unit gates

```bash
npx vitest run __tests__/scripts/preview-v2-real.test.ts
pnpm typecheck
pnpm guardrails:prod
```

All exact pass. Record test count, not generic PASS.

Static strictness proof:

```bash
rg -n 'page\.route|context\.route|routeFromHAR|addCookies|storageState|fixture=' \
  e2e/real-v2-preview.spec.ts
```

Expected zero matches.

Also prove source contains strict identities and both project names:

```bash
rg -n 'today\.v2\.1|frontendPayloadVersion|contentVersion|long|medium|fast' \
  e2e/real-v2-preview.spec.ts
rg -n "name: 'chromium'|name: 'mobile'|iPhone 13|Desktop Chrome" playwright.config.ts
```

## 6. Start one managed real preview

### 6.1 Create exact tmux window

Create one detached window in existing session `astro`:

```bash
tmux new-window -d -t astro: -n v2-preview \
  'cd /opt/solarsage-astro && exec pnpm preview:v2:real'
```

Do not run launcher with `nohup`, `&`, systemd, Docker or a second shell outside
this managed window.

Expected target after creation:

```text
astro:v2-preview.0
```

### 6.2 Wait for exact readiness labels

Poll only the pane output for up to 90 seconds. Expected exact labels:

```text
[preview:v2:real] Real API: http://127.0.0.1:8000
[preview:v2:real] http://127.0.0.1:3003/day/2026-07-08?why=1
[preview:v2:real] REAL backend preview; no fixture or mock API.
```

Do not expose environment or payload.

If pane exits or labels do not appear in 90 seconds, follow failure cleanup in
section 11. Do not create a second window/launcher.

### 6.3 Readiness transport

After labels:

```bash
curl -fsS --max-time 10 -o /dev/null -w 'root=%{http_code}\n' http://127.0.0.1:3003/
curl -fsS --max-time 10 -o /dev/null -w 'day_shell=%{http_code}\n' 'http://127.0.0.1:3003/day/2026-07-08?why=1'
curl -fsS --max-time 10 -o /dev/null -w 'rewritten_api_health=%{http_code}\n' http://127.0.0.1:3003/api/health
```

All exact 200.

### 6.4 Managed process ownership

Capture:

```bash
tmux list-windows -t astro -F '#{window_index}:#{window_name} panes=#{window_panes}'
tmux list-panes -t astro:v2-preview -F '#{session_name}:#{window_name}.#{pane_index} pid=#{pane_pid} cmd=#{pane_current_command}'
ss -ltnp 'sport = :3003'
ps -eo pid,ppid,pgid,sid,stat,lstart,cmd --forest | \
  rg 'preview-v2-real\.mjs|next dev --hostname 127\.0\.0\.1 --port 3003|next-server|PID'
```

Prove:

- one `v2-preview` window, one pane;
- launcher is descendant/owned process of that pane;
- Next 3003 server is descendant of launcher-owned process tree;
- exactly one 3003 listener;
- no unrelated/orphan 3003 process;
- 18092 and 8001 remain absent.

## 7. Config cleanliness while preview is running

Immediately after readiness:

```bash
sha256sum next-env.d.ts tsconfig.json package.json pnpm-lock.yaml
stat -c '%n %s %Y %a %U:%G' next-env.d.ts tsconfig.json package.json pnpm-lock.yaml
git diff --quiet
git diff --cached --quiet
git status --short
```

All four file snapshots must equal preflight. Tracked tree/index remain clean;
only exact six untracked entries including architect doc 117.

Ignored runtime dirs are allowed:

```text
.next-v2-real-preview/
test-results/
playwright-report/
```

They must not appear in git status.

## 8. Strict desktop + mobile no-interception E2E

Run exactly from coder pane while managed preview stays running:

```bash
E2E_BASE_URL=http://127.0.0.1:3003 \
  pnpm exec playwright test e2e/real-v2-preview.spec.ts \
    --project=chromium --project=mobile
```

Required exact result:

```text
2 passed
0 failed
0 skipped
```

The spec itself must prove for each project:

- fresh browser context with no cookies;
- natural auth POST exact 200;
- natural day GET exact 200;
- generated wire schema parse;
- exact `today.v2.1 / 3 / 10`;
- exact horizon order long/medium/fast;
- unique horizon IDs and non-empty activation/actions;
- URL contains only `why=1`, no fixture;
- no dev-fixture/18092/mock/JSON network;
- `today-screen` ready;
- Why expanded;
- backend horizons ready, not unavailable/fixture;
- three horizon cards;
- all three technical disclosures work with exact ARIA linkage;
- sphere navigation updates exact stable DOM contract;
- clicked sphere is focused and in viewport;
- project viewport remains configured Desktop Chrome / iPhone 13;
- per-project full-day PNG;
- per-project Why-section PNG;
- per-project redacted network proof JSON.

No V1/401/locked/unavailable compatibility acceptance.

## 9. Artifact inspection

After green E2E, list artifacts without printing raw binary or dynamic copy:

```bash
find test-results -type f -maxdepth 8 -printf '%p %s bytes\n' | sort
```

Locate exact two sets by project:

```text
real-v2-preview-chromium-network-proof.json
real-v2-preview-chromium-day.png
real-v2-preview-chromium-why.png
real-v2-preview-mobile-network-proof.json
real-v2-preview-mobile-day.png
real-v2-preview-mobile-why.png
```

Playwright may store attachment paths under project-specific result directories;
match by basename, not assumed parent path.

For each PNG:

- file exists;
- size > 0;
- `file` identifies PNG;
- record SHA-256 and dimensions if `identify` is available.

For each redacted JSON proof, parse with `jq` and assert exact shape/values:

```json
{
  "source": "real-api",
  "fixture": false,
  "interception": false,
  "transport": { "auth": 200, "day": 200 },
  "versions": { "payload": "today.v2.1", "frontend": 3, "content": 10 },
  "horizons": ["long", "medium", "fast"],
  "authPath": "/api/auth/dev",
  "dayPath": "/api/day/2026-07-08"
}
```

Assert each proof has exact top-level keys above and contains none of:

- Cookie/Set-Cookie/session/token;
- user/profile UUID;
- birth data;
- activation ids;
- titles, summaries, actions or other dynamic human copy;
- response body beyond the exact redacted structure.

Record artifact paths, byte sizes and SHA-256 only.

## 10. Final running-preview acceptance proof

After E2E and artifact validation, while preview remains running:

1. repeat config snapshots from section 5.4 — exact match;
2. repeat git clean state — exact six allowed untracked entries;
3. repeat service PID/start — all four unchanged;
4. repeat listeners — 3002/3003/8000/18091 present, 8001/18092 absent;
5. repeat managed process ownership — exactly one managed preview tree;
6. root/day/api-health through 3003 exact 200;
7. run a safe HTTP discriminator proof through 3003 in a clean browser or reuse
   the redacted Playwright proof — exact V2 only;
8. scan launcher pane since start for `error`, `failed`, `unsafe`, `timeout`,
   `occupied`, `unexpected child exit`; exact zero lifecycle failures;
9. scan API/sidecar journal only since W4 start for traceback/critical/5xx and
   privacy leakage without printing raw logs;
10. prove production frontend 3002 and nginx were not restarted.

User review URL must remain alive after callback:

```text
tmux target: astro:v2-preview.0
URL: http://127.0.0.1:3003/day/2026-07-08?why=1
```

## 11. Failure cleanup

If any gate after window creation fails:

1. capture only safe failure labels/output;
2. send exactly one `C-c` to `astro:v2-preview.0`;
3. wait up to 15 seconds for launcher awaited shutdown;
4. verify window/pane process exited;
5. kill-window only if pane has already exited but empty window remains;
6. do not kill by broad `pkill`;
7. verify 3003 listener and all owned descendants absent;
8. verify next-env/tsconfig exact preflight snapshots restored;
9. verify tracked tree/index clean and runtime services unchanged;
10. return blocked callback; do not edit code.

Do not stop preview after full success.

## 12. Success callback

```text
READY_STAGE_1_W4_STRICT_REAL_PREVIEW_ARCH_REVIEW
branch: preview/solarsage-v2-human-first-navigator-ux
head: 7d37acbaa31118a8545987a39a5fabe18fbb6e32
origin: 7d37acbaa31118a8545987a39a5fabe18fbb6e32
launcher_unit: <exact count> PASS
typecheck: PASS
prod_guard: PASS
launcher_target: astro:v2-preview.0
launcher_labels: EXACT_3
root_3003: 200
day_shell_3003: 200
api_health_through_3003: 200
managed_preview_tree: PASS_SINGLE_NO_ORPHAN
strict_e2e_chromium: PASS
strict_e2e_mobile: PASS
strict_e2e_total: 2_PASS_0_FAIL_0_SKIP
auth_day_transport_each_project: 200_200
versions_each_project: TODAY_V2_1_FRONTEND_3_CONTENT_10
horizons_each_project: LONG_MEDIUM_FAST
route_interception: ZERO
fixture_mock_18092: ZERO_ABSENT
desktop_day_png: <path,size,sha256>
desktop_why_png: <path,size,sha256>
mobile_day_png: <path,size,sha256>
mobile_why_png: <path,size,sha256>
desktop_network_proof: <path,size,sha256,REDACTED_EXACT>
mobile_network_proof: <path,size,sha256,REDACTED_EXACT>
config_snapshots: EXACT_UNCHANGED
tracked_worktree: CLEAN
index: EMPTY
untracked_scope: EXACT_6_ALLOWED
api_sidecar_frontend_nginx_pid_start: UNCHANGED
listeners_8001_18092: ABSENT
journal_runtime_errors_5xx: ABSENT
journal_privacy: PASS
review_url: http://127.0.0.1:3003/day/2026-07-08?why=1
review_url_state: RUNNING_LEFT_MANAGED
commit_push: NOT_PERFORMED
main_deploy: NOT_STARTED
```

Blocked callback:

```text
BLOCKED_STAGE_1_W4_STRICT_REAL_PREVIEW
failed_gate: <exact section>
safe_observed: <no secrets/payload/human copy>
repository_edits: ZERO
preview_cleanup: PASS_3003_AND_DESCENDANTS_ABSENT
config_restored: PASS
services: UNCHANGED
commit_push: NOT_PERFORMED
```

После callback остановиться. Architect review, evidence doc and docs-only commit
are separate. On success, leave preview running; do not close `v2-preview`.
