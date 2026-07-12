# Stage 1.W0 ТЗ — strict fail-closed real-preview harness stabilization

Дата: 2026-07-13
Ветка: `preview/solarsage-v2-human-first-navigator-ux`
Base HEAD/origin: `ae62ad8ced1865cef2b2b1b3a0382d2e06065ce0`
Parents: `101`, `102`; supersedes unfinished implementation details in `97`–`99` where they conflict
Статус: **AUTHORIZED IMPLEMENTATION WAVE — NO COMMIT / NO PUSH**

## 0. Role and outcome

Ты кодер. Заверши только strict harness checkpoint на текущем dirty worktree.

W0 outcome:

- one-command launcher is structurally correct, unit-tested and leaves no
  tracked config/process garbage;
- E2E is strict and can never pass/skip on V1, 401, locked or missing horizons;
- current stale canonical API produces an **expected fail-closed identity
  diagnostic**, not a green E2E;
- frontend/backend product code remains untouched;
- full frontend/static/build gates pass;
- no commit/push; architect separately reviews and authorizes checkpoint commit.

Do not attempt to solve canonical API V1 in this wave.

## 1. Preflight/current state

Require:

~~~text
branch/local/origin exact base
index empty
3003 and 18092 free
8000/18091 healthy
tracked modified: .gitignore, e2e/README.md, package.json, tsconfig.json
untracked implementation: launcher unit dir, e2e spec, launcher script
architect docs: 97..104
frozen unrelated paths untouched
~~~

If any backend/product/contract file is dirty, stop.

## 2. Exact implementation allowlist

~~~text
.gitignore
package.json
tsconfig.json
scripts/preview-v2-real.mjs
__tests__/scripts/preview-v2-real.test.ts
e2e/real-v2-preview.spec.ts
e2e/README.md
~~~

Architect docs `97`–`104` are not edited by coder.

Forbidden:

~~~text
next-env.d.ts final diff
next.config.mjs
pnpm-lock.yaml
app/** components/** hooks/** lib/**
apps/api/** apps/solarsage/**
packages/contracts/** generated artifacts
e2e/mock-visual/**
systemd/env/main
~~~

## 3. Config paths accepted as-is

Preserve exact intended diffs:

### `.gitignore`

~~~text
# Real V2 local preview Next dist
.next-v2-real-preview/
~~~

### `package.json`

~~~json
"preview:v2:real": "node scripts/preview-v2-real.mjs"
~~~

### `tsconfig.json`

Exactly once:

~~~json
".next-v2-real-preview/types/**/*.ts",
".next-v2-real-preview/dev/types/**/*.ts"
~~~

No launcher runtime code may add/rewrite these globs. They are tracked config.

## 4. Launcher final corrections

### 4.1 Canonical GRACE

Rewrite comments only as needed:

- no pre-GRACE informal header;
- module contract uses multi-line canonical fields;
- module map ends `END_MODULE_MAP`, not `END_MODULE_MODULE`;
- `public_entrypoints` and `semantic_blocks` are list entries;
- real side effects/console labels documented;
- every exported non-trivial helper, `main`, `shutdown` gets function contract;
- exact invariants below reflected truthfully.

### 4.2 Import-safe CLI detection

Use a correct `pathToFileURL(resolve(process.argv[1])).href` style comparison or
equivalent that works for absolute and relative CLI paths. Dynamic Vitest import
must never execute `main`.

### 4.3 File snapshots

Snapshot functions require both files to exist; missing file is a closed startup
error, not null flowing into string helpers.

Store exact:

- UTF-8 bytes/text;
- permission bits `mode & 0o777`.

No `exec`, shell interpolation, Python, git show/checkout/restore/reset.

### 4.4 Exact Next declaration classifier

Current Next 16 generated `next-env.d.ts` contains five non-empty lines:

~~~text
/// <reference types="next" />
/// <reference types="next/image-types/global" />
import "./.next-v2-real-preview/types/routes.d.ts";
// NOTE: This file should not be edited
// see https://nextjs.org/docs/app/api-reference/config/typescript for more information.
~~~

Preserve original EOL style and final newline.

Classifier accepts only:

- exact snapshot -> unchanged;
- exact deterministic generated declaration for real dist -> generated;
- anything else -> unsafe user edit.

No loose `includes`, no arbitrary line-count heuristic. Restore only exact
generated content, using snapshot permission bits. Unsafe content is never
overwritten and causes non-zero shutdown result.

### 4.5 `tsconfig.json` is verify-only at runtime

After readiness, before URL print:

~~~text
current bytes == snapshot bytes -> continue
different -> restore snapshot, terminate child group, fail non-zero
~~~

Launcher never parses/adds/removes globs at runtime. After successful URL print,
shutdown never writes tsconfig, so user edits cannot be clobbered.

### 4.6 Readiness deadline

Fix current infinite-poll bug. Every poll checks `Date.now() >= deadline`.

Inputs injectable for unit:

- fetch implementation;
- now implementation or short real timeout;
- interval/sleep if needed.

Return exact typed/closed result:

~~~text
ready
child_exited(code)
timeout
~~~

No polling continues after resolution.

### 4.7 Platform-safe process group

`spawn`:

~~~text
detached: process.platform !== 'win32'
~~~

Termination helper:

~~~text
POSIX -> kill(-pid, signal)
Windows -> child.kill(signal) or positive PID
~~~

Unit uses injected platform/kill and proves both paths without real kill.

### 4.8 Awaited idempotent shutdown

One shared Promise owns:

1. initial exact-generated next-env restore;
2. SIGTERM child/process group;
3. await already-exited check or exit event up to 5s;
4. SIGKILL if still live;
5. await bounded final exit;
6. final exact-generated next-env restore;
7. timer/listener cleanup;
8. process.exitCode result.

Handle SIGINT/SIGTERM/readiness failure/unexpected child exit/main rejection/
uncaught/unhandled. No premature `process.exit()` after spawn. Preflight before
spawn may return/throw and set exit code normally.

Register synchronous `process.on('exit')` last-chance restore only for exact
generated next-env; never tsconfig.

### 4.9 Actual launcher output

Only after readiness and file verification:

~~~text
[preview:v2:real] Real API: http://127.0.0.1:8000
[preview:v2:real] http://127.0.0.1:3003/day/2026-07-08?why=1
[preview:v2:real] REAL backend preview; no fixture or mock API.
~~~

No env/body/cookie/profile output.

## 5. Unit test matrix

At least 20 behavioral tests, not source-presence substitutes:

1. exact acceptance URL/path/query;
2. buildEnv malicious ambient mock -> canonical 8000;
3. exact development/dist/telemetry;
4. import does not run main;
5. bind free ephemeral port;
6. occupied port false and occupant remains;
7. health 2xx;
8. health non-2xx;
9. health network timeout/error;
10. exact generated next-env classifier;
11. CRLF generated classifier;
12. arbitrary extra line unsafe;
13. wrong dist import unsafe;
14. restore generated exact bytes + original mode;
15. unsafe user edit unchanged on disk;
16. tsconfig equal passes/no write;
17. tsconfig drift restores/fails only in startup helper;
18. readiness success;
19. readiness child exit;
20. readiness deadline terminates polling;
21. POSIX negative PID;
22. Windows/non-POSIX positive child path;
23. package script exact once;
24. gitignore exact once;
25. tsconfig globs exact once;
26. source guard no functional mock/manual API/shell exec/interception.

Use temp dirs/ephemeral ports/injected fetch/kill. `try/finally` cleanup. No
`any`, `require`, unsafe casts, suppressions or fixed service ports in tests.

## 6. E2E must be strict before convergence

Remove all current compatibility branches:

~~~text
no [200,401]
no return on 401
no V1 acceptance
no optional v2/horizons branch
no ready|locked acceptance
no conditional screenshots instead of assertions
~~~

### Required strict flow

- direct `@playwright/test` context, cookies empty;
- project viewports untouched (desktop Chrome, iPhone 13);
- passive request/response only;
- exact auth POST response `200`;
- exact day GET response `200`;
- generated `TodayPayloadWireSchema.parse`;
- exact versions `today.v2.1 / 3 / 10`;
- horizons non-null/order long-medium-fast/unique IDs/non-empty evidence/actions;
- exact acceptance pathname and only `why=1` query;
- no fixture/dev-fixture/18092/mock JSON;
- today-screen ready;
- why toggle expanded;
- backend horizons source ready;
- no unavailable/fixture shell;
- all technical regions visible/id/aria/horizon exact;
- sphere click/repeat selected/expanded/focus/status/details/viewport exact;
- attach project-specific day PNG, Why locator PNG, redacted JSON proof.

Use closed sphere enum narrowing before CSS selector. Do not use Node-global
`CSS.escape`; either static enum-safe selector or locator evaluation without
unsafe interpolation.

Side effects contract must truthfully state screenshot/proof writes to ignored
test-results.

## 7. Expected pre-convergence diagnostic

After launcher smoke, run both projects against current canonical API.

Command is expected non-zero in W0 because runtime is V1. Both project failures
must reach real auth/day `200` and fail at exact version assertion:

~~~text
expected today.v2.1, received today.v1
~~~

If failure is 401, timeout, launcher/config error or conditional pass, W0 is not
ready. Do not weaken assertions.

Record sanitized only:

~~~text
chromium: EXPECTED_FAIL_V1_IDENTITY
mobile:   EXPECTED_FAIL_V1_IDENTITY
auth/day transport: 200/200
mock/interception: zero
~~~

## 8. README

- keep top real preview section;
- no manual uvicorn anywhere;
- explicitly say strict E2E fails until Stage 1 canonical API convergence;
- do not claim a green real preview before S1.W3;
- mock preview remains separate test-only reference.

## 9. Gates

### Green gates

~~~bash
npx vitest run __tests__/scripts/preview-v2-real.test.ts
pnpm typecheck
npx vitest run
pnpm guardrails:prod
pnpm guardrails:frontend
NEXT_DIST_DIR=.next-stage1-w0-build pnpm build
bash scripts/grace/check-markers.sh
git diff --check
~~~

Build cleanup exact patch only; remove only candidate dist. No checkout/reset/
Python file rewrite/git show redirect.

### Managed smoke

- start launcher managed with recorded PID/process group;
- root and `/api/health` 200;
- config clean while running (`tsconfig` only intentional HEAD diff;
  `next-env` no diff);
- 18092 absent;
- terminate SIGTERM + wait;
- 3003 and descendants absent;
- config state unchanged.

### Expected-fail E2E

Run exact strict command and prove both failures are only identity V1.

## 10. Final state

Implementation exact 7 paths. Architect docs `97`–`104` untracked. Index empty.
No 3003/18092. No backend/product/generated/lock/next-config diff. No commit/push.

## 11. Callback

~~~text
READY_FOR_ARCH_REVIEW_STAGE_1_W0
changed_paths: EXACT_7_IMPLEMENTATION
launcher_grace: CANONICAL_COMPLETE
launcher_unit: <exact >=20 PASS>
next_env_exact_generated_restore: PASS
next_env_arbitrary_edit_preserved: PASS
tsconfig_runtime_write: ZERO
readiness_timeout: PASS_BOUNDED
shutdown_no_orphan: PASS_REAL
actual_root: 200
actual_api_health: 200
config_clean_while_running: PASS_REAL
strict_e2e_chromium: EXPECTED_FAIL_V1_IDENTITY_AUTH_DAY_200
strict_e2e_mobile: EXPECTED_FAIL_V1_IDENTITY_AUTH_DAY_200
conditional_skip_or_v1_acceptance: ZERO
route_interception: ZERO
mock_18092: ABSENT
full_vitest: <fresh exact>
typecheck: PASS
prod_guard: PASS
frontend_guard: <exact>
isolated_build: PASS
isolated_dist_removed: YES
grace_gate: <exact baseline>
git_diff_check: PASS
next_env_lock_generated: CLEAN
index: EMPTY
commit: NOT_CREATED
push: NOT_CREATED
broad_destructive_git_after_104: ZERO
unrelated_paths: UNTOUCHED
services_env_main: UNCHANGED
next_wave: NOT_STARTED
~~~

После callback остановиться.
