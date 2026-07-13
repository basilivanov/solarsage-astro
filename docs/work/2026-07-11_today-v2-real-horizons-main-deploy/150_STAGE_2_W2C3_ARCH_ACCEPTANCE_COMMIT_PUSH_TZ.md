# Stage 2.W2C-3 — architect acceptance, exact commit and push

Дата: `2026-07-13`
Branch/base: `preview/solarsage-v2-human-first-navigator-ux` /
`6c93217fa6fe778388d735659db4f7ae5b894700`
Accepted implementation:

- `147_STAGE_2_W2C3_API_FACADES_TRUTHFUL_GRACE_PREAMBLES_TZ.md`;
- `149_STAGE_2_W2C3_R1_PROFILE_META_PROMISE_ALL_CONTRACT_FIDELITY_TZ.md`.

Prepared next wave:
`151_STAGE_2_W2C4_GRACE_LIBRARY_TRUTHFUL_PREAMBLES_TZ.md`.

Статус: **ARCHITECT ACCEPTED — AUTHORIZED EXACT COMMIT/PUSH ONLY**

Исполнитель работает лично. Запрещены subagents, delegation, `delegate_*`,
background coding/review tasks и использование их результатов как evidence.

## 1. Accepted evidence

Architect independently reviewed the complete 13-facade diff, found one
documentation-fidelity issue in `profile-meta`, accepted the exact R1 repair
and reran all material gates. Accepted evidence:

```text
tracked implementation scope          exact 13 lib/api files
architect-owned tracked doc           exact 147 correction
R1 coder delta                        exact three profile-meta comment meanings
changed executable lines              zero
comment/blank-only diff               PASS 13/13
runtime suffix SHA                    unchanged 13/13
Promise.all runtime                   unchanged
other API files during R1             byte-frozen 12/12
module IDs                            unique and paired 13/13
canonical fields                      present 13/13
generic/garbled preamble text         absent
cities emitted_logs                   ui.fetch_failed only
other emitted_logs                    none 12/12
authorized GRACE                      PASS 13/13
GRACE linter self-tests               11 PASS
strict negative harness               6 PASS / 0 FAIL exact reasons
ESLint                                zero errors / zero warnings
typecheck                             PASS
targeted Vitest                       13 files / 104 tests PASS
remaining GRACE                       3 violations / 3 failing
remaining green/checked               44 / 47
remaining prefix                      lib/grace only
aggregate frontend guard              expected marker-only remainder
git diff check                        PASS
index                                 empty
runtime/services                      unchanged
ports 3003/8001/18092                 absent
```

No additional implementation or correction is authorized in this packet.

## 2. Mandatory preflight

Before staging:

1. completely read 141, 147, 149, 150 and 151;
2. run `git fetch origin` without merge/rebase;
3. prove current branch is exactly
   `preview/solarsage-v2-human-first-navigator-ux`;
4. prove local HEAD = tracking = remote feature =
   `6c93217fa6fe778388d735659db4f7ae5b894700`;
5. prove `main` and `origin/main` remain
   `c9bc36bd9a947566eddb1ffcf5617967c7412676` and are ancestors of HEAD;
6. prove index empty;
7. prove tracked diff contains exactly the 13 implementation paths in section
   3 plus architect-owned tracked doc 147;
8. re-prove comment-only/runtime-suffix/module-ID invariants for all 13 files;
9. prove 149, 150 and 151 are the only task docs currently untracked;
10. prove only the five frozen unrelated paths otherwise remain untracked;
11. prove runtime services and canonical ports are unchanged and auxiliary
    ports `3003`, `8001`, `18092` are absent.

Stop on any mismatch. Never reset, restore, checkout paths, stash, amend,
rebase or force-push. Do not edit any file during this wave. If a whitespace,
scope or evidence mismatch exists, stop for architect correction.

## 3. Exact implementation paths

```text
lib/api/access.ts
lib/api/calendar.ts
lib/api/chat.ts
lib/api/checkin.ts
lib/api/cities.ts
lib/api/config.ts
lib/api/dev-auth-guard.ts
lib/api/horary.ts
lib/api/natal.ts
lib/api/profile-meta.ts
lib/api/profile.ts
lib/api/readings.ts
lib/api/today.ts
```

## 4. Exact task-document paths

```text
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/147_STAGE_2_W2C3_API_FACADES_TRUTHFUL_GRACE_PREAMBLES_TZ.md
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/149_STAGE_2_W2C3_R1_PROFILE_META_PROMISE_ALL_CONTRACT_FIDELITY_TZ.md
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/150_STAGE_2_W2C3_ARCH_ACCEPTANCE_COMMIT_PUSH_TZ.md
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/151_STAGE_2_W2C4_GRACE_LIBRARY_TRUTHFUL_PREAMBLES_TZ.md
```

Doc 147 is an expected tracked modification owned by the architect. Docs 149,
150 and 151 are expected new task documents. Coder must stage them exactly as
they exist and must not edit their contents.

## 5. Exact staging set

Stage only exact 17 explicit paths:

```text
13 implementation paths from section 3
4 task-document paths from section 4
```

Use explicit path arguments. Forbidden: `git add .`, `git add -A`, directory
staging, wildcard staging or any staging of frozen/unrelated files.

Before commit require:

```text
staged count                    17
staged set                      exact 13 implementation + exact 4 docs
unstaged tracked diff           empty
cached executable changes       zero
cached runtime suffix proof     unchanged 13/13
cached diff check               PASS
frozen/unrelated in index       zero
```

The cached doc 147 diff must contain only the architect's Promise.all wording
correction. The cached `profile-meta.ts` preamble must describe the same
runtime truth: independent `.ok` handling occurs only after both promises
resolve; one rejected promise enters the shared catch fallback.

## 6. Exact commit

Create exactly one normal commit with exact subject:

```text
chore(grace): document api facade contracts
```

After commit require:

```text
parent                          6c93217fa6fe778388d735659db4f7ae5b894700
subject                         exact
changed paths                   exact 17
implementation paths            exact 13
task docs                       exact 4
tracked worktree                clean
index                           empty
```

No amend, fixup, second commit or W2C-4 edit.

## 7. Mandatory post-commit gates

### 7.1. GRACE and negative harness

```bash
python3 scripts/test_grace_front_lint.py
python3 scripts/grace_front_lint.py \
  lib/api/access.ts \
  lib/api/calendar.ts \
  lib/api/chat.ts \
  lib/api/checkin.ts \
  lib/api/cities.ts \
  lib/api/config.ts \
  lib/api/dev-auth-guard.ts \
  lib/api/horary.ts \
  lib/api/natal.ts \
  lib/api/profile-meta.ts \
  lib/api/profile.ts \
  lib/api/readings.ts \
  lib/api/today.ts
bash scripts/grace/check-negative.sh
```

Require: self-tests 11 PASS; all 13 facades clean; negative harness 6 PASS /
0 FAIL with exact rule reasons.

### 7.2. Frontend static and targeted regression

```bash
pnpm lint
pnpm typecheck
npx vitest run \
  __tests__/api/access.test.ts \
  __tests__/api/calendar.test.ts \
  __tests__/api/checkin.test.ts \
  __tests__/api/cities.test.ts \
  __tests__/api/dev-auth-route.test.ts \
  __tests__/api/natal-report.test.ts \
  __tests__/api/profile-meta.test.ts \
  __tests__/api/readings.test.ts \
  __tests__/hooks/useAccess.test.ts \
  __tests__/hooks/useChat.test.ts \
  __tests__/hooks/useProfile.test.ts \
  __tests__/horary/horary-screen-flow.test.tsx \
  __tests__/guardrails/preview-isolation.test.ts
```

Require: ESLint zero errors/warnings; typecheck PASS; 13 files / 104 tests
PASS.

### 7.3. Exact marker remainder and aggregate diagnostic

Full marker output must prove exactly:

```text
violations=3
failing_paths=3
green_paths=44
checked_paths=47
lib/api failing paths=0
remaining paths=lib/grace/hooks/useCalendar.ts,
                lib/grace/hooks/useDay.ts,
                lib/grace/index.ts
```

Run `pnpm guardrails:frontend` diagnostically. ESLint and typecheck must pass;
its only non-zero cause may be those exact three `GRC003` module-map
violations. No other output/failure is acceptable.

Finally run:

```bash
git diff --check origin/main...HEAD
```

Require PASS_ZERO. Production build and full Vitest remain mandatory in final
RC, not in this comment-only commit packet.

## 8. Normal push and final equality

After every post-commit gate passes:

1. normal push the existing feature branch; never force/change upstream;
2. prove local HEAD = tracking = remote feature SHA;
3. prove the pushed commit has exact parent, subject and 17-path set;
4. prove tracked worktree clean and index empty;
5. prove only five frozen unrelated untracked paths remain;
6. prove `main`/`origin/main` untouched and still ancestors;
7. prove env, systemd, nginx, database and runtime services untouched;
8. prove ports `3003`, `8001`, `18092` absent.

Do not begin W2C-4 before the callback and a separate architect message.
Committed doc 151 is traceability, not self-authorization.

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
PUSHED_STAGE_2_W2C3_API_FACADE_CONTRACTS
commit: <sha> chore(grace): document api facade contracts
staged_scope: EXACT_17
implementation_scope: EXACT_13_API_FACADES
task_docs: EXACT_4
comment_only_equivalence: PASS_13
runtime_suffix_hashes: UNCHANGED_13
promise_all_runtime: UNCHANGED
module_ids: UNIQUE_AND_PAIRED_13
grace_linter_self_tests: 11_PASS
authorized_paths_grace: PASS_13
negative_harness: 6_PASS_0_FAIL_EXACT_REASONS
eslint: PASS_ZERO_ERRORS_ZERO_WARNINGS
typecheck: PASS
targeted_tests: 13_FILES_104_PASS
remaining_grace: 3_VIOLATIONS_3_FAILING_44_GREEN_47_CHECKED
remaining_paths: EXACT_3_LIB_GRACE
guardrails_frontend: EXPECTED_FINAL_MARKER_REMAINDER_ONLY
feature_diff_check: PASS_ZERO
head_tracking_remote: EQUAL
tracked_index: CLEAN_EMPTY
runtime_services: UNCHANGED
ports: 3003/8001/18092_ABSENT
main_deploy: NOT_STARTED
```

Then stop.
