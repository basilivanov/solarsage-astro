# Stage 2.W2A — architect acceptance, exact commit and push

Дата: `2026-07-13`
Branch/base: `preview/solarsage-v2-human-first-navigator-ux` /
`58c9136b97fde78f4ad776bcd83c8591481ecde4`
Parents:

- `131_STAGE_2_W2A_ESLINT_PERIMETER_AND_RUNTIME_GLOBALS_TZ.md`;
- `132_STAGE_2_W2A_ARCH_REVIEW_R1_TYPESCRIPT_PARSER_COVERAGE_TZ.md`.

Статус: **ARCHITECT ACCEPTED — AUTHORIZED EXACT COMMIT/PUSH ONLY**

## 1. Accepted implementation

Architect independently reviewed the one-file implementation diff. It contains
exactly 31 additions in:

```text
eslint.config.mjs
```

Accepted behavior:

- generated Next trees matching `.next-*/**`, historical `docs/**` captures,
  `playwright-report/**` and `test-results/**` are outside the authored-source
  lint perimeter;
- existing `.next/**` and all previous ignores remain intact;
- no authored application, component, library, hook, test, e2e, package or
  root-config path was added to ignores;
- standard DOM/modern runtime globals `URL`, `Event`, `Node`, `NodeFilter`,
  `FrameRequestCallback` and `structuredClone` are declared read-only;
- `Buffer` is scoped only to authored tests, e2e and root config files;
- every matched authored `*.ts` and `*.tsx` path receives
  `@typescript-eslint/parser` with latest/module/JSX parser options;
- existing recommended, unused-variable, React Hooks and GRACE rules retain
  their severities;
- no source suppression, eslint-disable comment or runtime behavior change was
  introduced.

Independent/config evidence:

```text
config syntax                         PASS
TypeScript parsing errors             0
unmatched authored TS/TSX             0
build/docs/report findings            0
listed standard-global false no-undef 0
real source remainder                 152 errors / 6 warnings / 55 paths
```

Exact real remainder classification for W2B:

```text
no-unused-vars                  93 errors
no-undef                        53 errors
no-empty                         5 errors
require-yield                    1 error
react-hooks/exhaustive-deps      5 warnings
unused eslint-disable directive  1 warning
```

Regression evidence already accepted:

```text
typecheck                         PASS
focused Vitest                    33 PASS
contracts:check                  110 PASS
guardrails:prod                   PASS
git diff --check                 PASS
runtime/services                 unchanged
ports 3003/8001/18092            absent
```

No further implementation edit is authorized in this wave.

## 2. Mandatory preflight

Before staging:

1. read this document completely;
2. fetch origin without merge or rebase;
3. prove current branch is exactly
   `preview/solarsage-v2-human-first-navigator-ux`;
4. prove local HEAD, tracking ref and remote branch are still exactly
   `58c9136b97fde78f4ad776bcd83c8591481ecde4`;
5. prove `main` and `origin/main` are still
   `c9bc36bd9a947566eddb1ffcf5617967c7412676` and this SHA is a direct
   ancestor of feature HEAD;
6. prove index empty;
7. prove the only tracked worktree diff is `eslint.config.mjs` and its diff is
   byte-for-byte the implementation reviewed above;
8. prove architect docs 131, 132 and 133 are the only task documents currently
   untracked;
9. prove frozen unrelated paths remain untouched and untracked:

```text
.grace/
artifacts/design/
docs/superpowers/plans/2026-07-05-fix-day-route-auth-build.md
grace.db
skills/
```

10. prove canonical services are unchanged and 3003/8001/18092 are absent.

If any branch SHA, scope, diff or runtime invariant differs, stop without
staging, committing or pushing and return the discrepancy. Never rebase, reset,
force-push or edit around a mismatch.

## 3. Exact staging

Stage only these four explicit paths:

```text
eslint.config.mjs
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/131_STAGE_2_W2A_ESLINT_PERIMETER_AND_RUNTIME_GLOBALS_TZ.md
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/132_STAGE_2_W2A_ARCH_REVIEW_R1_TYPESCRIPT_PARSER_COVERAGE_TZ.md
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/133_STAGE_2_W2A_ARCH_ACCEPTANCE_COMMIT_PUSH_TZ.md
```

Use explicit `git add -- <path>...`. Never use `git add .`, `git add -A` or a
directory-wide add.

Before commit require:

```text
staged path count        exactly 4
staged path set          exactly the four paths above
unstaged tracked diff    empty
git diff --cached --check PASS
index contains frozen paths NO
```

Do not edit any file during this acceptance wave. If an EOF/diff-check problem
is discovered, stop for architect correction rather than changing an
architect-owned document.

## 4. Commit and post-commit proof

Create exactly one commit with subject:

```text
chore(frontend): establish eslint source perimeter
```

After commit and before push, require:

```bash
node --check eslint.config.mjs
pnpm typecheck
npx vitest run __tests__/guardrails/preview-isolation.test.ts \
  __tests__/scripts/preview-v2-real.test.ts
pnpm contracts:check
pnpm guardrails:prod
git diff --check origin/main...HEAD
```

Also rerun aggregate ESLint as a diagnostic while preserving its expected
non-zero exit status:

```bash
pnpm exec eslint . -f json > /tmp/stage2-w2a-accepted-eslint.json
```

Parse the JSON rather than treating the expected exit code 1 as a wave failure.
Required exact result:

```text
152 errors / 6 warnings / 55 paths
parsing errors = 0
ignored/no-matching-config authored TS/TSX = 0
build/docs/report paths = 0
```

If the count or classification differs, do not push. Return the exact delta.
No source correction belongs in this commit.

## 5. Normal push and final equality

Push normally to the existing feature branch. Never force. After push prove:

```text
local HEAD = tracking ref = git ls-remote feature SHA
tracked worktree = clean
index = empty
only the five frozen unrelated untracked paths remain
main = untouched
runtime/env/systemd = untouched
3003/8001/18092 = absent
```

Do not start W2B, change runtime, switch branch or deploy in this wave.

## 6. Callback

Return exactly the following evidence shape, then stop:

```text
PUSHED_STAGE_2_W2A_ESLINT_PERIMETER
commit: <sha> chore(frontend): establish eslint source perimeter
staged_scope: EXACT_4
config_syntax: PASS
typescript_parser_coverage: PASS_ALL_AUTHORED_TS_TSX
parsing_errors: ZERO
unmatched_authored_typescript: ZERO
build_docs_findings: ZERO
remaining_real_source: 152 errors / 6 warnings / 55 paths
typecheck: PASS
focused_tests: 33 PASS
contracts_check: 110 PASS
prod_guard: PASS
feature_diff_check: PASS_ZERO
head_tracking_remote: EQUAL
tracked_index: CLEAN_EMPTY
runtime_services: UNCHANGED
ports: 3003/8001/18092 ABSENT
main_deploy: NOT_STARTED
```
