# Stage 1.W4.R4 — classify active GRACE-slice baseline and finish bounded gates

Дата: `2026-07-13`
Ветка: `preview/solarsage-v2-human-first-navigator-ux`
Accepted base: `7d37acbaa31118a8545987a39a5fabe18fbb6e32`
Amends:

- `122_STAGE_1_W4_R3_REPAIR_DUPLICATED_GRACE_FRONT_LINTER_TZ.md` sections 3–6.

Статус: **AUTHORIZED BASELINE CLASSIFICATION + GATE CONTINUATION — NO COMMIT/PUSH/RESTART/PREVIEW**

## 1. Architect classification

The R3 repair itself is accepted:

```text
scripts/grace_front_lint.py
  syntax/import: PASS
  self-tests: 11 PASS
  duplicate copies: removed
  final lines/mode: 552 / 755
  algorithm and thresholds: unchanged
```

After the repair made the tracked gate executable again, its active repository
slice reported an existing migration baseline:

```text
49 violations across 47 files
GRC001: 3
GRC002: 5
GRC003: 41
```

The violations are limited to the old whitelist from `grace/frontend.paths`:

```text
app/(grace)/**
components/grace/**
lib/grace/**
lib/api/**
packages/contracts/index.ts
```

There is zero path intersection with the exact nine W4 implementation/repair
paths. In particular:

```text
reported: components/grace/TodayScreen.tsx
W4 path:  components/today/today-screen.tsx
```

These are distinct files and directories. No violation is reported for any W4
feature path or for the repaired linter.

The repository could not have had a meaningful green marker gate while the
linter contained a SyntaxError. Fixing 47 legacy files is a separate GRACE
migration wave and is explicitly outside Today V2 preview scope.

Therefore:

- retain the accepted linter repair;
- classify `python3 scripts/grace_front_lint.py --quiet` and
  `bash scripts/grace/check-markers.sh` as **KNOWN ACTIVE-SLICE BASELINE**;
- do not edit, exclude, rename or add markers to the 47 reported files;
- do not weaken marker rules or change `grace/frontend.paths`;
- continue the remaining W4 gates.

## 2. Complete repaired-tool proof

Run after R3 repair:

```bash
bash scripts/grace/check-negative.sh
```

It must pass with exact counts. The earlier pre-repair pass is not sufficient,
because SyntaxError could make negative fixtures fail for the wrong reason.

Also rerun or retain exact evidence for:

```text
python3 -m py_compile scripts/grace_front_lint.py = PASS
python3 scripts/test_grace_front_lint.py = 11 PASS
python3 scripts/grace_front_lint.py --quiet = 49/47 classified baseline
```

## 3. ESLint baseline diagnostic

Run exactly:

```bash
pnpm exec eslint . \
  --ignore-pattern '.next-prod/**' \
  --ignore-pattern '.next-v2-preview/**' \
  --ignore-pattern '.next-v2-real-preview/**'
```

Record exact errors/warnings. Non-zero is expected and classified per 121.

Prove no reported error is introduced by a current W4 diff hunk. For
`components/today/today-screen.tsx`, compare error line numbers with
`git diff -U0 -- components/today/today-screen.tsx`; the known errors are on
unchanged lines 98, 100, 142 and 168. Do not modify the file for lint cleanup.

## 4. Contracts

Run:

```bash
pnpm contracts:generate
git diff --exit-code -- \
  packages/contracts/openapi.json \
  packages/contracts/_generated.ts \
  packages/contracts/_generated.zod.ts
pnpm contracts:check
```

All contract commands must complete successfully and generated diff must be
zero. If generated files change, stop and report; do not accept or stage them.

## 5. Isolated build

Run:

```bash
NEXT_DIST_DIR=.next-stage1-w4-r1-build pnpm build
```

The build must pass. After success remove only the ignored candidate directory
`.next-stage1-w4-r1-build`. Never touch `.next`, `.next-prod`,
`.next-v2-preview` or `.next-v2-real-preview`.

`next-env.d.ts` and `tsconfig.json` must finish with original tracked bytes,
mode and zero git diff. If Next produces only its known exact generated
`next-env.d.ts` declaration for the isolated dist, restore the original tracked
snapshot bytes/mode exactly as already specified by 118/119; preserve any
unrecognized content and stop. Mtime is non-contractual.

## 6. Final witnesses

Confirm:

- exact nine tracked diff paths from 122;
- new access test `<=700` lines;
- repaired linter `<600` lines and mode 755;
- index empty;
- `git diff --check` clean;
- contract generated paths zero diff;
- architect docs 117–123 unchanged;
- frozen unrelated paths untouched;
- ports 3003/8001/18092 absent;
- no `v2-preview` window;
- API/sidecar/frontend/nginx PID and start timestamps unchanged;
- no commit/push/restart/reload.

## 7. Callback

```text
READY_STAGE_1_W4_R4_GATES
r2_change: removed unrelated whole-file SHA guards only
toolchain_repair: duplicate frontend GRACE linter removed; behavior preserved
scope: EXACT_9_PATHS
preview_access_test_lines: N <= 700
grace_linter_lines_mode: 552 / 755
focused_backend: 83 passed
focused_frontend: 121 passed
typecheck: PASS
grace_linter_selftests: 11 PASS
grace_negative_after_repair: PASS (exact counts)
grace_active_slice: CLASSIFIED_BASELINE (49 violations / 47 files; zero W4 intersection)
frontend_eslint: CLASSIFIED_BASELINE (exact errors/warnings; zero W4 diff-hunk regression)
contracts_generate_diff: ZERO
contracts_check: PASS
isolated_build: PASS
next_env_tsconfig: BYTE_MODE_GIT_UNCHANGED
runtime_services: UNCHANGED
ports: 3003/8001/18092 ABSENT
index: EMPTY
commit_push: NOT_PERFORMED
architect_docs: UNCHANGED_117_TO_123
```

Then stop and wait for architect review.
