# Stage 2.W4.R1 — restore Today redirect GRACE anchor contract

Дата: `2026-07-13`

Branch/base: `preview/solarsage-v2-human-first-navigator-ux` /
`42a0c5dba7d476b156e0ff17d4fdccb5a22aaa93`.

Parent:
`170_STAGE_2_W4_FINAL_RELEASE_CANDIDATE_TZ.md`.

Статус: **AUTHORIZED ONE-LINE COMMENT-ONLY CORRECTION — NO COMMIT/PUSH, NO RC RUNTIME**

Работай лично в `tmux astro:0.0`, без subagents/delegation/background coding.

## 1. Confirmed blocker and architectural decision

The W4 proof stopped correctly before build/runtime because full Vitest produced:

```text
Test Files  1 failed | 96 passed (97)
Tests       1 failed | 1066 passed (1067)

FAIL __tests__/grace-discipline.test.ts
GRACE Marker Discipline > should reject missing GRACE_ANCHOR in critical sections
```

The exact critical path is:

```text
app/(grace)/today/page.tsx
```

`origin/main` carried:

```text
// GRACE_ANCHORS: [TODAY_REDIRECT]
```

W2C commit `6f41b5c2` replaced the old minimal header with a truthful module
contract/map but accidentally omitted the required `GRACE_ANCHORS` declaration.
The runtime redirect body remained unchanged. The current module map names the
one conceptual region `COMPATIBILITY_REDIRECT`, so the restored declaration
must use that current truthful name.

This is a real public test-contract regression, not flaky behavior. Do not
change or weaken the test.

## 2. Entry gate

Require before editing:

```text
branch                         preview/solarsage-v2-human-first-navigator-ux
HEAD/upstream/remote feature   42a0c5dba7d476b156e0ff17d4fdccb5a22aaa93
main/origin/remote main        c9bc36bd9a947566eddb1ffcf5617967c7412676
tracked worktree               clean
index                          empty
3003/3010/8001/18092           absent
canonical services             unchanged and healthy
```

Allowed untracked state:

```text
.grace/
artifacts/design/
docs/superpowers/plans/2026-07-05-fix-day-route-auth-build.md
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/170_STAGE_2_W4_FINAL_RELEASE_CANDIDATE_TZ.md
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/171_STAGE_2_W4_R1_TODAY_REDIRECT_GRACE_ANCHOR_TZ.md
grace.db
skills/
```

Stop on any other tracked/untracked/task/runtime state. Do not reset, restore,
checkout, stash, switch, pull or rebase.

## 3. Exact edit allowlist and exact patch

Edit exactly one tracked path:

```text
app/(grace)/today/page.tsx
```

Add exactly one comment line after the existing `ROLE` line and before the
closing banner line:

```ts
// GRACE_ANCHORS: [COMPATIBILITY_REDIRECT]
```

The resulting four-line banner must be exactly:

```ts
// ############################################################################
// AI_HEADER: APP_TODAY_REDIRECT_PAGE — legacy /today compatibility redirect.
// ROLE: Server Next.js page called by /today; redirects all requests to the canonical migrated /day/today route.
// GRACE_ANCHORS: [COMPATIBILITY_REDIRECT]
// ############################################################################
```

Do not change any other byte in the file. In particular preserve exactly:

- module contract/map content and IDs;
- semantic block name `COMPATIBILITY_REDIRECT`;
- import formatting;
- default export name;
- `redirect("/day/today")` target and behavior;
- current newlines and file mode.

Do not add START_BLOCK markers, function contracts, whitespace cleanup or a
second anchor. Do not edit tests, linter, manifest, config or docs 170/171.

## 4. Absolute prohibitions

- no runtime/product behavior change;
- no test expectation change, skip, conditional or snapshot update;
- no formatter or autofix;
- no `git add`, commit or push;
- no build, 3003 preview, 3010 candidate or HMAC smoke in this wave;
- no service/env/nginx/systemd/DB operation;
- no frozen-path cleanup.

## 5. Exact diff and semantic-equivalence proof

After the patch require:

```bash
git diff --name-only
git diff -- 'app/(grace)/today/page.tsx'
git diff --check
git diff --cached --name-only
```

Expected:

```text
tracked diff paths    exact one
diff                  exact one added comment line
index                 empty
diff check            pass
```

Prove comment-stripped executable source is unchanged. A temporary parser may
remove line comments and blank lines from HEAD/current copies; resulting import
and function body must be byte-identical. Do not write a repository artifact.

## 6. Focused public-contract gates

Run:

```bash
npx vitest run \
  __tests__/grace-discipline.test.ts \
  __tests__/app/today-redirect.test.ts

python3 scripts/test_grace_front_lint.py
python3 scripts/grace_front_lint.py 'app/(grace)/today/page.tsx'
bash scripts/grace/check-negative.sh
```

Require:

```text
focused Vitest        2 files / 5 PASS
GRACE linter tests    all PASS with exact reported count
exact path lint       PASS / zero violations
negative gate         PASS
```

The focused discipline test must now see the literal declaration. Do not make
it pass by editing `__tests__/grace-discipline.test.ts`.

## 7. Full frontend release gates

Run all:

```bash
npx vitest run
pnpm typecheck
pnpm guardrails:prod
pnpm guardrails:frontend
pnpm guardrails:secrets
```

Require:

```text
Vitest                 97 files / 1067 PASS / 0 failed
typecheck              PASS
prod guard             PASS
frontend guard         PASS
secrets guard          PASS
```

Also run:

```bash
git diff --check origin/main...HEAD
git diff --check
```

Both pass. The already accepted W4 contract/backend/static evidence remains
read-only evidence; do not rerun runtime sections 12–14 here.

## 8. Final state and callback

Require:

```text
HEAD/upstream/remote feature   42a0c5d... unchanged
tracked diff                   exact one comment line / one path
index                          empty
untracked                      frozen five + docs 170/171
runtime services               unchanged
3003/3010/8001/18092           absent
commit/push                    not performed
main/deploy                    not started
```

Callback:

```text
READY_STAGE_2_W4_R1_ARCH_REVIEW
base_head: 42a0c5dba7d476b156e0ff17d4fdccb5a22aaa93
root_cause: W2C_HEADER_REPLACEMENT_DROPPED_REQUIRED_GRACE_ANCHOR
edit_scope: EXACT_1_PATH_1_COMMENT_LINE
anchor: COMPATIBILITY_REDIRECT
redirect_runtime: BYTE_EQUIVALENT_AFTER_COMMENT_STRIP
focused_vitest: 2_FILES_5_PASS
full_vitest: 97_FILES_1067_PASS
typecheck: PASS
grace_front_selftests: <exact count>_PASS
grace_exact_path: PASS
grace_negative: PASS
prod_guard: PASS
frontend_guard: PASS
secrets_guard: PASS
tracked_diff: EXACT_ONE_COMMENT_LINE
index: EMPTY
frozen_untracked: PRESERVED
runtime_services: UNCHANGED
ports: 3003_3010_8001_18092_ABSENT
commit_push: NOT_PERFORMED
rc_runtime_resume: NOT_STARTED
main_deploy: NOT_STARTED
```

Then stop for architect review. Do not commit or resume document 170 yourself.
