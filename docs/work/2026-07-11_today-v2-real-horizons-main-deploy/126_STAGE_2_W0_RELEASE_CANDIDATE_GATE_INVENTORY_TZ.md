# Stage 2.W0 — release-candidate gate inventory before main

Дата: `2026-07-13`
Feature branch: `preview/solarsage-v2-human-first-navigator-ux`
Accepted Stage 1 SHA: `7179818b6504be725afa48b513bc1f0a7852e387`
Current main/origin-main: `c9bc36bd9a947566eddb1ffcf5617967c7412676`
Parent plans: `101_TWO_STAGE_COMPLETION_MASTER_PLAN.md`,
`103_STAGE_2_PREVIEW_TO_MAIN_PRODUCTION_MASTER_TZ.md`

Статус: **AUTHORIZED READ-ONLY/GENERATED-IDEMPOTENCE AUDIT — NO CODE EDIT, COMMIT, MAIN OR DEPLOY**

## 1. Purpose

Stage 1 is accepted:

```text
real local V2 preview = today.v2.1 / frontend 3 / content 10
strict chromium + mobile = 2 passed
request-scoped preview access = full/null commercial metadata
feature local/tracking/remote = 7179818...
```

Before any `main` integration, produce the exact Stage 2 release-gate matrix.
This wave discovers the remaining corrective scope; it does not fix failures or
weaken gates.

The audit must answer with evidence:

1. Which contracts/frontend/API/sidecar/shared-package gates are green now?
2. Which failures are real release blockers?
3. Which failures are ignored build-output noise versus tracked source debt?
4. What exact path sets and error-code counts must later correction waves own?
5. Does an isolated production build remain clean and reproducible?
6. Is the feature branch a conflict-free direct descendant of current main?

## 2. Absolute restrictions

- no product/test/config/tooling/docs edit by coder;
- architect document 126 remains byte-identical;
- no git add/commit/push/switch/merge/rebase/pull;
- no env, systemd, nginx, DB or dependency install;
- no service restart/reload;
- no manual uvicorn or frontend production swap;
- no fixture/mock runtime;
- no broad cleanup of frozen untracked paths;
- no deletion of `.next-prod`, `.next`, `.next-v2-real-preview`;
- no `eslint --fix`, formatter or generated diff acceptance;
- do not stop after the first independent failed gate: this is an inventory.

Allowed writes are only commands that are required to prove idempotence and
produce ignored/temporary outputs:

- contract generation that must leave zero tracked diff;
- one isolated ignored build `.next-stage2-w0-audit`;
- `/tmp/stage2-w0-*` diagnostic logs;
- normal test outputs under ignored `test-results`/`playwright-report`.

If a command changes any tracked file unexpectedly, stop further mutating
commands, preserve the diff, and report it. Do not restore with checkout/reset.

## 3. Preflight and Stage 1 preview shutdown

### 3.1 Git topology

Run:

```bash
git fetch origin --prune
git branch --show-current
git rev-parse HEAD
git rev-parse origin/preview/solarsage-v2-human-first-navigator-ux
git rev-parse main
git rev-parse origin/main
git ls-remote --heads origin \
  refs/heads/main \
  refs/heads/preview/solarsage-v2-human-first-navigator-ux
git merge-base main HEAD
git merge-base --is-ancestor origin/main HEAD
git rev-list --count origin/main..HEAD
git rev-list --count HEAD..origin/main
git diff --check origin/main...HEAD
git status --short --branch
```

Required start state:

```text
branch/head/feature remote = preview/... / 7179818...
main/origin-main = c9bc36b...
origin/main is ancestor of feature
feature-only commits = 44
main-only commits = 0
tracked tree/index clean
only five frozen unrelated paths untracked
```

### 3.2 Runtime snapshot

Record service PID/start and canonical listeners. Required active:

```text
sidecar 18091
API 8000, PID 3940721 / Mon 2026-07-13 06:54:31 MSK
frontend 3002
nginx
```

Required absent: 8001 and 18092.

### 3.3 Stop accepted dev preview cleanly

The accepted `astro:v2-preview.0` is currently allowed to be running. Stop it
before release hardening:

1. confirm one managed preview pane and one 3003 listener;
2. send exactly one `C-c` to `astro:v2-preview.0`;
3. wait up to 15 seconds for launcher/Next exit;
4. if pane is dead and empty window remains, kill only that window;
5. prove no preview launcher/Next descendants and no 3003 listener;
6. prove `next-env.d.ts`/`tsconfig.json` bytes, mode and git diff unchanged.

Do not use broad `pkill`/`killall`.

Final runtime state for the audit: 3003/8001/18092 absent; canonical services
unchanged.

## 4. Config snapshots

Before idempotence/build commands record SHA-256, size and mode for:

```text
next-env.d.ts
tsconfig.json
package.json
pnpm-lock.yaml
packages/contracts/openapi.json
packages/contracts/_generated.ts
packages/contracts/_generated.zod.ts
```

Repeat after contracts, after build and at callback. Exact bytes/mode/git state
must return to the starting values. Mtime is non-contractual only for
`next-env.d.ts`/`tsconfig.json`.

## 5. Contract platform gates

Run in this order, recording exit code and exact test/check counts:

```bash
pnpm contracts:generate
git diff --exit-code -- \
  packages/contracts/openapi.json \
  packages/contracts/_generated.ts \
  packages/contracts/_generated.zod.ts
pnpm contracts:check
pnpm contracts:compat
pnpm contracts:fixture:check
```

Also run shared Python contract package tests without installation:

```bash
PYTHONPATH=packages/py-contracts \
  apps/api/.venv/bin/python -m pytest packages/py-contracts/tests/ -q
```

No generated diff is acceptable.

## 6. Frontend gates

Run all independent gates even when a previous non-mutating gate fails:

```bash
npx vitest run
pnpm typecheck
pnpm guardrails:prod
pnpm guardrails:contracts
pnpm guardrails:frontend
pnpm guardrails:secrets
```

For `guardrails:frontend`, save complete stdout/stderr to
`/tmp/stage2-w0-guardrails-frontend.log` and report:

- total errors/warnings;
- ignored build-output errors versus tracked source errors;
- unique tracked source paths;
- per-rule counts;
- exact overlap with `origin/main...HEAD` paths;
- whether any error is on a line added by the feature diff.

Do not infer overlap merely from similar filenames. Use exact repository paths
and zero-context feature diff hunks.

Also run an explicit build-output-excluded diagnostic:

```bash
pnpm exec eslint . \
  --ignore-pattern '.next-prod/**' \
  --ignore-pattern '.next-v2-preview/**' \
  --ignore-pattern '.next-v2-real-preview/**' \
  > /tmp/stage2-w0-eslint-source.log 2>&1
```

Non-zero is evidence to classify, not permission to edit.

For the repaired marker tool:

```bash
python3 -m py_compile scripts/grace_front_lint.py
python3 scripts/test_grace_front_lint.py
python3 scripts/grace_front_lint.py --quiet \
  > /tmp/stage2-w0-grace-source.log 2>&1
bash scripts/grace/check-negative.sh
```

Report exact GRACE code/path counts and feature-diff overlap.

## 7. Backend and sidecar gates

Run from repository root:

```bash
PYTHONPATH=apps/api \
  apps/api/.venv/bin/python -m pytest apps/api/tests/ -q

PYTHONPATH=apps/solarsage \
  apps/solarsage/venv/bin/python -m pytest apps/solarsage/tests/ -q

apps/api/.venv/bin/python -m ruff check apps/api/app apps/api/tests
apps/api/.venv/bin/python -m mypy apps/api/app

apps/solarsage/venv/bin/python -m ruff check \
  apps/solarsage/solarsage apps/solarsage/tests

apps/api/.venv/bin/python -m pip check
apps/solarsage/venv/bin/python -m pip check
```

If a tool is genuinely absent from the owning venv, report `TOOL_ABSENT` and
do not install it in this wave. Test failures must include exact count and path
set, without dumping personal payloads.

Security-focused proof (even though included in full API):

```bash
PYTHONPATH=apps/api apps/api/.venv/bin/python -m pytest \
  apps/api/tests/test_today_preview_transport.py \
  apps/api/tests/test_today_preview_access.py \
  apps/api/tests/test_today_selection_context.py \
  apps/api/tests/test_today_cache_v2_key.py \
  -q
```

Record exact pass count and confirm production/public/ordinary denial cases are
collected.

## 8. Production-import isolation scan

Run structural searches and report exact matches:

```bash
rg -n 'lib/mocks|lib/demo-data|demo-data|dev-fixtures|fixture=' \
  app components hooks lib --glob '!**/*.test.*'

rg -n 'USE_FIXTURES|18092|page\.route|context\.route|routeFromHAR' \
  app components hooks lib apps/api/app apps/solarsage/solarsage
```

Known test/dev-only routes are not automatically failures. Classify each match
as production-import reachable, explicit development fail-closed, or test-only.
Do not edit.

## 9. Isolated release build

Precondition: `.next-stage2-w0-audit` absent. Run:

```bash
NEXT_DIST_DIR=.next-stage2-w0-audit pnpm build
```

Record exact result and route summary. During build, production port 3002 must
remain served by existing `.next-prod` and its PID/start must not change.

After a successful build:

1. inspect only `next-env.d.ts` and `tsconfig.json` diff;
2. if drift is exactly the known Next-generated candidate-dist references,
   restore starting bytes/mode with a minimal `apply_patch` as operational
   hygiene, not a product edit;
3. preserve and stop on any unrecognized drift;
4. remove only `.next-stage2-w0-audit`;
5. prove snapshots and tracked tree restored exactly.

## 10. Final classification

Produce a table-like callback with every command as one of:

```text
PASS
FAIL_FEATURE
FAIL_TRACKED_BASELINE
FAIL_IGNORED_BUILD_OUTPUT
TOOL_ABSENT
NOT_RUN_DUE_TRACKED_DRIFT
```

For every failure include:

- exact command;
- exit code;
- error/test count;
- unique exact path set;
- feature-diff overlap yes/no;
- recommended smallest correction wave ownership.

Final state:

```text
branch/head/remote unchanged at 7179818...
main/origin-main unchanged at c9bc36b...
tracked tree/index clean
only frozen unrelated untracked paths + architect doc 126
3003/8001/18092 absent
canonical service PIDs/start unchanged
no commit/push/restart/deploy
```

## 11. Callback

```text
READY_STAGE_2_W0_GATE_INVENTORY
git_topology: MAIN_ANCESTOR_FEATURE_44_COMMITS_NO_MAIN_ONLY
preview_shutdown: PASS_3003_ABSENT
contracts_generate_diff: ...
contracts_check: ...
contracts_compat: ...
contracts_fixture: ...
py_contracts: ...
vitest_full: ...
typecheck: ...
prod_guard: ...
contracts_guard: ...
frontend_guard: ...
eslint_source: ...
grace_tool_selftests: ...
grace_source: ...
grace_negative: ...
api_full: ...
sidecar_full: ...
api_ruff_mypy: ...
sidecar_ruff: ...
pip_check_api_sidecar: ...
preview_security_focused: ...
production_import_isolation: ...
isolated_build: ...
config_generated_snapshots: EXACT_RESTORED
release_blocker_waves: <exact path/rule groups>
runtime_services: UNCHANGED
ports: 3003/8001/18092 ABSENT
tracked_index: CLEAN_EMPTY
commit_push_main_deploy: NOT_PERFORMED
```

Then stop and wait for architect review.
