# Stage 2.W3B1 — architect acceptance, exact commit and push

Дата: `2026-07-13`
Branch/base: `preview/solarsage-v2-human-first-navigator-ux` /
`24efa83eb91a36c6419cf174c8d24ee95870086b`
Accepted implementation chain:

- `155_STAGE_2_W3B1_SCHEMA_MYPY_CORRECTION_TZ.md`;
- `156_STAGE_2_W3B1_R1_DOWNSTREAM_TYPE_PRECISION_RECLASSIFICATION_TZ.md`;
- `157_STAGE_2_W3B1_R2_TODAY_HORIZONS_FUNCTION_CONTRACTS_TZ.md`.

Статус: **ARCHITECT ACCEPTED — AUTHORIZED EXACT COMMIT/PUSH ONLY**

Исполнитель работает лично. Запрещены subagents, delegation, `delegate_*`,
background coding/review tasks и использование их результатов как evidence.

## 1. Architect acceptance

Architect independently reviewed the exact four-file source delta and the R2
comment-only repair. No further correction wave is required.

Accepted implementation semantics:

```text
today_horizons.py
  set[str] input                         -> AbstractSet[str] read-only input
  runtime membership/subset expression  unchanged
  function contracts added              exact 16 paired unique
  R2 pre-image hash                      22c72c6f48dec30bc930800fad2901eb337e62599a97bb005979c99429e51f65
  R2 AST/token runtime equivalence       PASS
  final line count                       1000, within GRC030 maximum

horizon_canon.py
  edits                                  local loop-variable identities only
  validation branches/messages/order     unchanged

horizon_content_canon.py
  edits                                  local loop-variable identities only
  lookup keys/messages/iteration order   unchanged

horizon_content_canon_types.py
  HorizonThemeKey                        explicit closed ten-value Literal
  THEME_KEYS runtime values/order        unchanged
  canonical pair                         exact two-item unpack, same sorting
  casts/ignores/Any widening             none
```

Accepted evidence:

```text
tracked implementation scope            exact 4 schema files
W3B1 MyPy diagnostics before             16
W3B1 MyPy diagnostics after              0
cold global MyPy after                   118 diagnostics / 21 paths
newly exposed precise-boundary errors    exact 5 / exact 3 future-W3B2 paths
unexpected new MyPy errors               zero
Ruff                                     PASS_ZERO
GRACE self-tests                         13 PASS
authorized GRACE                         4/4 PASS
targeted regression                      7 files / 139 tests PASS
full API                                 1405 passed / 4 skipped
contracts check                          PASS_NO_DRIFT
contracts compatibility                  additive / zero breaking
fixture normalization                    PASS
shared Python contracts                  44 PASS
frontend guard                           PASS
git diff check                           PASS_ZERO
index                                    empty
runtime/services                         unchanged
ports 3003/8001/18092                    absent
```

The five downstream MyPy diagnostics are accepted type-precision evidence,
not W3B1 regressions. They remain assigned to a separately authored and
authorized W3B2 wave. Do not weaken `HorizonThemeKey`, add casts/ignores, or
edit service files in this acceptance wave.

## 2. Frozen accepted source hashes

Before staging require exactly:

```text
78e552ca56c9a1a436f2fa0aa728c5b5aeea2142f81676cff65d714e52f39733  apps/api/app/schemas/today_horizons.py
db6454a999d55990c5b53c828e7669b098ef9b026c8260558607aefe28a2088f  apps/api/app/schemas/horizon_canon.py
b8c56a2187ab7de3eac587ab1920e534a5117df2a07f2cfc1e892840b0c21672  apps/api/app/schemas/horizon_content_canon.py
82b486fb69422f3400aad6c608aaab931139145add4f9e55713701d18d35cff6  apps/api/app/schemas/horizon_content_canon_types.py
```

Do not edit any source, test, config, contract artifact or task document in
this wave. Documents `156`, `157`, and `158` are staged exactly as written.

## 3. Mandatory preflight

Before staging:

1. completely read master `127` and docs `155`, `156`, `157`, `158`;
2. run `git fetch origin` without merge/rebase;
3. prove branch is exactly
   `preview/solarsage-v2-human-first-navigator-ux`;
4. prove local HEAD = tracking = remote feature =
   `24efa83eb91a36c6419cf174c8d24ee95870086b`;
5. prove `main` = `origin/main` =
   `c9bc36bd9a947566eddb1ffcf5617967c7412676` and remains an ancestor;
6. prove index empty;
7. prove tracked diff paths are the exact four schema files in section 4;
8. prove all four hashes exactly match section 2;
9. prove task docs `156`, `157`, `158` are untracked and unchanged;
10. prove only the five frozen unrelated groups otherwise remain untracked;
11. rerun exact four-file Ruff and GRACE and require clean results;
12. prove runtime services unchanged and ports `3003`, `8001`, `18092`
    absent.

Stop on any mismatch. Never reset, restore, checkout paths, stash, amend,
rebase, force-push or edit a file during this wave.

## 4. Exact implementation paths

```text
apps/api/app/schemas/today_horizons.py
apps/api/app/schemas/horizon_canon.py
apps/api/app/schemas/horizon_content_canon.py
apps/api/app/schemas/horizon_content_canon_types.py
```

## 5. Exact task-document paths

```text
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/156_STAGE_2_W3B1_R1_DOWNSTREAM_TYPE_PRECISION_RECLASSIFICATION_TZ.md
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/157_STAGE_2_W3B1_R2_TODAY_HORIZONS_FUNCTION_CONTRACTS_TZ.md
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/158_STAGE_2_W3B1_ARCH_ACCEPTANCE_COMMIT_PUSH_TZ.md
```

## 6. Exact staging set

Stage only the exact seven explicit paths:

```text
4 implementation paths from section 4
3 task-document paths from section 5
```

Use explicit paths. Forbidden: `git add .`, `git add -A`, directory staging,
wildcards, or staging any frozen/unrelated path.

Before commit require:

```text
staged count                         7
staged set                           exact 4 implementation + exact 3 docs
unstaged tracked diff                empty
cached diff check                    PASS_ZERO
cached source hashes                 exact section 2
cached W3B1 MyPy errors              zero
cached frozen/unrelated paths        zero
```

Inspect the complete cached delta. No file edit is authorized to repair a
staging mismatch; stop and report it.

## 7. Exact commit

Create exactly one normal commit with exact subject:

```text
refactor(api): tighten horizon schema typing
```

After commit require:

```text
parent                               24efa83eb91a36c6419cf174c8d24ee95870086b
subject                              exact
changed paths                        exact 7
implementation paths                 exact 4
task docs                            exact 3
tracked worktree                     clean
index                                empty
```

No amend, fixup, second commit, W3B2 implementation or service edit.

## 8. Mandatory post-commit gates

### 8.1. Ruff and GRACE

```bash
apps/api/.venv/bin/python -m ruff check \
  apps/api/app/schemas/today_horizons.py \
  apps/api/app/schemas/horizon_canon.py \
  apps/api/app/schemas/horizon_content_canon.py \
  apps/api/app/schemas/horizon_content_canon_types.py

apps/api/.venv/bin/python scripts/test_grace_lint.py
apps/api/.venv/bin/python scripts/grace_lint.py \
  apps/api/app/schemas/today_horizons.py \
  apps/api/app/schemas/horizon_canon.py \
  apps/api/app/schemas/horizon_content_canon.py \
  apps/api/app/schemas/horizon_content_canon_types.py
```

Require Ruff zero, 13 GRACE self-tests PASS and exact four files clean.

### 8.2. Cold MyPy proof

From `apps/api`:

```bash
set +e
./.venv/bin/mypy app --no-incremental --no-error-summary --show-error-codes \
  > /tmp/stage2-w3b1-acceptance-mypy.log 2>&1
rc=$?
set -e
test "$rc" -eq 1
```

Parse the diagnostic output and require exactly:

```text
global diagnostics                    118
global failing paths                   21
four W3B1 paths                         0
reclassified W3B2 diagnostics           5
reclassified W3B2 paths                 3
unexpected new errors                   0
```

The exact five accepted service locations remain:

```text
app/services/horizon_guidance_builders.py:292
app/services/horizon_guidance_builders.py:414
app/services/horizon_guidance_service.py:138
app/services/horizon_guidance_service.py:316
app/services/horizon_claim_policy.py:189
```

Do not fix them here.

### 8.3. Targeted and full API

```bash
PYTHONPATH=apps/api apps/api/.venv/bin/python -m pytest \
  apps/api/tests/test_today_horizons_contract.py \
  apps/api/tests/test_contract_registry.py \
  apps/api/tests/test_horizon_canon_service.py \
  apps/api/tests/test_horizon_language_canon.py \
  apps/api/tests/test_horizon_actions_canon.py \
  apps/api/tests/test_personal_patterns_canon.py \
  apps/api/tests/test_horizon_content_canon_service.py \
  -q

PYTHONPATH=apps/api apps/api/.venv/bin/python -m pytest apps/api/tests/ -q
```

Require exact 7 files / 139 PASS and full API 1405 PASS / 4 SKIP.

### 8.4. Contracts and frontend

```bash
pnpm contracts:check
pnpm contracts:compat
pnpm contracts:fixture:check
PYTHONPATH=packages/py-contracts \
  apps/api/.venv/bin/python -m pytest packages/py-contracts/tests/ -q
pnpm guardrails:frontend
git diff --check origin/main...HEAD
```

Require contracts no drift, additive compatibility with zero breaking,
fixture clean, 44 py-contract tests PASS, frontend guard PASS and feature diff
PASS_ZERO.

## 9. Normal push and final equality

Only after every post-commit gate passes:

1. normal push the existing feature branch; never force/change upstream;
2. prove local HEAD = tracking = remote feature SHA;
3. prove exact parent, subject and seven-path commit set;
4. prove tracked worktree clean and index empty;
5. prove only five frozen unrelated untracked groups remain;
6. prove `main`/`origin/main` untouched and still ancestors;
7. prove env/systemd/nginx/database/runtime untouched;
8. prove ports `3003`, `8001`, `18092` absent.

Do not begin W3B2 before callback and a separate architect-authored TZ path.
No W3B2 document is self-authorized by this acceptance wave.

## 10. Frozen unrelated paths

```text
.grace/
artifacts/design/
docs/superpowers/plans/2026-07-05-fix-day-route-auth-build.md
grace.db
skills/
```

## 11. Required callback

```text
PUSHED_STAGE_2_W3B1_SCHEMA_MYPY_CLEAN
commit: <sha> refactor(api): tighten horizon schema typing
staged_scope: EXACT_7
implementation_scope: EXACT_4_SCHEMA_FILES
task_docs: EXACT_3
source_hashes: PASS_4
runtime_equivalence: PASS
function_contracts_added: EXACT_16_PAIRED_UNIQUE
mypy_w3b1: PASS_ZERO
mypy_total: 118_DIAGNOSTICS_21_PATHS
reclassified_downstream: EXACT_5_ERRORS_3_W3B2_PATHS
ruff: PASS_ZERO
grace_selftests: 13_PASS
authorized_grace: PASS_4
targeted_tests: 7_FILES_139_PASS
api_full: 1405_PASS_4_SKIP
contracts_check_compat_fixture: PASS
py_contracts: 44_PASS
frontend_guard: PASS
feature_diff_check: PASS_ZERO
head_tracking_remote: EQUAL
tracked_index: CLEAN_EMPTY
runtime_services: UNCHANGED
ports: 3003/8001/18092_ABSENT
main_deploy: NOT_STARTED
```

Then stop. W3B2/W3B3/W3C remain forbidden.
