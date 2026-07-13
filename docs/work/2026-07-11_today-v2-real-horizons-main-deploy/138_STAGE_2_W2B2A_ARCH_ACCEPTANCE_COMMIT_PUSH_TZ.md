# Stage 2.W2B-2A — architect acceptance, exact commit and push

Дата: `2026-07-13`
Branch/base: `preview/solarsage-v2-human-first-navigator-ux` /
`cf37dc951dd385534095b6f64d6e64582a92edd0`
Accepted implementation:
`137_STAGE_2_W2B2A_MECHANICAL_UNUSED_AND_GENERATED_DIRECTIVE_TZ.md`

Статус: **ARCHITECT ACCEPTED — AUTHORIZED EXACT COMMIT/PUSH ONLY**

## 1. Accepted review evidence

Architect independently reviewed all 25 diffs and accepts:

```text
27 extension unused errors            removed through dead import/binding cleanup
public CalendarScreen access prop      preserved in Props
public TodayScreen optional props      preserved in Props
toast action discriminants             same literal runtime behavior via pure type map
generated Zod directive                removed at generate.sh source
_generated.zod.ts diff                 first line only
_generated.ts/OpenAPI drift            zero
remaining ESLint                       6 errors / 5 warnings / 6 paths
typecheck                              PASS
full Vitest                            1067 PASS
contract semantic tests               110 PASS
fixture normalization                  PASS
production guard                      PASS
working diff check                    PASS
runtime/services                      unchanged
ports 3003/8001/18092                 absent
```

No further edit is authorized in this wave.

## 2. Mandatory preflight

Before staging:

1. read this document completely;
2. fetch origin without merge/rebase;
3. prove branch/local/tracking/remote feature remain at the exact base SHA;
4. prove `main`/`origin/main` remain
   `c9bc36bd9a947566eddb1ffcf5617967c7412676` and are an ancestor;
5. prove index empty;
6. prove tracked diff is exactly the 25 accepted implementation paths from
   document 137;
7. prove docs 137 and 138 are the only task docs untracked;
8. prove only five frozen unrelated untracked paths otherwise remain;
9. prove generated hashes/diffs and runtime invariants still match acceptance.

Stop on mismatch. No source edit, reset, rebase, force push, runtime operation
or W2B-2B work.

## 3. Exact staging

Stage the exact 25 paths listed in section 3 of document 137 plus exactly:

```text
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/137_STAGE_2_W2B2A_MECHANICAL_UNUSED_AND_GENERATED_DIRECTIVE_TZ.md
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/138_STAGE_2_W2B2A_ARCH_ACCEPTANCE_COMMIT_PUSH_TZ.md
```

Use all 27 explicit file paths; never `git add .`, `-A` or directory staging.

Before commit require:

```text
staged count                    exactly 27
staged set                      exact accepted 25 + docs 137/138
unstaged tracked diff           empty
frozen paths in index           zero
git diff --cached --check       PASS
generated Zod staged diff       first-line removal only
OpenAPI/_generated.ts staged    unchanged/not staged
```

If an architect-doc EOF problem appears, stop for architect correction.

## 4. Commit and post-commit gates

Create one commit with exact subject:

```text
chore(frontend): clean mechanical lint residue
```

After commit and before push run:

```bash
pnpm typecheck
npx vitest run
pnpm contracts:check
pnpm guardrails:prod
git diff --check origin/main...HEAD
```

Canonical `pnpm contracts:check` must now pass completely with 110 tests and
zero generated drift because the accepted generated artifact is in HEAD.

Run aggregate ESLint as expected non-zero JSON:

```bash
pnpm exec eslint . -f json > /tmp/stage2-w2b2a-accepted-eslint.json
```

Require exact result:

```text
6 errors / 5 warnings / 6 paths
unused errors = 0
unused directives = 0
no-empty = 5 errors
require-yield = 1 error
react-hooks/exhaustive-deps = 5 warnings
parsing/fatal/unmatched/build-doc findings = 0
```

Do not fix the remaining findings in this commit.

## 5. Normal push and final state

Push normally to the existing feature branch, never force. Then prove:

```text
local HEAD = tracking ref = remote feature SHA
tracked worktree clean
index empty
only five frozen unrelated untracked paths remain
main untouched
runtime/env/systemd untouched
3003/8001/18092 absent
```

Do not begin W2B-2B before callback.

## 6. Callback

```text
PUSHED_STAGE_2_W2B2A_MECHANICAL_SOURCE
commit: <sha> chore(frontend): clean mechanical lint residue
staged_scope: EXACT_27
unused_errors: ZERO
generated_directive_warning: ZERO_VIA_GENERATOR_SOURCE
contracts_check: 110 PASS_ZERO_DRIFT
remaining_expected: 6 errors / 5 warnings / 6 paths
typecheck: PASS
vitest_full: 1067 PASS
prod_guard: PASS
feature_diff_check: PASS_ZERO
head_tracking_remote: EQUAL
tracked_index: CLEAN_EMPTY
runtime_services: UNCHANGED
ports: 3003/8001/18092 ABSENT
main_deploy: NOT_STARTED
```

Then stop.
