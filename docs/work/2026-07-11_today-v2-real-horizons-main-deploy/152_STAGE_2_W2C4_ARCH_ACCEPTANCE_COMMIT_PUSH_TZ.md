# Stage 2.W2C-4 — architect acceptance, exact commit and push

Дата: `2026-07-13`
Branch/base: `preview/solarsage-v2-human-first-navigator-ux` /
`ddd1fab24ba31bab913763cefff38bb75de1f1c6`
Accepted implementation:
`151_STAGE_2_W2C4_GRACE_LIBRARY_TRUTHFUL_PREAMBLES_TZ.md`.
Prepared next wave:
`153_STAGE_2_W3A_FEATURE_API_RUFF_CORRECTION_TZ.md`.

Статус: **ARCHITECT ACCEPTED — AUTHORIZED EXACT COMMIT/PUSH ONLY**

Исполнитель работает лично. Запрещены subagents, delegation, `delegate_*`,
background coding/review tasks и использование их результатов как evidence.

## 1. Accepted evidence

Architect independently reviewed the complete three-file diff and reran every
material gate. Accepted evidence:

```text
tracked implementation scope          exact 3 lib/grace files
changed executable lines              zero
comment/blank-only diff               PASS 3/3
runtime suffix byte comparison        unchanged 3/3
imports/exports/interfaces/functions  unchanged
hook dependencies                     unchanged
event names/log metadata              unchanged
timeout/status/redirect/error copy    unchanged
module IDs                            unique and paired 3/3
contract truthfulness                 PASS 3/3
authorized GRACE                      PASS 3/3
GRACE linter self-tests               11 PASS
strict negative harness               6 PASS / 0 FAIL exact reasons
ESLint                                zero errors / zero warnings
typecheck                             PASS
targeted Vitest                       3 files / 17 tests PASS
full marker                           0 violations / 0 failing
full marker green/checked             47 / 47
aggregate frontend guard              PASS exit zero
git diff check                        PASS
index                                 empty
runtime/services                      unchanged
ports 3003/8001/18092                 absent
```

No correction wave is required. No file content edit is authorized in this
packet.

## 2. Mandatory preflight

Before staging:

1. completely read 141, 151, 152 and 153;
2. run `git fetch origin` without merge/rebase;
3. prove current branch exactly
   `preview/solarsage-v2-human-first-navigator-ux`;
4. prove local HEAD = tracking = remote feature =
   `ddd1fab24ba31bab913763cefff38bb75de1f1c6`;
5. prove `main` and `origin/main` remain
   `c9bc36bd9a947566eddb1ffcf5617967c7412676` and are ancestors of HEAD;
6. prove index empty;
7. prove tracked diff is exactly the three implementation paths in section 3;
8. re-prove comment-only and runtime-suffix equivalence 3/3;
9. prove 152 and 153 are the only task docs untracked;
10. prove only the five frozen unrelated paths otherwise remain untracked;
11. prove runtime services unchanged and ports `3003`, `8001`, `18092` absent.

Stop on any mismatch. Never reset, restore, checkout paths, stash, amend,
rebase or force-push. Do not edit any file during this wave. On whitespace,
scope or evidence mismatch, stop for architect correction.

## 3. Exact implementation paths

```text
lib/grace/hooks/useCalendar.ts
lib/grace/hooks/useDay.ts
lib/grace/index.ts
```

## 4. Exact task-document paths

```text
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/152_STAGE_2_W2C4_ARCH_ACCEPTANCE_COMMIT_PUSH_TZ.md
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/153_STAGE_2_W3A_FEATURE_API_RUFF_CORRECTION_TZ.md
```

Coder must stage both documents exactly as written and must not edit them.

## 5. Exact staging set

Stage only exact five explicit paths:

```text
3 implementation paths from section 3
2 task-document paths from section 4
```

Use explicit path arguments. Forbidden: broad `git add`, directory staging,
wildcards or staging frozen/unrelated files.

Before commit require:

```text
staged count                    5
staged set                      exact 3 implementation + exact 2 docs
unstaged tracked diff           empty
cached executable changes       zero
cached runtime suffix proof     unchanged 3/3
cached diff check               PASS
frozen/unrelated in index       zero
```

## 6. Exact commit

Create exactly one normal commit with exact subject:

```text
chore(grace): complete frontend contract migration
```

After commit require:

```text
parent                          ddd1fab24ba31bab913763cefff38bb75de1f1c6
subject                         exact
changed paths                   exact 5
implementation paths            exact 3
task docs                       exact 2
tracked worktree                clean
index                           empty
```

No amend, fixup, second commit or W3A implementation.

## 7. Mandatory post-commit gates

### 7.1. Exact slice and negative harness

```bash
python3 scripts/test_grace_front_lint.py
python3 scripts/grace_front_lint.py \
  lib/grace/hooks/useCalendar.ts \
  lib/grace/hooks/useDay.ts \
  lib/grace/index.ts
bash scripts/grace/check-negative.sh
```

Require: self-tests 11 PASS; three authorized files clean; negative harness
6 PASS / 0 FAIL with exact rule reasons.

### 7.2. Static and targeted regression

```bash
pnpm lint
pnpm typecheck
npx vitest run \
  __tests__/hooks/useCalendar.test.ts \
  __tests__/hooks/useDay.test.ts \
  __tests__/app/day-page.test.tsx
```

Require: ESLint zero errors/warnings; typecheck PASS; exact 3 files / 17 tests
PASS.

### 7.3. Completed marker and aggregate frontend gate

Run the full marker gate and require exactly:

```text
violations=0
failing_paths=0
green_paths=47
checked_paths=47
```

Then run:

```bash
pnpm guardrails:frontend
```

Require exit zero for all sections: ESLint, typecheck, marker 47/47 and strict
negative tests 6/0.

Finally:

```bash
git diff --check origin/main...HEAD
```

Require PASS_ZERO. Production build/full Vitest remain final-RC gates, not
part of this comment-only commit packet.

## 8. Normal push and final equality

After every post-commit gate passes:

1. normal push the existing feature branch; never force/change upstream;
2. prove local HEAD = tracking = remote feature SHA;
3. prove exact parent, subject and five-path commit set;
4. prove tracked worktree clean and index empty;
5. prove only five frozen unrelated untracked paths remain;
6. prove `main`/`origin/main` untouched and still ancestors;
7. prove env/systemd/nginx/database/runtime untouched;
8. prove ports `3003`, `8001`, `18092` absent.

Do not begin W3A before callback and a separate architect message. Committed
doc 153 is traceability, not self-authorization.

## 9. Frozen unrelated paths

```text
.grace/
artifacts/design/
docs/superpowers/plans/2026-07-05-fix-day-route-auth-build.md
grace.db
skills/
```

## 10. Required callback

```text
PUSHED_STAGE_2_W2C4_FRONTEND_GRACE_COMPLETE
commit: <sha> chore(grace): complete frontend contract migration
staged_scope: EXACT_5
implementation_scope: EXACT_3_LIB_GRACE_FILES
task_docs: EXACT_2
comment_only_equivalence: PASS_3
runtime_suffix_hashes: UNCHANGED_3
module_ids: UNIQUE_AND_PAIRED_3
grace_linter_self_tests: 11_PASS
authorized_paths_grace: PASS_3
negative_harness: 6_PASS_0_FAIL_EXACT_REASONS
eslint: PASS_ZERO_ERRORS_ZERO_WARNINGS
typecheck: PASS
targeted_tests: 3_FILES_17_PASS
remaining_grace: 0_VIOLATIONS_0_FAILING_47_GREEN_47_CHECKED
guardrails_frontend: PASS
feature_diff_check: PASS_ZERO
head_tracking_remote: EQUAL
tracked_index: CLEAN_EMPTY
runtime_services: UNCHANGED
ports: 3003/8001/18092_ABSENT
main_deploy: NOT_STARTED
```

Then stop.
