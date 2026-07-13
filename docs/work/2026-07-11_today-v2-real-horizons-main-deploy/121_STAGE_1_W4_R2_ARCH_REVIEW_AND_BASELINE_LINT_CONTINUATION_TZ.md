# Stage 1.W4.R2 — architect review: remove frozen-file hashes and finish bounded gates

Дата: `2026-07-13`
Ветка: `preview/solarsage-v2-human-first-navigator-ux`
Accepted base: `7d37acbaa31118a8545987a39a5fabe18fbb6e32`
Amends:

- `119_STAGE_1_W4_R1_REQUEST_SCOPED_FULL_ACCESS_PREVIEW_TZ.md`;
- `120_STAGE_1_W4_R1_ARCH_ERRATA_REPO_ROOT_FULL_API_TZ.md`.

Статус: **AUTHORIZED R2 CORRECTION AND GATE CONTINUATION — NO COMMIT/PUSH/RESTART/PREVIEW**

## 1. Architect verdict on R1

The implementation direction is accepted:

```text
real AccessService result
  + same immutable TodaySelectionContext
  -> pure request-scoped resolver
  -> exact authorized LOCAL_DEV_PREVIEW receives full/null access
  -> ordinary/global/denied requests preserve the original access object
```

Accepted properties already proven by the coder:

- exact eight implementation/test paths only;
- no access-ledger, settings, DB, auth or global mutation;
- no public schema/enum change;
- request overlap is isolated;
- preview access is `full` with all commercial metadata null;
- real subscription/referral semantics remain distinguishable in the adapter;
- `TrialBanner` is trial-only;
- strict E2E now requires exact backend access and absence of `access-card`;
- focused backend: `83 passed`;
- corrected full backend: `1405 passed, 4 skipped`;
- focused frontend: `121 passed`;
- full Vitest: `1067 passed`;
- typecheck and production guard passed.

No redesign of the resolver or route integration is authorized in R2.

## 2. Required architecture correction

The new test currently imports `hashlib` and freezes complete SHA-256 hashes of:

```text
apps/api/app/api/calendar.py
lib/grace/api/client.ts
```

This is rejected. Unit tests must not make unrelated legitimate future edits to
whole files fail merely because their bytes changed. Exact wave scope is an
architect/git acceptance property, not a runtime unit-test contract.

In `apps/api/tests/test_today_preview_access.py` only:

1. remove `import hashlib`;
2. remove `calendar_path` and `client_path` if they become unused;
3. remove both whole-file `sha256(...)` assertions;
4. update the module map, function purpose, side effects and nearby wording so
   they no longer claim frozen calendar/client hashes or reads;
5. retain the useful AST/static assertions over the two owned feature files:
   `day.py` and `today_preview_access.py`;
6. keep the file at `<=700` lines;
7. do not replace the hashes with mtimes, byte snapshots, `git` subprocesses or
   other whole-file fingerprints.

Do not edit `calendar.py` or `lib/grace/api/client.ts`. Their non-modification is
proved at callback by the exact git allowlist.

## 3. `guardrails:frontend` classification

The literal command failed:

```text
pnpm guardrails:frontend
ESLint exit 1
10757 problems
```

Architect independently removed only ignored build-output noise from the
diagnostic invocation:

```bash
pnpm exec eslint . \
  --ignore-pattern '.next-prod/**' \
  --ignore-pattern '.next-v2-preview/**' \
  --ignore-pattern '.next-v2-real-preview/**'
```

The repository still reports the pre-existing baseline:

```text
64 errors
5 warnings
```

The four errors reported in the only touched lint-covered product file,
`components/today/today-screen.tsx`, are on unchanged lines:

```text
98   calendarLunar unused
100  importantToday unused
142  FrameRequestCallback undefined
168  FrameRequestCallback undefined
```

R1 changes in that file are contract comments and the trial-card condition near
line 254. Therefore the failed aggregate ESLint command is classified as known
repository baseline, not a W4.R1 regression.

R2 must not:

- edit `eslint.config.mjs`;
- delete or modify `.next`, `.next-prod`, `.next-v2-preview` or
  `.next-v2-real-preview` merely to manufacture a green lint result;
- fix unrelated source/docs/e2e lint debt;
- add eslint-disable comments;
- rename unrelated props/globals;
- expand the implementation allowlist.

After the required test correction, rerun the build-output-excluded diagnostic
above and record its exact counts. Non-zero is expected. Also prove that every
ESLint error in a touched lint-covered file is outside the current diff hunks.

This R2 explicitly authorizes continuation past that classified baseline.

## 4. Required continuation gates

Run from `/opt/solarsage-astro` after the correction.

### 4.1 Mechanical and focused regression

```bash
git diff --check
wc -l apps/api/tests/test_today_preview_access.py

PYTHONPATH=apps/api apps/api/.venv/bin/python -m pytest \
  apps/api/tests/test_today_preview_access.py \
  apps/api/tests/test_today_preview_transport.py \
  apps/api/tests/test_access_service.py \
  -q

npx vitest run \
  __tests__/lib/adapt-payload.test.ts \
  __tests__/components/TodayScreen.test.tsx \
  __tests__/components/TodayScreen.v2-downstream.test.tsx \
  __tests__/scripts/preview-v2-real.test.ts
```

Zero failures required. The existing 997-line transport test remains untouched.

### 4.2 Execute the non-ESLint frontend guard components explicitly

The full aggregate command has already been run and classified. Execute its
remaining components directly:

```bash
pnpm typecheck
bash scripts/grace/check-markers.sh
bash scripts/grace/check-negative.sh
```

All three must pass. Do not rerun full Vitest or full backend unless the R2 edit
somehow touches more than the authorized test-only correction; it must not.

### 4.3 Contracts

```bash
pnpm contracts:generate
git diff --exit-code -- \
  packages/contracts/openapi.json \
  packages/contracts/_generated.ts \
  packages/contracts/_generated.zod.ts
pnpm contracts:check
```

Generation must produce zero generated diff. Public contracts are unchanged.

### 4.4 Isolated build

```bash
NEXT_DIST_DIR=.next-stage1-w4-r1-build pnpm build
```

On success remove only `.next-stage1-w4-r1-build`. Do not touch any running or
previous preview build directory. Prove tracked bytes/mode and git diff for
`next-env.d.ts` and `tsconfig.json` are unchanged; mtime is not contractual.

## 5. Exact final scope

Tracked implementation diff remains exactly these eight paths:

```text
apps/api/app/services/today_preview_access.py
apps/api/app/api/day.py
apps/api/tests/test_today_preview_access.py
lib/adapters/today-payload.ts
__tests__/lib/adapt-payload.test.ts
components/today/today-screen.tsx
__tests__/components/TodayScreen.test.tsx
e2e/real-v2-preview.spec.ts
```

Index remains empty. No commit/push, no service restart/reload, no 3003 start.

Architect docs 117–121 remain byte-identical after task delivery. Frozen
unrelated paths remain untouched:

```text
.grace/
artifacts/design/
docs/superpowers/plans/2026-07-05-fix-day-route-auth-build.md
grace.db
skills/
```

Runtime final witness:

```text
3003/8001/18092 absent
v2-preview tmux window absent
API/sidecar/frontend/nginx PID and start timestamp unchanged
```

## 6. Callback

Return one exact summary containing:

```text
READY_STAGE_1_W4_R2_ARCH_REVIEW
r2_change: removed unrelated whole-file SHA guards only
scope: EXACT_8_PATHS
test_file_lines: N <= 700
focused_backend: ...
focused_frontend: ...
typecheck: PASS
grace_markers: PASS
grace_negative: PASS
frontend_eslint: CLASSIFIED_BASELINE (exact errors/warnings)
contracts_generate_diff: ZERO
contracts_check: PASS
isolated_build: PASS
next_env_tsconfig: BYTE_MODE_GIT_UNCHANGED
runtime_services: UNCHANGED
ports: 3003/8001/18092 ABSENT
index: EMPTY
commit_push: NOT_PERFORMED
architect_docs: UNCHANGED_117_TO_121
```

Then stop and wait for architect review.
